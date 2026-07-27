import requests, os
from dotenv import load_dotenv
load_dotenv()

print('=== Adzuna Test ===')
adzuna_id = os.getenv('ADZUNA_APP_ID')
adzuna_key = os.getenv('ADZUNA_APP_KEY')
try:
    r = requests.get('https://api.adzuna.com/v1/api/jobs/fr/search/1', 
        params={'app_id': adzuna_id, 'app_key': adzuna_key, 'results_per_page': 3, 'what': 'Développeur Full-Stack', 'where': 'Paris'}, 
        timeout=15)
    print(f'Status: {r.status_code}')
    print(f'Headers: {dict(r.headers)}')
    if r.status_code == 200:
        data = r.json()
        print(f'Results: {len(data.get("results", []))}')
    else:
        print(f'Body: {r.text[:500]}')
except Exception as e:
    print(f'Error: {e}')