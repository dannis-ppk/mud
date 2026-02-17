import csv
import random

# Configuration
WIDTH = 21 # -10 to 10
HEIGHT = 101 # -50 to 50
MIN_X = -10
MAX_X = 10
MIN_Y = -50
MAX_Y = 50

ROOMS_FILE = 'data/rooms.csv'

# Zones
def get_zone(x, y):
    if -3 <= x <= 3 and -3 <= y <= 3:
        return 'village'
    if y > 3:
        return 'forest'
    if y < -3:
        return 'wasteland'
    return 'wild'

# Content Pools
NAMES_VILLAGE = ["村莊廣場", "村莊街道", "寧靜的角落", "冒險者公會前", "村民的家"]
NAMES_FOREST = ["幽暗森林", "古老樹林", "迷霧小徑", "森林空地", "灌木叢"]
NAMES_WASTELAND = ["荒蕪之地", "龜裂的大地", "被遺忘的戰場", "白骨堆", "焦黑的土地"]

ENEMIES_FOREST = ['mob_rabbit', 'mob_rat', 'mob_snake', 'mob_wolf', 'mob_goblin', 'mob_spider']
ENEMIES_WASTELAND = ['mob_bandit', 'mob_bear', 'mob_skeleton', 'mob_orc', 'mob_troll']

ITEMS_COMMON = ['item_bread', 'item_healing_potion_s']
ITEMS_RARE = ['item_healing_potion_m', 'item_mana_potion_s', 'item_gem']

def generate_rooms():
    rooms = []
    
    print(f"Generating map {WIDTH}x{HEIGHT}...")
    
    for y in range(MIN_Y, MAX_Y + 1):
        for x in range(MIN_X, MAX_X + 1):
            zone = get_zone(x, y)
            name = ""
            desc = ""
            enemy_id = ""
            shop_items = ""
            
            # --- Village ---
            if zone == 'village':
                name = random.choice(NAMES_VILLAGE)
                desc = "這裡是新手村，四周充滿了祥和的氣氛。"
                if x == 0 and y == 0:
                    name = "村莊中心 (Village Center)"
                    desc = "村莊的中心廣場，有一個巨大的噴水池。北邊是森林，南邊是荒地。"
                    # Add Shop Here
                    shop_items = "item_bread;item_healing_potion_s;item_mana_potion_s;weapon_dagger;weapon_sword;armor_leather;armor_chain;item_scroll_town"
                
                # No enemies in village
                
            # --- Forest (North) ---
            elif zone == 'forest':
                name = random.choice(NAMES_FOREST)
                desc = "高大的樹木遮蔽了陽光，空氣中瀰漫著潮濕的味道。"
                
                # Enemy Spawn Chance
                if random.random() < 0.4:
                    # Difficulty scales with distance from village (y)
                    # y from 4 to 50
                    difficulty = (y - 3) / 47.0 # 0.0 to 1.0
                    
                    if difficulty < 0.3:
                        enemy_id = random.choice(['mob_rabbit', 'mob_rat'])
                    elif difficulty < 0.7:
                        enemy_id = random.choice(['mob_snake', 'mob_wolf', 'mob_goblin'])
                    else:
                        enemy_id = random.choice(['mob_wolf', 'mob_spider', 'mob_bear'])
            
            # --- Wasteland (South) ---
            elif zone == 'wasteland':
                name = random.choice(NAMES_WASTELAND)
                desc = "這裡寸草不生，只有死亡與危險。"
                
                if random.random() < 0.5:
                    # y from -4 to -50
                    difficulty = (abs(y) - 3) / 47.0
                    
                    if difficulty < 0.3:
                        enemy_id = random.choice(['mob_rat', 'mob_bandit'])
                    elif difficulty < 0.7:
                        enemy_id = random.choice(['mob_bandit', 'mob_skeleton', 'mob_orc'])
                    else:
                        enemy_id = random.choice(['mob_skeleton', 'mob_orc', 'mob_troll'])

            # --- Bosses ---
            if x == 0 and y == 50:
                name = "冰封王座 (Frozen Throne)"
                desc = "寒風刺骨，這裡居住著北方的霸主。你感到一股強大的壓力。"
                enemy_id = "boss_frost_king"
                zone = "boss"
            
            if x == 0 and y == -50:
                name = "烈焰深淵 (Abyss of Fire)"
                desc = "周圍是滾燙的岩漿，炎魔就在前方等待著挑戰者。"
                enemy_id = "boss_fire_demon"
                zone = "boss"

            # --- Create Room Dict ---
            # Exits are calculated dynamically in game usually, but CSV format had 'exits' field?
            # Looking at mud_main.py loader:
            # reader = csv.DictReader(f)
            # row['exits'] was read but logic seemed to be:
            # if row._raw_exits ... self.world.add_room ...
            # Actually grid based movement doesn't strictly need explicit exits if logic computes neighbors.
            # But let's check mud_main.py: Game.setup_world uses room.x/y and logic 
            # "if hasattr(room, '_raw_exits') ... room.exits[d] = ..."
            # BUT player.move uses dx, dy on grid directly?
            # Let's check mud_main.py move logic.
            # Player.move updates x,y.
            # Game.process_move checks self.world.get_room(new_x, new_y).
            # So explicit exits in CSV are OPTIONAL if we trust the grid.
            # We will generate neighbors implicitly by existence.
            
            rooms.append({
                'id': f"{x}_{y}",
                'name': name,
                'zone': zone,
                'x': x,
                'y': y,
                'description': desc,
                'exits': '', # Not strictly needed for grid system
                'enemy_id': enemy_id,
                'shop_item_ids': shop_items
            })
            
    # Write to CSV
    with open(ROOMS_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ['id', 'name', 'zone', 'x', 'y', 'description', 'exits', 'enemy_id', 'shop_item_ids']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rooms)
        
    print(f"Successfully generated {len(rooms)} rooms manually to '{ROOMS_FILE}'.")

if __name__ == "__main__":
    generate_rooms()
