import requests

url = "http://purl.obolibrary.org/obo/go/go-basic.obo"

response = requests.get(url)

with open("go-basic.obo", "wb") as f:
    f.write(response.content)

print("Downloaded")