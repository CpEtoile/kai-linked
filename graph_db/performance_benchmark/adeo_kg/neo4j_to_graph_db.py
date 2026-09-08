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
):
    log.info("Connecting to Neo4j at %s ...", neo4j_uri)
    driver = GraphDatabase.driver(neo4j_uri, auth=(user, password))
    driver.verify_connectivity()
    log.info("Neo4j connected.")

    with driver.session(database=database) as session:
        # 1. Export Nodes -> Turtle triples
        log.info("--- Phase 1: Exporting Nodes ---")
        offset = 0
        total_nodes = 0
        while True:
            res = session.run(
                "MATCH (n) RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS props "
                "ORDER BY elementId(n) SKIP $offset LIMIT $limit",
                offset=offset,
                limit=batch_size,
            )
            records = list(res)
            if not records:
                break

            triples = []
            for r in records:
                s = node_to_uri(r["id"], prefix)
                for lbl in r["labels"]:
                    triples.append(
                        f"{s} <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> <{prefix}class/{lbl}> ."
                    )
                for k, v in r["props"].items():
                    if v is not None:
                        triples.append(f"{s} <{prefix}prop/{k}> {value_to_rdf(v)} .")

            if triples:
                upload_turtle_batch(endpoint, "\n".join(triples))
                total_nodes += len(records)
                log.info("  Uploaded %d nodes (total: %d)", len(records), total_nodes)

            offset += batch_size

        # 2. Export Relationships -> Turtle triples
        log.info("--- Phase 2: Exporting Relationships ---")
        offset = 0
        total_rels = 0
        while True:
            res = session.run(
                "MATCH (a)-[r]->(b) "
                "RETURN elementId(a) AS src, elementId(b) AS tgt, type(r) AS rel_type, properties(r) AS props "
                "ORDER BY elementId(r) SKIP $offset LIMIT $limit",
                offset=offset,
                limit=batch_size,
            )
            records = list(res)
            if not records:
                break

            triples = []
            for r in records:
                src_uri = node_to_uri(r["src"], prefix)
                tgt_uri = node_to_uri(r["tgt"], prefix)
                rel_pred = f"<{prefix}rel/{r['rel_type']}>"
                triples.append(f"{src_uri} {rel_pred} {tgt_uri} .")

            if triples:
                upload_turtle_batch(endpoint, "\n".join(triples))
                total_rels += len(records)
                log.info("  Uploaded %d relationships (total: %d)", len(records), total_rels)

            offset += batch_size

    driver.close()
    log.info("=== Migration complete: %d nodes, %d relationships ===", total_nodes, total_rels)


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
        default=os.getenv("RDF_PREFIX", "http://example.org/employee/"),
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
    )


if __name__ == "__main__":
    main()
