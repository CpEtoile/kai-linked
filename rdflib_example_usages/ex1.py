from rdflib import Graph, URIRef, Literal

g = Graph()

alice = URIRef("http://example.org/Alice")
knows = URIRef("http://example.org/knows")
bob = URIRef("http://example.org/Bob")

g.add((alice, knows, bob))

for s, p, o in g:
    print(s, p, o)