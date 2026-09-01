import requests

GRAPHDB = "http://localhost:7200"
REPOSITORY = "testing-kg-shacl"

URL = (
    f"{GRAPHDB}/repositories/{REPOSITORY}/statements"
)

data = """
@prefix ex: <http://example.com/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:Alice
    a ex:Person ;
    ex:name "Alice" ;
    ex:age 25 .
"""

response = requests.post(
    URL,
    data=data.encode("utf-8"),
    headers={
        "Content-Type": "text/turtle"
    }
)

print("Status:", response.status_code)
print(response.text)