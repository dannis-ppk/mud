import os

data_dir = 'd:/dev/projects/MUD_the_age/data'

def overwrite_csv(source, dest):
    try:
        with open(os.path.join(data_dir, source), 'r', encoding='utf-8-sig') as f_src:
            content = f_src.read()
        
        with open(os.path.join(data_dir, dest), 'w', encoding='utf-8-sig') as f_dest:
            f_dest.write(content)
            
        print(f"Successfully overwrote {dest} with {source}")
    except Exception as e:
        print(f"Error overwriting {dest}: {e}")

overwrite_csv('items_new.csv', 'items.csv')
overwrite_csv('enemies_new.csv', 'enemies.csv')
