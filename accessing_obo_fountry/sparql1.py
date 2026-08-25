from rdflib import Graph

g = Graph()
# g.parse(
#     "https://purl.obolibrary.org/obo/go.owl",
#     format="xml"
# )
# OR to load it locally after downloading
g.parse("go.owl")

query = """
SELECT ?label
WHERE {
    ?entity rdfs:label ?label .
}
LIMIT 4
"""

q2 = """
SELECT ?predicate ?object
WHERE {
    <http://purl.obolibrary.org/obo/GO_0008150>
        ?predicate ?object .
}
limit 4
"""

for row in g.query(q2):
    print(f"row start---------------------------------")
    print(row)
    print(f"row end------------------------------")
