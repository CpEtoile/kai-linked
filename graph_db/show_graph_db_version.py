import requests

url = "http://localhost:7200"

response = requests.get(url)

print(response.status_code)
print(response.text[:1000])