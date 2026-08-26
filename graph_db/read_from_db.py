import requests

url = "http://localhost:7200/repositories/testing-kg"

query = """
PREFIX ex: <http://example.com/>

SELECT ?person ?company ?city
WHERE {
    ?person ex:worksFor ?company .
    ?person ex:livesIn ?city .
}
"""

response = requests.post(
    url,
    data={"query": query},
    headers={"Accept": "application/sparql-results+json"},
    timeout=30,
)

response.raise_for_status()

results = response.json()

for row in results["results"]["bindings"]:
    print(
        row["person"]["value"],
        "works for",
        row["company"]["value"],
        "and lives in",
        row["city"]["value"],
    )