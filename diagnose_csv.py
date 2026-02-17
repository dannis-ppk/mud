import csv
import os

data_dir = r"d:\dev\projects\MUD_the_age\data"
csv_path = os.path.join(data_dir, "commands.csv")

print(f"Reading {csv_path}...")
try:
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if 'skill power' in row['command']:
                print(f"Found row: {row}")
                aliases = row['aliases'].split(';')
                print(f"Raw aliases split: {aliases}")
                clean_aliases = [max_a.strip() for max_a in aliases]
                print(f"Clean aliases: {clean_aliases}")
                if 'p a' in clean_aliases:
                    print("SUCCESS: 'p a' alias found.")
                else:
                    print("FAILURE: 'p a' alias NOT found.")
except Exception as e:
    print(f"Error: {e}")
