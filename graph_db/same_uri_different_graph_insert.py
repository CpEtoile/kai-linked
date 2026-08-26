import requests

GRAPHDB_URL = "http://localhost:7200"
REPOSITORY = "testing-kg"

url = f"{GRAPHDB_URL}/repositories/{REPOSITORY}/statements"

sparql_update = """
INSERT DATA {

    GRAPH <https://test-star-war-kg.com/sourceA> {
        <https://swapi.co/resource/luke/1>
            <https://test-star-war-kg.com/height>
            "172" .
    }

    GRAPH <https://test-star-war-kg.com/sourceB> {
        <https://swapi.co/resource/luke/1>
            <https://test-star-war-kg.com/height>
            "175" .
    }
}
"""

response = requests.post(
    url,
    data=sparql_update,
    headers={
        "Content-Type": "application/sparql-update"
    },
    timeout=30,
)

response.raise_for_status()

print("Inserted!")