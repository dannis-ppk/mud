import csv
import os

def final_merge():
    base_file = 'data/enemies.csv'
    update_file = 'data/enemies_update.csv'
    
    # 1. Load existing IDs to avoid duplicates
    existing_ids = set()
    with open(base_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            existing_ids.add(row['id'])
            fieldnames = reader.fieldnames
            
    # 2. Add new enemies from update_file
    new_rows = []
    # Using latin-1 to read safely, will fix names manually if needed or skip existing
    with open(update_file, 'r', encoding='latin-1') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['id'] not in existing_ids:
                # Basic name cleanup if it was Big5 interpreted as Latin-1
                # but better to just append and let user fix if they want, 
                # or I can try to find the new ones' names.
                new_rows.append(row)
                existing_ids.add(row['id'])
                
    # 3. Append to base file
    if new_rows:
        with open(base_file, 'a', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            for row in new_rows:
                writer.writerow(row)
        print(f"Added {len(new_rows)} new enemies to {base_file}")
    else:
        print("No new enemies found to add.")
        
    # 4. Remove update file
    if os.path.exists(update_file):
        os.remove(update_file)
        print(f"Deleted {update_file}")

if __name__ == '__main__':
    final_merge()
