from rdflib import Graph

g = Graph()

g.parse(
    "http://purl.obolibrary.org/obo/go.owl"
)

print("Number of triples:", len(g))

some_g = g[0:10]

for sg in some_g:
    print('sg-------------------')
    print(sg)
    print('sg-------------------fin')
