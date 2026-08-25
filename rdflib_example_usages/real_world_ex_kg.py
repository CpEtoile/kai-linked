from rdflib import Graph, Namespace, Literal
from rdflib.namespace import RDF

g = Graph()

MOVIE = Namespace("http://movies.org/")

g.add((MOVIE.Inception, RDF.type, MOVIE.Movie))
g.add((MOVIE.Inception, MOVIE.title, Literal("Inception")))
g.add((MOVIE.Inception, MOVIE.director,
       Literal("Christopher Nolan")))

query = """
SELECT ?title ?director
WHERE {
    ?m <http://movies.org/title> ?title .
    ?m <http://movies.org/director> ?director .
}
"""

for row in g.query(query):
    print(row)