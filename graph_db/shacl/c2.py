import requests

GRAPHDB = "http://localhost:7200"
REPOSITORY = "testing-kg-shacl"

STATEMENTS_URL = (
    f"{GRAPHDB}/repositories/{REPOSITORY}/statements"
)

SHACL_GRAPH = (
    "http://rdf4j.org/schema/rdf4j#SHACLShapeGraph"
)


shapes = """
@prefix ex: <http://example.com/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:PersonShape
    a sh:NodeShape ;

    sh:targetClass ex:Person ;

    sh:property [
        sh:path ex:name ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
    ] ;

    sh:property [
        sh:path ex:age ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:integer ;
    ] .
"""


response = requests.post(
    STATEMENTS_URL,
    params={
        "context": f"<{SHACL_GRAPH}>"
    },
    data=shapes.encode("utf-8"),
    headers={
        "Content-Type": "text/turtle"
    }
)

print("Status:", response.status_code)
print(response.text)