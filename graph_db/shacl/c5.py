import requests
REPOSITORY = "testing-kg-shacl"

endpoint = f"http://localhost:7200/repositories/{REPOSITORY}/statements"

data = """
@prefix ex: <http://example.com/> .

ex:Bob
    a ex:Person ;
    ex:name "Bob" .
"""

response = requests.post(
    endpoint,
    params={
        "context": "<http://example.com/g1>"
    },
    data=data,
    headers={
        "Content-Type": "text/turtle"
    }
)

print("Status:", response.status_code)
print(response.text)