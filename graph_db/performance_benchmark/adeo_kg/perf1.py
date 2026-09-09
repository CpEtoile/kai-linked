import time
import statistics
import random
from SPARQLWrapper import SPARQLWrapper, JSON

endpoint = "http://localhost:7200/repositories/test-adeo-kg"

# example 5764 Électricité  2719 consommable  840 accessoire

subtree_sparql_from_neo4j = """
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX adeo: <https://opus-adeo.poolparty.biz/COMMONTAXO/>

SELECT DISTINCT ?concept ?parent ?parentCode ?childrenCount ?label
WHERE {
  VALUES ?root { adeo:840 }

  ?child a skos:Concept ;
         skos:broader* ?root ;
         skos:prefLabel ?label .
  FILTER(?child != ?root)
  FILTER(langMatches(lang(?label), "fr"))

  OPTIONAL {
    ?child skos:broader ?parent .
    ?parent a skos:Concept .
    BIND(REPLACE(STR(?parent), "^.*[/#]", "") AS ?parentCode)
  }

  OPTIONAL {
    SELECT ?child (COUNT(?subChild) AS ?childrenCount)
    WHERE {
      ?subChild skos:broader ?child .
      ?subChild skos:prefLabel ?subChildLabel .
      FILTER(langMatches(lang(?subChildLabel), "fr"))
    }
    GROUP BY ?child
  }

  BIND(?child AS ?concept)
}
ORDER BY ?childrenCount ?label"""

queries = {
    "simple": """
        SELECT ?s ?p ?o
        WHERE {
          ?s ?p ?o .
        }
        ORDER BY ?s
        LIMIT 1000
        OFFSET 200
    """,

    "optional": """
        PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
        PREFIX adeo: <https://opus-adeo.poolparty.biz/COMMONTAXO/>
        
        SELECT ?property ?value ?broader
        WHERE {
          adeo:2777 ?property ?value .
          
          OPTIONAL {
            adeo:2777 skos:broader ?broader .
          }
        }
        ORDER BY ?broader
        LIMIT 100
    """,

    "adeo_kg": subtree_sparql_from_neo4j
}

def benchmark(query, runs=10):
    times = []

    for _ in range(runs):
        sparql = SPARQLWrapper(endpoint)
        sparql.setQuery(query)
        sparql.setReturnFormat(JSON)

        start = time.perf_counter()

        results = sparql.queryAndConvert()

        results_list = list(results["results"]["bindings"])
        length = len(results_list)
        print(f"we have get out {length} results")

        ran = random.randint(0, min(200, length - 1))  # includes 0 and 2
        print(f"And the {ran} number of list is {results_list[ran]}")
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    return {
        "min": min(times),
        "median": statistics.median(times),
        "mean": statistics.mean(times),
        "max": max(times),
    }


for name, query in queries.items():
    stats = benchmark(query)

    print(f"\n{name}")
    print(f"min:    {stats['min']:.4f}s")
    print(f"median: {stats['median']:.4f}s")
    print(f"mean:   {stats['mean']:.4f}s")
    print(f"max:    {stats['max']:.4f}s")

