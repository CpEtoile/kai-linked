import requests

term = "glucose"

url = f"https://www.ebi.ac.uk/ols4/api/search?q={term}"

response = requests.get(url)

data = response.json()

response = data["response"]


for doc in response["docs"]:
    print('doc-------------------------')
    print(doc)
    print('doc-------------------------fin')