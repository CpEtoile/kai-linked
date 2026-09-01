import requests

GRAPHDB = "http://localhost:7200"
REPOSITORY = "testing-kg-shacl"

STATEMENTS_URL = (
    f"{GRAPHDB}/repositories/{REPOSITORY}/statements"
)

SHACL_GRAPH = (
    "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"
)


# Step 3: Try uploading bad data (missing ex:age)
bad_data = """
@prefix ex: <http://example.com/> .

ex:Dave
    a ex:Person ;
    ex:name "Dave" .
"""

print("Uploading bad data (missing age)...")
response = requests.post(
    STATEMENTS_URL,
    data=bad_data.encode("utf-8"),
    headers={"Content-Type": "text/turtle"},
)
print(f"  HTTP status: {response.status_code}")
print("Response:")
print(response.text)
