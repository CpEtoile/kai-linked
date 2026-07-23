from rdflib import Graph

g = Graph()
g.parse("go.owl")

query = """
SELECT ?label
WHERE {
    ?entity rdfs:label ?label .
}
LIMIT 10
"""

for row in g.query(query):
    print(row.label)