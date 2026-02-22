import csv
import os

def merge_enemies():
    update_file = 'data/enemies_update.csv'
    base_file = 'data/enemies.csv'
    
    # Read the update file (Big5)
    with open(update_file, 'r', encoding='big5') as f:
        reader = csv.DictReader(f)
        updates = {row['id']: row for row in reader}
    
    # Read the base file (UTF-8-SIG)
    with open(base_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        base_data = {row['id']: row for row in reader}
    
    # Merge
    base_data.update(updates)
    
    # Write back to base file in UTF-8-SIG
    with open(base_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row_id in sorted(base_data.keys()):
            writer.writerow(base_data[row_id])
            
    print(f"Successfully merged {len(updates)} entries from {update_file} into {base_file}")

if __name__ == '__main__':
    merge_enemies()
