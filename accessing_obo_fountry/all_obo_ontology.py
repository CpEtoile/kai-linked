import requests
import yaml

url = "https://obofoundry.org/registry/ontologies.yml"

response = requests.get(url)

# Force UTF-8
text = response.content.decode("utf-8", errors="replace")

registry = yaml.safe_load(text)

for ontology in registry["ontologies"][:2]:
    print(
        ontology
    )