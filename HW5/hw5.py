"""
Starter code: Fetch covid cases data for Utah from the CDC API

Dataset:
Weekly United States COVID-19 Cases by State (ARCHIVED)

IMPORTANT:
- This dataset is WEEKLY, not daily.  The day shown is the end of week date.
- This starter code prints RAW JSON text.
- You are expected to parse and analyze the data.
"""

import requests
import json

DATASET_ID = "pwn4-m3yp"
BASE_URL = f"https://data.cdc.gov/resource/{DATASET_ID}.json"

params = {
    "$where": "state='UT' AND end_date >= '2020-01-01' AND end_date <= '2023-12-31'",
    "$order": "end_date ASC"
}
req = requests.get(BASE_URL, params=params)
print(req.text)
 
dates = []
new_cases = []


key_new = "new_cases"
key_date = "date_updated"

lst = json.loads(req.text)
fil = open("utah.json", "w")
json.dump(lst, fil, indent=2)
print(lst)

input("pause")

for d in lst:
    print(d)
    new_cases.append(d[key_new])
    dates.append(d[key_date])


