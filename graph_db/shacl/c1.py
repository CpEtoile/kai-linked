import requests
from rdflib import Graph


# ============================================================
# CONFIGURATION
# ============================================================

GRAPHDB_URL = "http://localhost:7200"
REPOSITORY = "testing-kg-shacl"

SPARQL_ENDPOINT = (
    f"{GRAPHDB_URL}/repositories/{REPOSITORY}"
)

STATEMENTS_ENDPOINT = (
    f"{GRAPHDB_URL}/repositories/{REPOSITORY}/statements"
)


# ============================================================
# 1. RDF DATA
# ============================================================

data = """
@prefix ex: <http://example.com/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ex:Alice
    a ex:Person ;
    ex:name "Alice" ;
    ex:age 25 .

ex:Bob
    a ex:Person ;
    ex:name "Bob" .

ex:Charlie
    a ex:Person ;
    ex:name "Charlie" ;
    ex:age "twenty" .
"""


# ============================================================
# 2. SHACL SHAPES
# ============================================================

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


# ============================================================
# 3. UPLOAD RDF DATA TO GRAPHDB
# ============================================================

def upload_data():

    print("Uploading RDF data...")

    response = requests.post(
        STATEMENTS_ENDPOINT,
        data=data.encode("utf-8"),
        headers={
            "Content-Type": "text/turtle"
        }
    )

    response.raise_for_status()

    print("RDF data uploaded successfully.")


# ============================================================
# 4. UPLOAD SHACL SHAPES
# ============================================================

def upload_shapes():

    print("Uploading SHACL shapes...")

    # SHACL shapes are normally kept separately from
    # your normal RDF data.

    SHACL_GRAPH = (
        "http://example.com/shapes"
    )

    response = requests.post(
        STATEMENTS_ENDPOINT,
        params={
            "context": f"<{SHACL_GRAPH}>"
        },
        data=shapes.encode("utf-8"),
        headers={
            "Content-Type": "text/turtle"
        }
    )

    response.raise_for_status()

    print("SHACL shapes uploaded successfully.")


# ============================================================
# 5. SEE WHAT IS IN GRAPHDB
# ============================================================

def show_data():

    print("\nCurrent data:")
    print("----------------------------")

    query = """
    PREFIX ex: <http://example.com/>

    SELECT ?person ?name ?age
    WHERE {
        ?person a ex:Person ;
                ex:name ?name .

        OPTIONAL {
            ?person ex:age ?age .
        }
    }
    """

    response = requests.get(
        SPARQL_ENDPOINT,
        params={
            "query": query
        },
        headers={
            "Accept": "application/sparql-results+json"
        }
    )

    response.raise_for_status()

    results = response.json()

    for row in results["results"]["bindings"]:

        person = row["person"]["value"]
        name = row["name"]["value"]

        age = row.get("age")

        if age:
            age = age["value"]
        else:
            age = "MISSING"

        print(
            f"{person} | {name} | age={age}"
        )


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    upload_data()

    upload_shapes()

    show_data()

    print("\nDone.")