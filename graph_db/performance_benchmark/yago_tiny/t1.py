import time
import statistics
import random
from SPARQLWrapper import SPARQLWrapper, JSON

# endpoint = "http://localhost:3030/yago/sparql"
endpoint = "http://localhost:7200/repositories/shacl_employee_demo"

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
        PREFIX schema: <http://schema.org/>
        PREFIX yago: <http://yago-knowledge.org/resource/>
        
        SELECT ?property ?value ?name ?foundingDate
        WHERE {
          yago:Air_New_Zealand ?property ?value .
          
          OPTIONAL {
            yago:Air_New_Zealand schema:name ?name .
          }
          OPTIONAL {
            yago:Air_New_Zealand schema:foundingDate ?foundingDate .
          }
        }
        ORDER BY ?foundingDate
        LIMIT 100
    """
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

        ran = random.randint(0, 10)  # includes 0 and 10
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