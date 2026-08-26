import requests

GRAPHDB_URL = "http://localhost:7200"
REPOSITORY = "testing-kg"

ttl = """
@prefix ex: <http://example.com/> .

ex:Alice ex:worksFor ex:Acme .
ex:Alice ex:livesIn ex:Paris .

ex:Bob ex:worksFor ex:Google .
ex:Bob ex:livesIn ex:London .
"""

url = f"{GRAPHDB_URL}/repositories/{REPOSITORY}/statements"

response = requests.post(
    url,
    data=ttl,
    headers={"Content-Type": "text/turtle"},
    timeout=30,
)

response.raise_for_status()

print("Data inserted!")