import pronto

ontology = pronto.Ontology("go-basic.obo")

term = ontology["GO:0008150"]

print(term)