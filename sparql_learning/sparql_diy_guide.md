# SPARQL Quick Start Guide: Learning through DIY Data

This guide covers the core concepts of **SPARQL** (SPARQL Protocol and RDF Query Language) using a hands-on, practical dataset comprising a DIY project ontology, a tool taxonomy, and a garden taxonomy.

---

## 1. Key Concepts & Data Architecture

RDF data is structured as three-part statements called **triples**:
$$\text{Subject} \longrightarrow \text{Predicate} \longrightarrow \text{Object}$$

### Example Triples
* `diy:BuildRaisedBed` $\rightarrow$ `diy:usesTool` $\rightarrow$ `diy:Drill`
* `diy:Drill` $\rightarrow$ `rdf:type` $\rightarrow$ `diy:PowerTool`

### Dataset Breakdown

```
                         ┌── SKOS Tool Taxonomy (diy_tools_taxonomy.ttl)
                         │   └── Concepts, skos:broader, skos:prefLabel
                         │
DIY Knowledge Graph ─────┼── SKOS Garden Taxonomy (diy_garden_taxonomy.ttl)
                         │   └── Concepts, skos:broader, skos:prefLabel
                         │
                         └── OWL Ontology (diy_ontology.owl.ttl)
                             └── Classes, Object/Data Properties, Individuals
```

> **Note on Aligning Namespaces:** 
> The OWL ontology and SKOS taxonomies use separate namespaces (e.g., `diy:Drill` vs `tools:Drill`). To execute cross-dataset queries, link equivalent entities using `skos:exactMatch` or `owl:sameAs`.

---

## 2. Basic Query Structure

Every SPARQL query follows a simple pattern: define the prefixes, choose the variables to display (`SELECT`), and match patterns in the graph (`WHERE`).

```sparql
PREFIX diy:  <https://example.org/diy#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?projectName ?toolLabel
WHERE {
  ?project a diy:Project ;
           diy:projectName ?projectName ;
           diy:usesTool ?tool .
  
  ?tool rdfs:label ?toolLabel .
}
```

* **`?variable`**: Variables start with `?` and act as placeholders that SPARQL fills with matching data.
* **`a`**: Shorthand for `rdf:type`.
* **`;` (Semicolon)**: Chains multiple predicates for the *same* subject.
* **`.` (Period)**: Ends a triple pattern.

---

## 3. Core SPARQL Toolkit

| Syntax / Operator | Purpose | Example Pattern |
| :--- | :--- | :--- |
| `OPTIONAL { ... }` | Returns results even if the inner pattern is missing. | `OPTIONAL { ?project diy:difficultyLevel ?diff }` |
| `FILTER(...)` | Filters results based on conditional expressions. | `FILTER(CONTAINS(LCASE(STR(?label)), "saw"))` |
| `ORDER BY` | Sorts output values (ascending by default). | `ORDER BY DESC(?duration)` |
| `LIMIT n` | Restricts the total number of returned rows. | `LIMIT 10` |
| `BIND(... AS ?var)` | Assigns a calculated or formatted value to a new variable. | `BIND(?label AS ?equipmentName)` |

---

## 4. Query Cheat Sheet by Use Case

### A. Graph Exploration

**Inspect raw triples (First step in any graph):**
```sparql
SELECT ?s ?p ?o
WHERE {
  ?s ?p ?o .
}
LIMIT 50
```

**Find all classes and labels:**
```sparql
PREFIX owl:  <http://www.w3.org/2002/07/owl#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?class ?label
WHERE {
  ?class a owl:Class .
  OPTIONAL { ?class rdfs:label ?label }
}
ORDER BY ?label
```

---

### B. Ontology & Hierarchy Navigation

**Explore Class Subclass Relationships:**
```sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?parent ?child
WHERE {
  ?child rdfs:subClassOf ?parent .
}
ORDER BY ?parent ?child
```

**Explore SKOS Taxonomy Hierarchies:**
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

---

### C. Project Knowledge Queries

**Find Project Details (Name, Difficulty, Duration):**
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

**Get Tools and Safety Equipment Required for Projects:**
```sparql
PREFIX diy:  <https://example.org/diy#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?projectName ?toolLabel ?safetyLabel
WHERE {
  ?project a diy:Project ;
           diy:projectName ?projectName ;
           diy:usesTool ?tool ;
           diy:requiresSafetyEquipment ?safety .
           
  ?tool rdfs:label ?toolLabel .
  ?safety rdfs:label ?safetyLabel .
}
```

---

### D. Advanced Graph Pattern Matching

**Find Projects Using Specific Tool Types (e.g., Power Tools):**
```sparql
PREFIX diy: <https://example.org/diy#>

SELECT ?projectName ?tool
WHERE {
  ?project a diy:Project ;
           diy:projectName ?projectName ;
           diy:usesTool ?tool .
           
  ?tool a diy:PowerTool .
}
```

---

## 5. Recommended SPARQL Learning Path

```
 1. SELECT & WHERE
       │
 2. Variables (?x) & Triple Patterns
       │
 3. Multiple Patterns & Joins (;)
       │
 4. OPTIONAL Patterns
       │
 5. Filtering (FILTER, CONTAINS, LCASE)
       │
 6. Ordering & Constraints (ORDER BY, LIMIT)
       │
 7. Aggregations (COUNT, GROUP BY)
       │
 8. Property Paths & Reasoning (owl:sameAs, skos:exactMatch)
```
