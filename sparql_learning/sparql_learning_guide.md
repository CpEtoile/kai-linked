# Comprehensive Guide to SPARQL & SHACL for DIY Knowledge Graphs

Welcome to this comprehensive tutorial and reference guide based on the **DIY Knowledge Base** dataset. This document covers RDF data structures, SPARQL queries (from basic retrieval to advanced analytics), query keywords (`VALUES`, `UNION`, `BIND`), and SHACL data quality validation.

---

## 1. Datasets Overview

The examples in this guide operate across three core Turtle (`.ttl`) files:

1. **`diy_garden_taxonomy.ttl`**: SKOS taxonomy for garden planning, soil, tools, maintenance, and structures.
2. **`diy_tools_taxonomy.ttl`**: SKOS taxonomy covering hand tools, power tools, safety equipment, and workshop items.
3. **`diy_ontology.owl.ttl`**: OWL ontology defining domain classes (`diy:Project`, `diy:Tool`, `diy:Material`, `diy:GardenActivity`) and properties (`diy:usesTool`, `diy:estimatedDurationMinutes`, etc.).

---

## 2. Basic SPARQL Queries

### Query 1: Retrieve SKOS Concepts with Optional Metadata
Retrieves concepts from the taxonomy along with their optional definitions or broader hierarchy relationships.

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?label ?definition ?broader
WHERE {
  ?concept a skos:Concept ;
           skos:prefLabel ?label .
  
  # OPTIONAL block: returns definitions if available
  OPTIONAL { 
    ?concept skos:definition ?definition . 
  }
  
  # OPTIONAL block: returns broader concepts if present
  OPTIONAL { 
    ?concept skos:broader ?broader . 
  }
}
ORDER BY ?label
```

---

### Query 2: Inspecting an Entity Across Graphs (`diy:Drill`)
Uses a `UNION` pattern to retrieve all triples where the `Drill` resource acts as either the **subject** or the **object** across both ontology and taxonomy definitions.

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX diy: <https://example.org/diy#>
PREFIX diy-tools: <https://example.org/diy/tools#>

SELECT ?predicate ?object
WHERE {
  {
    # Case 1: Drill is the subject (attributes, types, labels)
    VALUES ?drill { diy:Drill diy-tools:Drill }
    ?drill ?predicate ?object .
  }
  UNION
  {
    # Case 2: Drill is the object (e.g., projects that use the Drill)
    VALUES ?drill { diy:Drill diy-tools:Drill }
    ?subject ?predicate ?drill .
    BIND(?subject AS ?object)
  }
}
```

---

## 3. SPARQL Keyword Breakdown

| Keyword | Core Function | Description & Usage |
| :--- | :--- | :--- |
| **`VALUES`** | Inline Data Binding | Restricts query variables to a fixed list of URIs or literals directly within the query. |
| **`UNION`** | Alternative Match (Logical OR) | Combines results from multiple graph patterns. Matches if pattern A **OR** pattern B is true. |
| **`BIND`** | Expression Assignment | Evaluates an expression/function and assigns the result to a **new** variable name. |

### Practical Example Combining `VALUES`, `UNION`, and `BIND`:

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX diy: <https://example.org/diy#>

SELECT ?item ?label ?type
WHERE {
  {
    # VALUES assigns specific URIs directly
    VALUES ?item { diy:GardenSpade diy:GardenFork }
    ?item skos:prefLabel ?label .
    
    # BIND creates a new string variable
    BIND("Taxonomy Item" AS ?type)
  }
  UNION
  {
    # UNION branches into a second alternative pattern
    ?item a diy:Project ;
          diy:projectName ?label .
          
    BIND("Ontology Project" AS ?type)
  }
}
```

---

## 4. Working with `BIND`

In SPARQL, `BIND` assigns the result of an expression to a variable: `BIND(<expression> AS ?newVariable)`.

### 1. String Concatenation (`CONCAT`)
```sparql
PREFIX diy: <https://example.org/diy#>

SELECT ?project ?fullDescription WHERE {
  ?project diy:projectName ?name ;
           diy:difficultyLevel ?level .

  # Combines ?name and ?level into ?fullDescription
  BIND(CONCAT(?name, " - Level: ", ?level) AS ?fullDescription)
}
```

### 2. Numerical Calculations
```sparql
PREFIX diy: <https://example.org/diy#>

SELECT ?project ?durationInHours WHERE {
  ?project diy:estimatedDurationMinutes ?minutes .

  # Converts minutes to hours
  BIND(?minutes / 60.0 AS ?durationInHours)
}
```

### Note on Binding Multiple Variables:
A single `BIND` statement cannot assign multiple variables at once (e.g., `BIND('a' AS ?A 'b' AS ?B)` is invalid). Instead, use sequential `BIND` calls or `VALUES`:

```sparql
# Method A: Sequential BINDs
BIND('a' AS ?A)
BIND('b' AS ?B)

# Method B: Multi-variable VALUES clause
VALUES (?A ?B) { ('a' 'b') }
```

---

## 5. Advanced SPARQL Analytics Query

This query uses advanced SPARQL features including **property paths (`+`)**, **aggregations (`COUNT`, `GROUP_CONCAT`)**, **`GROUP BY`**, **`HAVING`**, and **`OPTIONAL` with `VALUES`** on `diy_garden_taxonomy.ttl`.

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX diy: <https://example.org/diy/garden#>

SELECT 
  ?topConcept 
  ?topLabel 
  (COUNT(DISTINCT ?narrowerConcept) AS ?totalSubConcepts)
  (GROUP_CONCAT(DISTINCT ?targetLabel; SEPARATOR=", ") AS ?foundTargetConcepts)
WHERE {
  # 1. Target the main Taxonomy Scheme
  diy:GardenTaxonomy skos:hasTopConcept ?topConcept .
  ?topConcept skos:prefLabel ?topLabel .

  # 2. Transitive property path (skos:narrower+) to find all nested sub-concepts
  ?topConcept skos:narrower+ ?narrowerConcept .

  # 3. OPTIONAL lookup with inline VALUES for target items
  OPTIONAL {
    VALUES ?targetConcept { diy:Composting diy:Mulching diy:PruningShears }
    
    ?topConcept skos:narrower+ ?targetConcept .
    ?targetConcept skos:prefLabel ?targetLabel .
  }
}
GROUP BY ?topConcept ?topLabel
# 4. Filter groups to show branches with more than 3 sub-concepts
HAVING (COUNT(DISTINCT ?narrowerConcept) > 3)
ORDER BY DESC(?totalSubConcepts)
```

---

## 6. SHACL Constraints (`diy_shapes.ttl`)

To maintain graph consistency across all ontology and taxonomy files, use the following SHACL shapes definition file:

```ttl
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix diy: <https://example.org/diy#> .
@prefix diy-shapes: <https://example.org/diy/shapes#> .

#################################################################
# 1. SKOS Taxonomy Shapes
#################################################################

diy-shapes:ConceptSchemeShape
    a sh:NodeShape ;
    sh:targetClass skos:ConceptScheme ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:message "A ConceptScheme must have at least one preferred string label." ;
    ] ;
    sh:property [
        sh:path skos:hasTopConcept ;
        sh:minCount 1 ;
        sh:class skos:Concept ;
        sh:message "A ConceptScheme must link to valid SKOS Concepts via skos:hasTopConcept." ;
    ] .

diy-shapes:ConceptShape
    a sh:NodeShape ;
    sh:targetClass skos:Concept ;
    sh:property [
        sh:path skos:prefLabel ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:message "Every Concept must have at least one skos:prefLabel." ;
    ] ;
    sh:property [
        sh:path skos:broader ;
        sh:or (
            [ sh:class skos:Concept ]
            [ sh:class skos:ConceptScheme ]
        ) ;
        sh:message "skos:broader targets must be a skos:Concept or skos:ConceptScheme." ;
    ] .

#################################################################
# 2. Ontology Core Class Shapes
#################################################################

diy-shapes:ProjectShape
    a sh:NodeShape ;
    sh:targetClass diy:Project ;
    sh:property [
        sh:path diy:projectName ;
        sh:minCount 1 ;
        sh:maxCount 1 ;
        sh:datatype xsd:string ;
        sh:message "A Project must have exactly one string project name." ;
    ] ;
    sh:property [
        sh:path diy:estimatedDurationMinutes ;
        sh:datatype xsd:nonNegativeInteger ;
        sh:message "Duration in minutes must be a non-negative integer." ;
    ] ;
    sh:property [
        sh:path diy:difficultyLevel ;
        sh:datatype xsd:string ;
        sh:message "Difficulty level must be a string." ;
    ] ;
    sh:property [
        sh:path diy:usesTool ;
        sh:class diy:Tool ;
        sh:message "Values of diy:usesTool must be instances of diy:Tool." ;
    ] ;
    sh:property [
        sh:path diy:usesMaterial ;
        sh:class diy:Material ;
        sh:message "Values of diy:usesMaterial must be instances of diy:Material." ;
    ] ;
    sh:property [
        sh:path diy:performedIn ;
        sh:class diy:Location ;
        sh:message "Values of diy:performedIn must be instances of diy:Location." ;
    ] .

diy-shapes:GardenActivityShape
    a sh:NodeShape ;
    sh:targetClass diy:GardenActivity ;
    sh:property [
        sh:path diy:usesGardenTool ;
        sh:class diy:GardenTool ;
        sh:message "diy:usesGardenTool must link to a diy:GardenTool instance." ;
    ] ;
    sh:property [
        sh:path diy:involvesPlant ;
        sh:class diy:Plant ;
        sh:message "diy:involvesPlant must link to a diy:Plant instance." ;
    ] .

diy-shapes:SafetyRequirementShape
    a sh:NodeShape ;
    sh:targetClass diy:SafetyRequirement ;
    sh:property [
        sh:path diy:hasDescription ;
        sh:minCount 1 ;
        sh:datatype xsd:string ;
        sh:message "Safety requirements must include a text description." ;
    ] .
```

---

## 7. Valid SPARQL vs. SHACL Validation

The following SPARQL `INSERT DATA` query is **100% syntactically valid SPARQL** and will execute without errors in a SPARQL engine. However, when loaded into a SHACL-enabled dataset, the SHACL engine will **reject** the transaction due to schema rule violations.

```sparql
PREFIX diy: <https://example.org/diy#>
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

INSERT DATA {
  # Violation 1: Missing required skos:prefLabel
  diy:InvalidConcept a skos:Concept .

  # Violation 2 & 3: Invalid duration datatype (string) and incorrect class target for usesTool (Material)
  diy:BrokenBuildProject a diy:Project ;
      diy:projectName "Broken Garden Shed" ;
      diy:estimatedDurationMinutes "120 minutes" ;  # Expected: xsd:nonNegativeInteger
      diy:usesTool diy:Plywood .                     # Expected: diy:Tool instance

  diy:Plywood a diy:Material .
}
```

### Why SHACL Rejects This Data:
1. `diy:InvalidConcept` fails `diy-shapes:ConceptShape` (missing mandatory `skos:prefLabel`).
2. `diy:BrokenBuildProject` fails `diy-shapes:ProjectShape`:
   - `"120 minutes"` is an `xsd:string`, not `xsd:nonNegativeInteger`.
   - `diy:Plywood` is typed as `diy:Material`, but `diy:usesTool` requires an instance of `diy:Tool`.
