#!/usr/bin/env python3
"""
neo4j_to_bigquery_graph.py
==========================
Full pipeline: Neo4j --> BigQuery tables --> BigQuery Property Graph.

The script auto-discovers the Neo4j schema (node labels, relationship types,
and all their properties), exports everything in batches, bulk-loads into
BigQuery via load jobs, and finally issues a CREATE PROPERTY GRAPH statement.

Designed for large Neo4j databases (millions of nodes / relationships).

Environment variables (or pass via CLI flags):
  NEO4J_URI            bolt://localhost:7687
  NEO4J_USER           neo4j
  NEO4J_PASSWORD       (required)
  BIGQUERY_PROJECT_ID  your-gcp-project
  BIGQUERY_DATASET     your_dataset          (created if missing)
  BIGQUERY_LOCATION    US                    (optional, default US)
  BIGQUERY_GRAPH_NAME  MyGraph               (property graph name)
  BATCH_SIZE           10000                 (rows per Neo4j fetch + BQ load)

Usage:
  pip install neo4j google-cloud-bigquery
  python neo4j_to_bigquery_graph.py

  # or override via flags:
  python neo4j_to_bigquery_graph.py \
      --neo4j-uri bolt://localhost:7687 \
      --neo4j-user neo4j \
      --neo4j-password secret \
      --bq-project my-project \
      --bq-dataset my_dataset \
      --bq-graph-name MyGraph \
      --batch-size 10000
"""

import argparse
import json
import os
import sys
import logging
import tempfile
from datetime import date, datetime

from neo4j import GraphDatabase
from google.cloud import bigquery

# Default batch size for Neo4j SKIP/LIMIT pagination and BQ load chunks
DEFAULT_BATCH_SIZE = 10_000

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Neo4j type -> BigQuery type mapping
# ---------------------------------------------------------------------------
_NEO4J_TYPE_MAP = {
    "Long": "INT64",
    "Integer": "INT64",
    "Double": "FLOAT64",
    "Float": "FLOAT64",
    "String": "STRING",
    "Boolean": "BOOL",
    "Date": "DATE",
    "DateTime": "TIMESTAMP",
    "LocalDateTime": "DATETIME",
    "LocalDate": "DATE",
    "LocalTime": "TIME",
    "Time": "TIME",
    "Duration": "STRING",  # no BQ equivalent; store as ISO string
    "Point": "STRING",  # serialise as JSON / WKT
    "StringArray": "STRING",  # serialise as JSON array
    "LongArray": "STRING",
    "DoubleArray": "STRING",
    "BooleanArray": "STRING",
}


def _map_neo4j_type(neo4j_type: str) -> str:
    """Return a BigQuery type for a Neo4j property type string."""
    # neo4j schema procedures return types like "String", "Long", "List(String)" ...
    if neo4j_type.startswith("List"):
        return "STRING"  # serialise lists as JSON strings
    return _NEO4J_TYPE_MAP.get(neo4j_type, "STRING")


def _python_value_to_bq(value):
    """Coerce a Python value returned by the Neo4j driver for BigQuery."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, default=str)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    # neo4j spatial / duration objects -> string
    if hasattr(value, "__class__") and value.__class__.__module__.startswith("neo4j"):
        return str(value)
    return value


# ---------------------------------------------------------------------------
# Schema discovery
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Label collapsing
# ---------------------------------------------------------------------------
# When a Neo4j node has multiple labels like :ADEO_Concept:ADEO_NatureOfProduct,
# db.schema.nodeTypeProperties() returns compound nodeType strings.
# We want to collapse these: if a compound label contains a "dominant" label
# (e.g. ADEO_Concept), all nodes with that dominant label are merged into one
# BigQuery table, with the union of all their properties.
#
# This avoids dozens of near-identical tables and fixes the edge-reference
# problem where edges point at labels that don't exist as standalone tables.
# ---------------------------------------------------------------------------

# Labels that absorb any compound label containing them.
# Order matters: first match wins.  Add more entries as needed.
DOMINANT_LABELS = ["ADEO_Concept", "ADEO_ConceptScheme"]


def _collapse_label(raw_label: str) -> str | None:
    """
    Given a compound label string (e.g. "ADEO_Concept___ADEO_NatureOfProduct"),
    return the dominant label if one is present, otherwise return None.
    Nodes/edges whose labels don't match any dominant label are ignored.
    """
    for dominant in DOMINANT_LABELS:
        if dominant in raw_label:
            return dominant
    return None


def discover_node_labels(session) -> dict:
    """
    Returns {label: {prop_name: bq_type, ...}, ...}
    Uses CALL db.schema.nodeTypeProperties() which works on Neo4j 4.x/5.x.

    Labels containing a dominant label (see DOMINANT_LABELS) are collapsed
    into a single entry.  Properties from all compound variants are merged
    (union) so the resulting BigQuery table has every column that any variant
    might use.

    Node types that do not contain any dominant label are silently skipped.
    """
    result = session.run("CALL db.schema.nodeTypeProperties()")
    labels = {}
    skipped = set()
    for record in result:
        # nodeType looks like ":`Person`" or ":`ADEO_Concept`&`ADEO_NatureOfProduct`"
        raw_label = record["nodeType"]
        raw_stripped = raw_label.strip(":` ")
        # Collapse compound labels into the dominant one
        label = _collapse_label(raw_stripped)
        if label is None:
            skipped.add(raw_stripped)
            continue
        prop = record["propertyName"]
        # propertyTypes is a list, take the first
        neo4j_types = record["propertyTypes"]
        bq_type = _map_neo4j_type(neo4j_types[0]) if neo4j_types else "STRING"
        labels.setdefault(label, {})
        if prop and (prop != "properties" or prop != "EN_definition_BACKUP"):
            labels[label][prop] = bq_type
    if skipped:
        log.warning(
            "Skipped %d node type(s) with no dominant label: %s",
            len(skipped),
            sorted(skipped),
        )
    log.info(
        "Discovered %d node label(s) (after collapsing): %s",
        len(labels),
        list(labels.keys()),
    )
    return labels


def discover_rel_types(session) -> dict:
    """
    Returns {relType: {prop_name: bq_type, ...}, ...}
    Uses CALL db.schema.relTypeProperties().
    """
    result = session.run("CALL db.schema.relTypeProperties()")
    rels = {}
    for record in result:
        raw_type = record["relType"]
        rel_type = raw_type.strip(":` ")
        prop = record["propertyName"]
        neo4j_types = record["propertyTypes"]
        bq_type = _map_neo4j_type(neo4j_types[0]) if neo4j_types else "STRING"
        rels.setdefault(rel_type, {})
        if prop:  # propertyName can be None when rel has no props
            rels[rel_type][prop] = bq_type
    log.info("Discovered %d relationship type(s): %s", len(rels), list(rels.keys()))
    return rels


def discover_rel_endpoints(session, rel_types: list) -> dict:
    """
    For each relationship type, discover (source_label, target_label).
    Returns {relType: (source_label, target_label), ...}
    Uses CALL db.schema.visualization() (Neo4j 4.x/5.x).
    Falls back to sampling if the procedure is unavailable.

    Returned labels are collapsed via _collapse_label() so they match
    the node_labels dict produced by discover_node_labels().
    Relationships whose source or target has no dominant label are skipped.
    """
    endpoints = {}
    try:
        result = session.run("CALL db.schema.visualization()")
        record = result.single()
        if record:
            rels_data = record["relationships"]
            for rel in rels_data:
                rel_type = rel.type
                src_label = _collapse_label(list(rel.start_node.labels)[0])
                tgt_label = _collapse_label(list(rel.end_node.labels)[0])
                if src_label is None or tgt_label is None:
                    log.warning(
                        "Skipping relationship :%s (endpoint has no dominant label: src=%s, tgt=%s)",
                        rel_type,
                        list(rel.start_node.labels),
                        list(rel.end_node.labels),
                    )
                    continue
                endpoints[rel_type] = (src_label, tgt_label)
    except Exception:
        log.warning("db.schema.visualization() not available; sampling relationships")

    # Fill gaps by sampling one relationship per type
    for rt in rel_types:
        if rt not in endpoints:
            sample = session.run(
                f"MATCH (a)-[r:`{rt}`]->(b) RETURN labels(a)[0] AS src, labels(b)[0] AS tgt LIMIT 1"
            )
            rec = sample.single()
            if rec:
                src_label = _collapse_label(rec["src"])
                tgt_label = _collapse_label(rec["tgt"])
                if src_label is None or tgt_label is None:
                    log.warning(
                        "Skipping relationship :%s (endpoint has no dominant label: src=%s, tgt=%s)",
                        rt,
                        rec["src"],
                        rec["tgt"],
                    )
                    continue
                endpoints[rt] = (src_label, tgt_label)
            else:
                log.warning("No instances found for relationship :%s -- skipping", rt)
    return endpoints


# ---------------------------------------------------------------------------
# Neo4j data export
# ---------------------------------------------------------------------------


def _count_nodes(session, label: str) -> int:
    result = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt")
    return result.single()["cnt"]


def _count_rels(session, rel_type: str) -> int:
    result = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) AS cnt")
    return result.single()["cnt"]


def export_nodes_batched(session, label: str, properties: dict, batch_size: int):
    """
    Generator: yields batches (lists) of node dicts, each up to batch_size rows.
    Uses SKIP/LIMIT pagination to avoid loading everything into memory at once.
    Each row includes a neo4jNodeLabels field preserving the original Neo4j labels.
    """
    total = _count_nodes(session, label)
    log.info("  :%s — %d nodes to export (batch_size=%d)", label, total, batch_size)
    offset = 0
    exported = 0
    while offset < total:
        query = (
            f"MATCH (n:`{label}`) "
            f"RETURN n, labels(n) AS _labels "
            f"ORDER BY elementId(n) "
            f"SKIP {offset} LIMIT {batch_size}"
        )
        result = session.run(query)
        batch = []
        for record in result:
            node = record["n"]
            row = {
                "_node_id": str(node.element_id),
                "neo4jNodeLabels": json.dumps(sorted(record["_labels"])),
            }
            for prop in properties:
                row[prop] = _python_value_to_bq(node.get(prop))
            batch.append(row)
        if not batch:
            break
        exported += len(batch)
        log.info(
            "    :%s — batch %d rows (total so far: %d/%d)",
            label,
            len(batch),
            exported,
            total,
        )
        yield batch
        offset += batch_size
    log.info("  :%s — export complete: %d nodes", label, exported)


def export_rels_batched(session, rel_type: str, properties: dict, batch_size: int):
    """
    Generator: yields batches (lists) of relationship dicts.
    Uses SKIP/LIMIT pagination.
    """
    total = _count_rels(session, rel_type)
    log.info(
        "  :%s — %d relationships to export (batch_size=%d)",
        rel_type,
        total,
        batch_size,
    )
    offset = 0
    exported = 0
    while offset < total:
        query = (
            f"MATCH (a)-[r:`{rel_type}`]->(b) "
            f"RETURN elementId(a) AS _src_id, elementId(b) AS _tgt_id, r "
            f"ORDER BY elementId(r) "
            f"SKIP {offset} LIMIT {batch_size}"
        )
        result = session.run(query)
        batch = []
        for record in result:
            rel = record["r"]
            row = {
                "_src_id": str(record["_src_id"]),
                "_tgt_id": str(record["_tgt_id"]),
            }
            for prop in properties:
                row[prop] = _python_value_to_bq(rel.get(prop))
            batch.append(row)
        if not batch:
            break
        exported += len(batch)
        log.info(
            "    :%s — batch %d rows (total so far: %d/%d)",
            rel_type,
            len(batch),
            exported,
            total,
        )
        yield batch
        offset += batch_size
    log.info("  :%s — export complete: %d relationships", rel_type, exported)


# ---------------------------------------------------------------------------
# BigQuery helpers
# ---------------------------------------------------------------------------


def ensure_dataset(
    bq_client: bigquery.Client, project: str, dataset_id: str, location: str
):
    dataset_ref = f"{project}.{dataset_id}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = location
    bq_client.create_dataset(dataset, exists_ok=True)
    log.info("Dataset %s ready", dataset_ref)


def _bq_schema_for_node(properties: dict) -> list:
    """Build a BigQuery schema field list for a node table."""
    fields = [
        bigquery.SchemaField("_node_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("neo4jNodeLabels", "STRING", mode="NULLABLE"),
    ]
    for prop, bq_type in properties.items():
        fields.append(bigquery.SchemaField(prop, bq_type, mode="NULLABLE"))
    return fields


def _bq_schema_for_rel(properties: dict) -> list:
    """Build a BigQuery schema field list for a relationship table."""
    fields = [
        bigquery.SchemaField("_src_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("_tgt_id", "STRING", mode="REQUIRED"),
    ]
    for prop, bq_type in properties.items():
        fields.append(bigquery.SchemaField(prop, bq_type, mode="NULLABLE"))
    return fields


def _sanitize_table_name(name: str) -> str:
    """BigQuery table names: letters, numbers, underscores."""
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)


def create_table(
    bq_client: bigquery.Client,
    project: str,
    dataset: str,
    table_name: str,
    schema: list,
):
    """Drop-and-recreate a BigQuery table."""
    table_ref = f"{project}.{dataset}.{table_name}"
    bq_client.delete_table(table_ref, not_found_ok=True)
    table = bigquery.Table(table_ref, schema=schema)
    bq_client.create_table(table)
    log.info("  Created table %s", table_ref)
    return table_ref


def load_batch_to_bigquery(
    bq_client: bigquery.Client,
    table_ref: str,
    schema: list,
    rows: list[dict],
):
    """
    Bulk-load a batch of rows into an existing BigQuery table using a load job.
    Writes rows to a temporary newline-delimited JSON file, then loads via
    load_table_from_file (much faster and more reliable than insert_rows_json
    for large data).
    """
    if not rows:
        return 0

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=True) as tmp:
        for row in rows:
            tmp.write(json.dumps(row, default=str) + "\n")
        tmp.flush()

        # Reopen in binary mode for the BQ client
        with open(tmp.name, "rb") as f:
            job = bq_client.load_table_from_file(f, table_ref, job_config=job_config)
        job.result()  # block until done
        if job.errors:
            log.error("Load job errors for %s: %s", table_ref, job.errors)
            raise RuntimeError(f"BigQuery load errors: {job.errors}")

    return len(rows)


# ---------------------------------------------------------------------------
# Property Graph DDL generation & execution
# ---------------------------------------------------------------------------


def build_property_graph_ddl(
    project: str,
    dataset: str,
    graph_name: str,
    node_labels: dict,  # {label: {prop: bq_type}}
    rel_types: dict,  # {relType: {prop: bq_type}}
    rel_endpoints: dict,  # {relType: (src_label, tgt_label)}
) -> str:
    """
    Build a CREATE OR REPLACE PROPERTY GRAPH statement matching the pattern
    used in sql/social_network_example/03_create_graph.sql.
    """
    fqn = f"`{project}.{dataset}.{graph_name}`"
    parts = [f"CREATE OR REPLACE PROPERTY GRAPH {fqn}"]

    # -- NODE TABLES ----------------------------------------------------------
    node_clauses = []
    for label, props in node_labels.items():
        tbl = _sanitize_table_name(label)
        tbl_ref = f"`{project}.{dataset}.{tbl}`"
        prop_list = ", ".join(["_node_id", "neo4jNodeLabels"] + list(props.keys()))
        node_clauses.append(
            f"  {tbl_ref}\n"
            f"    KEY (_node_id)\n"
            f"    LABEL {tbl}\n"
            f"    PROPERTIES ({prop_list})"
        )
    parts.append("NODE TABLES (\n" + ",\n\n".join(node_clauses) + "\n)")

    # -- EDGE TABLES ----------------------------------------------------------
    edge_clauses = []
    for rel_type, props in rel_types.items():
        if rel_type not in rel_endpoints:
            log.warning("Skipping relationship %s (no endpoint info)", rel_type)
            continue
        src_label, tgt_label = rel_endpoints[rel_type]
        tbl = _sanitize_table_name(rel_type)
        tbl_ref = f"`{project}.{dataset}.{tbl}`"
        src_tbl_ref = f"`{project}.{dataset}.{_sanitize_table_name(src_label)}`"
        tgt_tbl_ref = f"`{project}.{dataset}.{_sanitize_table_name(tgt_label)}`"

        prop_names = list(props.keys())
        prop_clause = (
            f"\n    PROPERTIES ({', '.join(prop_names)})" if prop_names else ""
        )
        edge_clauses.append(
            f"  {tbl_ref}\n"
            f"    KEY (_src_id, _tgt_id)\n"
            f"    SOURCE KEY (_src_id) REFERENCES {src_tbl_ref}(_node_id)\n"
            f"    DESTINATION KEY (_tgt_id) REFERENCES {tgt_tbl_ref}(_node_id)\n"
            f"    LABEL {tbl}"
            f"{prop_clause}"
        )
    parts.append("EDGE TABLES (\n" + ",\n\n".join(edge_clauses) + "\n);")

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def parse_args():
    p = argparse.ArgumentParser(
        description="Migrate a Neo4j database into a BigQuery Property Graph."
    )
    p.add_argument(
        "--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687")
    )
    p.add_argument("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"))
    p.add_argument("--neo4j-password", default=os.getenv("NEO4J_PASSWORD"))
    p.add_argument(
        "--neo4j-database",
        default=os.getenv("NEO4J_DATABASE", "neo4j"),
        help="Neo4j database name (default: neo4j)",
    )
    p.add_argument("--bq-project", default=os.getenv("BIGQUERY_PROJECT_ID"))
    p.add_argument(
        "--bq-dataset", default=os.getenv("BIGQUERY_DATASET", "neo4j_import")
    )
    p.add_argument("--bq-location", default=os.getenv("BIGQUERY_LOCATION", "EU"))
    p.add_argument(
        "--bq-graph-name", default=os.getenv("BIGQUERY_GRAPH_NAME", "Neo4jGraph")
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("BATCH_SIZE", str(DEFAULT_BATCH_SIZE))),
        help=f"Rows per Neo4j fetch and BQ load chunk (default: {DEFAULT_BATCH_SIZE})",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated DDL without executing anything on BigQuery",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if not args.neo4j_password:
        log.error("Neo4j password is required (--neo4j-password or NEO4J_PASSWORD)")
        sys.exit(1)
    if not args.bq_project and not args.dry_run:
        log.error("BigQuery project is required (--bq-project or BIGQUERY_PROJECT_ID)")
        sys.exit(1)

    batch_size = args.batch_size

    # ---- Connect to Neo4j ---------------------------------------------------
    log.info("Connecting to Neo4j at %s ...", args.neo4j_uri)
    driver = GraphDatabase.driver(
        args.neo4j_uri,
        auth=(args.neo4j_user, args.neo4j_password),
    )
    driver.verify_connectivity()
    log.info("Neo4j connected.")

    with driver.session(database=args.neo4j_database) as session:
        # ---- 1. Discover schema ---------------------------------------------
        log.info("--- Phase 1: Schema discovery ---")
        node_labels = discover_node_labels(session)
        rel_types = discover_rel_types(session)
        rel_endpoints = discover_rel_endpoints(session, list(rel_types.keys()))

        # ---- 2. Generate DDL (before export so dry-run is fast) -------------
        ddl = build_property_graph_ddl(
            project=args.bq_project,
            dataset=args.bq_dataset,
            graph_name=args.bq_graph_name,
            node_labels=node_labels,
            rel_types=rel_types,
            rel_endpoints=rel_endpoints,
        )

        if args.dry_run:
            log.info("--- DRY RUN: Generated Property Graph DDL ---")
            print("\n" + ddl + "\n")
            print(f"Node tables: {list(node_labels.keys())}")
            print(f"Edge tables: {list(rel_types.keys())}")
            for label in node_labels:
                cnt = _count_nodes(session, label)
                print(f"  :{label}  -> {cnt} nodes")
            for rt in rel_types:
                cnt = _count_rels(session, rt)
                print(f"  :{rt}  -> {cnt} relationships")
            driver.close()
            sys.exit(0)

        # ---- 3. Setup BigQuery ----------------------------------------------
        log.info("--- Phase 2: Setup BigQuery tables ---")
        bq_client = bigquery.Client(project=args.bq_project, location=args.bq_location)
        ensure_dataset(bq_client, args.bq_project, args.bq_dataset, args.bq_location)

        # Create all tables up front (empty), then stream batches into them
        node_table_refs = {}
        for label, props in node_labels.items():
            table_name = _sanitize_table_name(label)
            schema = _bq_schema_for_node(props)
            node_table_refs[label] = (
                create_table(
                    bq_client, args.bq_project, args.bq_dataset, table_name, schema
                ),
                schema,
            )

        rel_table_refs = {}
        for rel_type, props in rel_types.items():
            table_name = _sanitize_table_name(rel_type)
            schema = _bq_schema_for_rel(props)
            rel_table_refs[rel_type] = (
                create_table(
                    bq_client, args.bq_project, args.bq_dataset, table_name, schema
                ),
                schema,
            )

        # ---- 4. Export from Neo4j + bulk load into BigQuery (batched) -------
        log.info("--- Phase 3: Batched export + load (batch_size=%d) ---", batch_size)
        total_nodes = 0
        for label, props in node_labels.items():
            table_ref, schema = node_table_refs[label]
            for batch in export_nodes_batched(session, label, props, batch_size):
                loaded = load_batch_to_bigquery(bq_client, table_ref, schema, batch)
                total_nodes += loaded
                log.info("    -> loaded %d rows to %s", loaded, table_ref)

        total_rels = 0
        for rel_type, props in rel_types.items():
            table_ref, schema = rel_table_refs[rel_type]
            for batch in export_rels_batched(session, rel_type, props, batch_size):
                loaded = load_batch_to_bigquery(bq_client, table_ref, schema, batch)
                total_rels += loaded
                log.info("    -> loaded %d rows to %s", loaded, table_ref)

    driver.close()
    log.info("Neo4j export + BigQuery load complete.")

    # ---- 5. Create Property Graph -------------------------------------------
    log.info("--- Phase 4: Create BigQuery Property Graph ---")
    log.info("DDL:\n%s", ddl)
    query_job = bq_client.query(ddl)
    query_job.result()  # wait for completion
    log.info(
        "Property Graph `%s.%s.%s` created successfully!",
        args.bq_project,
        args.bq_dataset,
        args.bq_graph_name,
    )

    # ---- Summary ------------------------------------------------------------
    log.info("=== Migration complete ===")
    log.info("  Node tables: %s", list(node_labels.keys()))
    log.info("  Edge tables: %s", list(rel_types.keys()))
    log.info("  Total nodes loaded: %d", total_nodes)
    log.info("  Total relationships loaded: %d", total_rels)

if __name__ == "__main__":
    main()
