import requests

GRAPHDB_URL = "http://localhost:7200"
REPOSITORY = "testing-kg"

url = f"{GRAPHDB_URL}/repositories/{REPOSITORY}"

query = """
SELECT ?heightA ?heightB
WHERE {

    GRAPH <https://test-star-war-kg.com/sourceA> {
        <https://swapi.co/resource/luke/1>
            <https://test-star-war-kg.com/height>
            ?heightA .
    }

    GRAPH <https://test-star-war-kg.com/sourceB> {
        <https://swapi.co/resource/luke/1>
            <https://test-star-war-kg.com/height>
            ?heightB .
    }
}
"""

response = requests.post(
    url,
    data={"query": query},
    headers={
        "Accept": "application/sparql-results+json"
    },
    timeout=30,
)

response.raise_for_status()

print(response.json())