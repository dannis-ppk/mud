import os

file_path = 'd:/dev/projects/MUD_the_age/mud_main.py'

new_load_items = """    def load_items(self):
        try:
            import csv
            # use utf-8-sig to handle Excel CSVs (which add BOM)
            with open(os.path.join(self.data_dir, 'items.csv'), 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # id,name,type,value,keyword,min_dmg,max_dmg,defense,slot,description,english_name,hands,accuracy
                    item_id = row['id']
                    name = row['name']
                    i_type = row['type']
                    value = row['value']
                    keyword = row['keyword']
                    slot = row['slot']
                    desc = row['description']
                    english_name = row.get('english_name', '')
                    
                    item = None
                    if i_type == 'weapon':
                        min_d = int(row.get('min_dmg', 0))
                        max_d = int(row.get('max_dmg', 0))
                        hands = int(row.get('hands', 1)) 
                        accuracy = int(row.get('accuracy', 100))
                        item = Weapon(name, desc, int(value), keyword, min_d, max_d, slot, english_name=english_name, hands=hands, accuracy=accuracy)
                    elif i_type == 'armor' or i_type == 'helm': 
                        defense = int(row.get('defense', 0))
                        item = Armor(name, desc, int(value), keyword, int(defense), slot, english_name=english_name)
                    else:
                        item = Item(name, desc, int(value), keyword, english_name=english_name)
                    
                    self.items[item_id] = item
            print("Items loaded.")
        except Exception as e:
            print(f"Error loading items: {e}")
"""

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if line.strip() == 'def load_items(self):':
        start_idx = i
    if start_idx != -1 and line.strip() == 'def load_enemies(self):':
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Found load_items at {start_idx} to {end_idx}")
    # Replace lines
    # Note: new_load_items is a string, needs to be list of lines?
    # Or just slice list.
    
    # We need to preserve lines before start_idx and after end_idx (inclusive of load_enemies?)
    # load_enemies starts at end_idx. So we replace up to end_idx.
    
    new_content = "".join(lines[:start_idx]) + new_load_items + "\n" + "".join(lines[end_idx:])
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Patched successfully.")
else:
    print(f"Could not find method boundaries. Start: {start_idx}, End: {end_idx}")
