import requests
from bs4 import BeautifulSoup

url = "http://10.107.194.70/conn/temp/ldap.php?user=ac42027"
response = requests.get(url)
print("--- RAW HTML START ---")
print(response.text)
print("--- RAW HTML END ---")

soup = BeautifulSoup(response.text, 'html.parser')
tablas = soup.find_all('table')
print(f"\nFound {len(tablas)} tables")

for i, tabla in enumerate(tablas):
    print(f"\nTable {i}:")
    for j, fila in enumerate(tabla.find_all('tr')):
        celdas = [td.get_text(strip=True) for td in fila.find_all(['td', 'th'])]
        print(f"  Row {j}: {celdas}")
