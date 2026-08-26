import requests

GRAPHDB_URL = "http://localhost:7200"
REPOSITORY = "testing-kg"

query = """
INSERT DATA {
    GRAPH <https://test-star-war-kg.com/g1> {

        <https://swapi.co/resource/clawdite/70>
            <https://test-star-war-kg.com/species>
            "Clawdite" .

    }
}
"""

url = f"{GRAPHDB_URL}/repositories/{REPOSITORY}/statements"

response = requests.post(
    url,
    data=query,
    headers={
        "Content-Type": "application/sparql-update"
    },
    timeout=30
)

print("Status:", response.status_code)
print("Response:", response.text)

response.raise_for_status()

print("Inserted into g1!")