import sys
from pathlib import Path
import requests
from rdflib import Graph


sys.path.insert(0, str(Path(__file__).parent))
from shacl_shape import shapes
from data import employee_data


def insert_turtle(turtle_data, graph_uri):

    response = requests.post(
        STATEMENTS_URL,
        params={
            "context": f"<{graph_uri}>"
        },
        data=turtle_data.encode("utf-8"),
        headers={
            "Content-Type": "text/turtle"
        }
    )

    print("Status:", response.status_code)

    if response.status_code >= 400:
        print(response.text)
        response.raise_for_status()

GRAPHDB = "http://localhost:7200"
REPOSITORY = "shacl_employee_demo"

STATEMENTS_URL = (
    f"{GRAPHDB}/repositories/{REPOSITORY}/statements"
)

VALIDATE_URL = (
    f"{GRAPHDB}/rest/repositories/{REPOSITORY}/validate/text"
)

G1 = "http://example.com/g1"
G2 = "http://example.com/g2"

SHACL_GRAPH = (
    "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"
)

# Step 1: Clear repository
print("Clearing repository...")
r = requests.delete(STATEMENTS_URL)
print("  Status:", r.status_code)

# Step 2: Upload SHACL shapes
print("Uploading SHACL shapes...")
insert_turtle(shapes, SHACL_GRAPH)

# Step 3: Upload employee data
print("Uploading employee data...")
insert_turtle(employee_data, G1)
