import pronto

ont = pronto.Ontology("go-basic.obo")

term = ont["GO:0008150"]

print("Term:", term.name)

for parent in term.superclasses(distance=2):
    print("Parent:", parent.name)
    print(parent)