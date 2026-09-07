GRAPHDB - RDF and SPARQL Learning
===============================

- Graph storage compared to Neo4j (e.g., https://example.org/diy/garden#Mowing)
    - Triple-based only: a node cannot hold more than one property.
    - As a consequence, for the same data, graph DBs have many more edges/relations than Neo4j.
- SKOS is for taxonomy, and OWL is for ontology.
- `skos:broader`, `owl:Class`, and `owl:subClassOf` all have global references.
    - Inference is direct, with no extra algorithm needed (RDF libs, SHACL, etc.).
    - For example, `narrower` is the inverse of `broader`.
    - Some relations are transitive, and others are not.
- Use the default graph for ontologies.
  - Use named graphs for different taxonomy sources.