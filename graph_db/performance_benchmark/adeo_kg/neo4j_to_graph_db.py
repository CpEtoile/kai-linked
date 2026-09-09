#!/usr/bin/env python3
"""
neo4j_to_graph_db.py
====================
Migrate Neo4j nodes and relationships into GraphDB repository via RDF Turtle triples.

Environment variables (or pass via CLI flags):
  NEO4J_URI          bolt://localhost:7687
  NEO4J_USER         neo4j
  NEO4J_PASSWORD     (required)
  NEO4J_DATABASE     neo4j
  GRAPHDB_ENDPOINT   http://localhost:7200/repositories/shacl_employee_demo/statements
  BATCH_SIZE         5000
  RDF_PREFIX         http://example.org/employee/

Usage:
  uv run graph_db/performance_benchmark/adeo_kg/neo4j_to_graph_db.py \
      --neo4j-uri "bolt://localhost:7687" \
      --neo4j-password "secret"
"""

import argparse
import json
import logging
import os
import sys
import requests
from neo4j import GraphDatabase

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

SKOS_NS = "http://www.w3.org/2004/02/skos/core#"

def node_to_uri(node_id: str, prefix: str) -> str:
    node_id_str = str(node_id).strip()
    if node_id_str.startswith("<") and node_id_str.endswith(">"):
        return node_id_str
    if node_id_str.startswith(("http://", "https://", "urn:")):
        return f"<{node_id_str}>"
    return f"<{prefix}node/{node_id_str}>"


def value_to_rdf(val) -> str:
    if isinstance(val, bool):
        return f'"{str(val).lower()}"^^<http://www.w3.org/2001/XMLSchema#boolean>'
    if isinstance(val, int):
        return f'"{val}"^^<http://www.w3.org/2001/XMLSchema#integer>'
    if isinstance(val, float):
        return f'"{val}"^^<http://www.w3.org/2001/XMLSchema#double>'
    # String / fallback
    clean = str(val).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{clean}"'


EXCLUDED_PROPERTIES = {"embedding"}


def is_property_excluded(prop_name: str) -> bool:
    return prop_name.lower() in EXCLUDED_PROPERTIES



def map_class_to_rdf(class_name: str, prefix: str = "") -> str:
    print(f"Mapping class name: {class_name} with prefix: {prefix}")
    normalized = str(class_name).strip()
    mapping = {
        "ADEO_CONCEPT": f"<{SKOS_NS}Concept>",
        "ADEO_CONCEPT_SCHEME": f"<{SKOS_NS}ConceptScheme>",
    }
    key = normalized.upper().replace("-", "_").replace(" ", "_")
    if key in mapping:
        return mapping[key]
    if prefix:
        return f"<{prefix}class/{normalized}>"
    return f"<{normalized}>"


def map_relation_to_rdf(rel_name: str, prefix: str = "") -> str:
    print(f"Mapping relation name: {rel_name} with prefix: {prefix}")

    normalized = str(rel_name).strip()
    mapping = {
        "BROADER": f"<{SKOS_NS}broader>",
        "NARROWER": f"<{SKOS_NS}narrower>",
        "TOP_CONCEPT_OF": f"<{SKOS_NS}topConceptOf>",
        "PREF_LABEL": f"<{SKOS_NS}prefLabel>",
        "ALT_LABEL": f"<{SKOS_NS}altLabel>",
        "LABEL": f"<{SKOS_NS}prefLabel>",
    }
    key = normalized.upper().replace("-", "_").replace(" ", "_")
    if key in mapping:
        return mapping[key]
    if prefix:
        return f"<{prefix}rel/{normalized}>"
    return f"<{normalized}>"


def upload_turtle_batch(endpoint: str, turtle_data: str):
    headers = {"Content-Type": "text/turtle"}
    resp = requests.post(endpoint, data=turtle_data.encode("utf-8"), headers=headers)
    resp.raise_for_status()


def export_neo4j_to_graphdb(
    neo4j_uri: str,
    user: str,
    password: str,
    database: str,
    endpoint: str,
    batch_size: int,
    prefix: str,
    dry_run: bool = False,
    limit: int | None = None,
):
    log.info("Connecting to Neo4j at %s ...", neo4j_uri)
    driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
    driver.verify_connectivity()
    log.info("Neo4j connected.")

    with driver.session(database=database) as session:
        # 1. Export Nodes -> Turtle triples
        log.info("--- Phase 1: Exporting Nodes %s---", "(DRY RUN) " if dry_run else "")
        offset = 0
        total_nodes = 0
        while True:
            if limit is not None and total_nodes >= limit:
                log.info("Reached node limit of %d", limit)
                break
            current_batch_limit = (
                min(batch_size, limit - total_nodes) if limit is not None else batch_size
            )
            res = session.run(
                "MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS props "
                "ORDER BY elementId(n) SKIP $offset LIMIT $limit",
                offset=offset,
                limit=current_batch_limit,
            )
            records = list(res)
            if not records:
                break

            triples = []
            for r in records:
                s = node_to_uri(r["id"], prefix)
                for lbl in r["labels"]:
                    mapped_type = map_class_to_rdf(lbl, prefix)
                    triples.append(
                        f"{s} <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> {mapped_type} ."
                    )
                for k, v in r["props"].items():
                    if is_property_excluded(k):
                        continue
                    if v is not None:
                        triples.append(f"{s} {map_relation_to_rdf(k, prefix)} {value_to_rdf(v)} .")

            if triples:
                if dry_run:
                    if total_nodes == 0:
                        log.info("  [DRY RUN] Sample node triples:\n" + "\n".join(triples[:5]))
                    total_nodes += len(records)
                    log.info("  [DRY RUN] Processed %d nodes (total: %d)", len(records), total_nodes)
                else:
                    upload_turtle_batch(endpoint, "\n".join(triples))
                    total_nodes += len(records)
                    log.info("  Uploaded %d nodes (total: %d)", len(records), total_nodes)

            offset += len(records)

        # 2. Export Relationships -> Turtle triples
        log.info("--- Phase 2: Exporting Relationships %s---", "(DRY RUN) " if dry_run else "")
        offset = 0
        total_rels = 0
        while True:
            if limit is not None and total_rels >= limit:
                log.info("Reached relationship limit of %d", limit)
                break
            current_batch_limit = (
                min(batch_size, limit - total_rels) if limit is not None else batch_size
            )
            res = session.run(
                "MATCH (a)-[r]->(b) "
                "RETURN elementId(a) AS src, elementId(b) AS tgt, type(r) AS rel_type, properties(r) AS props "
                "ORDER BY elementId(r) SKIP $offset LIMIT $limit",
                offset=offset,
                limit=current_batch_limit,
            )
            records = list(res)
            if not records:
                break

            triples = []
            for r in records:
                src_uri = node_to_uri(r["src"], prefix)
                tgt_uri = node_to_uri(r["tgt"], prefix)
                rel_pred = map_relation_to_rdf(r["rel_type"], prefix)
                triples.append(f"{src_uri} {rel_pred} {tgt_uri} .")

            if triples:
                if dry_run:
                    if total_rels == 0:
                        log.info("  [DRY RUN] Sample relationship triples:\n" + "\n".join(triples[:5]))
                    total_rels += len(records)
                    log.info("  [DRY RUN] Processed %d relationships (total: %d)", len(records), total_rels)
                else:
                    upload_turtle_batch(endpoint, "\n".join(triples))
                    total_rels += len(records)
                    log.info("  Uploaded %d relationships (total: %d)", len(records), total_rels)

            offset += len(records)

    driver.close()
    log.info(
        "=== Migration %scomplete: %d nodes, %d relationships ===",
        "(DRY RUN) " if dry_run else "",
        total_nodes,
        total_rels,
    )


def parse_args():
    p = argparse.ArgumentParser(
        description="Migrate Neo4j graph into GraphDB RDF repository."
    )
    p.add_argument(
        "--neo4j-uri", default=os.getenv("NEO4J_URI", "bolt://localhost:7687")
    )
    p.add_argument("--neo4j-user", default=os.getenv("NEO4J_USER", "neo4j"))
    p.add_argument("--neo4j-password", default=os.getenv("NEO4J_PASSWORD"))
    p.add_argument(
        "--neo4j-database",
        default=os.getenv("NEO4J_DATABASE", "neo4j"),
    )
    p.add_argument(
        "--graphdb-endpoint",
        default=os.getenv(
            "GRAPHDB_ENDPOINT",
            "http://localhost:7200/repositories/shacl_employee_demo/statements",
        ),
    )
    p.add_argument(
        "--batch-size",
        type=int,
        default=int(os.getenv("BATCH_SIZE", "5000")),
    )
    p.add_argument(
        "--prefix",
        default=os.getenv("RDF_PREFIX", "https://opus-adeo.biz/"),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Process nodes and relationships without inserting into GraphDB",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max number of nodes and relationships to process",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if not args.neo4j_password:
        log.error("Neo4j password is required (--neo4j-password or NEO4J_PASSWORD)")
        sys.exit(1)

    export_neo4j_to_graphdb(
        neo4j_uri=args.neo4j_uri,
        user=args.neo4j_user,
        password=args.neo4j_password,
        database=args.neo4j_database,
        endpoint=args.graphdb_endpoint,
        batch_size=args.batch_size,
        prefix=args.prefix,
        dry_run=args.dry_run,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
