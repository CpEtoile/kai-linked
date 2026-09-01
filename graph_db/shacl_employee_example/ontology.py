
ontology = """
@prefix ex: <http://example.com/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .

# Manager is a subclass of Employee
ex:Manager
    rdfs:subClassOf ex:Employee .

# Developer is also an Employee
ex:Developer
    rdfs:subClassOf ex:Employee .

# manages is a subproperty of supervises
ex:manages
    rdfs:subPropertyOf ex:supervises .
"""