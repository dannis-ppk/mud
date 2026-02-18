import csv
import random
import os

ROOMS_FILE = 'd:/dev/projects/MUD_the_age/data/rooms.csv'
BACKUP_FILE = 'd:/dev/projects/MUD_the_age/data/rooms_backup.csv'

def populate():
    # Read Existing
    with open(ROOMS_FILE, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # Backup
    with open(BACKUP_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Backed up to {BACKUP_FILE}")

    count = 0
    for row in rows:
        if row['zone'] == 'forest' and not row['enemy_id']:
            try:
                y = int(row['y'])
            except ValueError:
                continue

            # 30% Chance to stay empty
            if random.random() > 0.7:
                continue

            # Determine Pool
            pool = []
            if 4 <= y <= 9:
                pool = ['mob_rabbit', 'mob_rat', 'mob_bat']
            elif 10 <= y <= 24:
                pool = ['mob_wolf', 'mob_boar', 'mob_snake', 'mob_wisp', 'mob_thief']
            elif y >= 25:
                pool = ['mob_bear', 'mob_spider', 'mob_ent', 'mob_bandit', 'mob_thief', 'mob_thief'] # Double chance
            
            if pool:
                choice = random.choice(pool)
                # Ensure mob_bat/boar/wisp/ent exist in enemies.csv (we added them)
                row['enemy_id'] = choice
                count += 1

    # Write Back
    with open(ROOMS_FILE, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Populated {count} rooms with enemies.")

if __name__ == "__main__":
    populate()
