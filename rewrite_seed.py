import re
path = 'c:\\Users\\eltonlo_house730\\Documents\\Repositories\\uo-price-tracker\\scripts\\seed_test_data.py'

with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

text = text.replace("def add_snap(flight, dt, fare, status='success'):", "def add_snap(flight, dt, fare, currency='HKD', status='success'):")
text = text.replace("currency='HKD' if status == 'success' else None,", "currency=currency if status == 'success' else None,")
text = text.replace("flight2, now - timedelta(days=i), 3500 + random.randint(-50, 50))", "flight2, now - timedelta(days=i), 3500 + random.randint(-50, 50), currency='JPY')")
text = text.replace("flight4, now - timedelta(days=i), 1200 + random.randint(-50, 50))", "flight4, now - timedelta(days=i), 1200 + random.randint(-50, 50), currency='TWD')")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
