import csv
import os

ITEMS_FILE = 'd:/dev/projects/MUD_the_age/data/items.csv'
TEMP_FILE = 'd:/dev/projects/MUD_the_age/data/items_temp.csv'

print("Script started.")
def update_csv_durability():
    print(f"Checking {ITEMS_FILE}")
    if not os.path.exists(ITEMS_FILE):
        print(f"File not found: {ITEMS_FILE}")
        return

    try:
        with open(ITEMS_FILE, 'r', encoding='utf-8-sig') as f_in, \
             open(TEMP_FILE, 'w', encoding='utf-8-sig', newline='') as f_out:
            
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            
            if 'max_durability' not in fieldnames:
                fieldnames.append('max_durability')
            
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                i_type = row.get('type', '')
                max_dur = 0
                
                # Default Durability based on Type
                if i_type in ['weapon', 'armor', 'helm', 'part_legs', 'part_feet', 'shield']:
                    max_dur = 100
                    # Maybe higher for expensive items?
                    val = int(row.get('value', 0))
                    if val > 500: max_dur = 200
                elif i_type in ['accessory']:
                    max_dur = 50
                
                row['max_durability'] = max_dur
                writer.writerow(row)
                
        print("Items CSV updated with max_durability.")
        
        # Replace original
        os.remove(ITEMS_FILE)
        os.rename(TEMP_FILE, ITEMS_FILE)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_csv_durability()
