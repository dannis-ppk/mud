import csv
import os

ENEMIES_FILE = 'd:/dev/projects/MUD_the_age/data/enemies.csv'
TEMP_FILE = 'd:/dev/projects/MUD_the_age/data/enemies_temp.csv'

# Base Level Mapping (Infer from ID or Name)
LEVEL_MAP = {
    'mob_rabbit': 1,
    'mob_rat': 2,
    'mob_slime': 3,
    'mob_snake': 4,
    'mob_wolf': 5,
    'mob_bear': 8,
    'mob_goblin': 10,
    'mob_bandit': 12,
    'mob_orc': 15,
    'mob_skeleton': 18,
    'mob_zombie': 20,
    'mob_ghost': 22,
    'mob_ogre': 25,
    'mob_drake': 30,
    'mob_dragon': 50,
    'boss_king_slime': 10,
    'boss_wolf_king': 15,
    'boss_goblin_lord': 20,
    'boss_bandit_leader': 25,
    'boss_orc_warlord': 35,
    'boss_necromancer': 45,
    'boss_red_dragon': 60
}

def update_csv():
    if not os.path.exists(ENEMIES_FILE):
        print(f"File not found: {ENEMIES_FILE}")
        return

    try:
        with open(ENEMIES_FILE, 'r', encoding='utf-8-sig') as f_in, \
             open(TEMP_FILE, 'w', encoding='utf-8-sig', newline='') as f_out:
            
            reader = csv.DictReader(f_in)
            fieldnames = reader.fieldnames
            
            if 'level' not in fieldnames:
                fieldnames.append('level')
            
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            
            for row in reader:
                eid = row['id']
                # Default to 1 if not in map
                level = LEVEL_MAP.get(eid, 1)
                
                # Check if it's a boss/elite generic logic if missing
                if 'boss' in eid and level == 1:
                    level = 10
                
                row['level'] = level
                writer.writerow(row)
                
        print("CSV updated successfully.")
        
        # Replace original
        os.remove(ENEMIES_FILE)
        os.rename(TEMP_FILE, ENEMIES_FILE)
        print("Original file replaced.")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_csv()
