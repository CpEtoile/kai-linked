---
name: sparql-diy-knowledge-graphs
description: Use this skill when working with SPARQL queries, SKOS taxonomies, OWL ontologies, RDF graphs, and SHACL validation for DIY knowledge graphs.
---

# SPARQL + SHACL + SKOS Skill

This skill covers the practical workflow for exploring, querying, and validating RDF knowledge graphs based on the DIY ontology and taxonomy examples.

## What this skill is for

Use this skill when you need to:
- query RDF datasets with SPARQL
- inspect RDF triples and graph structure
- follow SKOS hierarchies such as `skos:broader` and `skos:narrower`
- query OWL classes and properties alongside taxonomy concepts
- validate graph quality with SHACL constraints
- reconcile equivalent entities across multiple namespaces using `owl:sameAs` or `skos:exactMatch`

## Core dataset model

The DIY knowledge graph usually combines:
- `diy_ontology.owl.ttl`: OWL ontology with classes, properties, and individuals
- `diy_tools_taxonomy.ttl`: SKOS concepts for tools and workshop items
- `diy_garden_taxonomy.ttl`: SKOS concepts for garden planning and maintenance
- `diy_shapes.ttl`: SHACL shape constraints for graph validation

The basic RDF pattern is:

```text
Subject -> Predicate -> Object
```

Example:

```text
diy:BuildRaisedBed -> diy:usesTool -> diy:Drill

diy:Drill -> rdf:type -> diy:PowerTool
```

## SPARQL fundamentals

### Query shape

```sparql
PREFIX diy: <https://example.org/diy#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?projectName ?toolLabel
WHERE {
  ?project a diy:Project ;
           diy:projectName ?projectName ;
           diy:usesTool ?tool .

  ?tool rdfs:label ?toolLabel .
}
```

### Common syntax

- `?variable`: query variable
- `a`: shorthand for `rdf:type`
- `;`: same subject, multiple predicates
- `.`: end of a triple pattern
- `OPTIONAL { ... }`: return optional matches without failing the whole query
- `FILTER(...)`: restrict results
- `ORDER BY`: sort output
- `LIMIT n`: cap rows

## Useful SPARQL patterns

### 1. Read raw triples

```sparql
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o .
}
LIMIT 50
```

### 2. Query SKOS concepts and labels

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?label ?broader
WHERE {
  ?concept a skos:Concept ;
           skos:prefLabel ?label .

  OPTIONAL { ?concept skos:broader ?broader . }
}
ORDER BY ?label
```

### 3. Explore taxonomy hierarchies

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?parentLabel ?childLabel
WHERE {
  ?child skos:broader ?parent ;
         skos:prefLabel ?childLabel .
  ?parent skos:prefLabel ?parentLabel .
}
ORDER BY ?parentLabel ?childLabel
```

### 4. Query projects and their tool usage

```sparql
PREFIX diy: <https://example.org/diy#>

SELECT ?project ?name ?difficulty ?duration
WHERE {
  ?project a diy:Project ;
           diy:projectName ?name .

  OPTIONAL { ?project diy:difficultyLevel ?difficulty }
  OPTIONAL { ?project diy:estimatedDurationMinutes ?duration }
}
ORDER BY ?duration
```

### 5. Use UNION to match two alternative patterns

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX diy: <https://example.org/diy#>
PREFIX diy-tools: <https://example.org/diy/tools#>

SELECT ?predicate ?object
WHERE {
  {
    VALUES ?drill { diy:Drill diy-tools:Drill }
    ?drill ?predicate ?object .
  }
  UNION
  {
    VALUES ?drill { diy:Drill diy-tools:Drill }
    ?subject ?predicate ?drill .
    BIND(?subject AS ?object)
  }
}
```

## Useful SPARQL keywords

### VALUES

Restricts variables to a fixed list of URIs or literals.

```sparql
VALUES ?item { diy:GardenSpade diy:GardenFork }
```

### UNION

Combines alternative graph patterns using logical OR semantics.

### BIND

Assigns an expression output to a new variable.

```sparql
BIND(CONCAT(?name, " - Level: ", ?level) AS ?fullDescription)
```

```sparql
BIND(?minutes / 60.0 AS ?durationInHours)
```

### Property paths

Useful for navigating nested taxonomy relationships.

```sparql
?topConcept skos:narrower+ ?narrowerConcept .
```

## SHACL validation workflow

Use SHACL to enforce quality constraints on the RDF graph.

Example shape:

```ttl
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .

[] a sh:NodeShape ;
  sh:targetClass skos:ConceptScheme ;
  sh:property [
    sh:path skos:prefLabel ;
    sh:minCount 1 ;
    sh:datatype xsd:string ;
  ] .
```

Important SHACL checks often include:
- concept schemes must have labels
- required properties must exist
- node types must match expected classes
- values must follow datatype constraints

## Namespace alignment tips

The ontology files and taxonomy files may use different namespaces. When querying across them, align equivalent entities with:
- `skos:exactMatch`
- `owl:sameAs`

Example:

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>

SELECT ?a ?b
WHERE {
  ?a skos:exactMatch ?b .
}
```

## Typical reasoning process

1. Start with a simple `SELECT * WHERE { ?s ?p ?o } LIMIT 50`
2. Identify the relevant classes and properties
3. Add `FILTER`, `VALUES`, and `OPTIONAL` to narrow the result set
4. Use `skos:broader`, `skos:narrower`, or `rdfs:subClassOf` to traverse hierarchy
5. Validate with SHACL after data updates
6. Reconcile namespace mismatches before cross-dataset joins

## Quick checklist

- `rdf:type` is the class assertion
- `skos:Concept` marks taxonomy items
- `skos:ConceptScheme` marks the taxonomy itself
- `skos:broader` indicates parent concept
- `skos:prefLabel` is a common human-readable label
- `OPTIONAL` prevents missing values from eliminating rows
- `UNION` covers alternate patterns
- `BIND` creates derived values
- SHACL validates consistency and required structure

## Typical query templates

### Concept lookup by label

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?label
WHERE {
  ?concept a skos:Concept ;
           skos:prefLabel ?label .
  FILTER(LCASE(STR(?label)) CONTAINS "saw")
}
```

### Hierarchy traversal with transitive closure

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?parent ?child
WHERE {
  ?child skos:broader+ ?parent .
}
```

### Aggregate taxonomy sizes

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?topConcept (COUNT(?narrowerConcept) AS ?count)
WHERE {
  ?topConcept skos:narrower+ ?narrowerConcept .
}
GROUP BY ?topConcept
ORDER BY DESC(?count)
```

## Final principle

Treat the graph as a connected set of triples. Start simple, inspect the data, then refine with filters, joins, hierarchy traversal, and validation rules. This is the core workflow behind successful SPARQL and SHACL work on DIY RDF knowledge graphs.
