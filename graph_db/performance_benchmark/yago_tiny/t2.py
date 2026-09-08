import requests

url = "http://localhost:7200/repositories/shacl_employee_demo"

queries = {
    "simple": """
        SELECT ?s ?p ?o
        WHERE {
            ?s ?p ?o
        }
        LIMIT 100
    """,

    "optional": """
        SELECT ?person ?name ?birthDate
        WHERE {
            ?person <http://schema.org/name> ?name .
            OPTIONAL {
                ?person <http://schema.org/birthDate> ?birthDate .
            }
        }
        LIMIT 100
    """
}

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