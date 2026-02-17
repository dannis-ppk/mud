import os
import sys

# Add project dir to path
sys.path.append('d:/dev/projects/MUD_the_age')

from mud_main import DataLoader, Game, Player, Weapon, Item

def test_items_loading():
    dl = DataLoader('d:/dev/projects/MUD_the_age/data')
    dl.load_settings()
    dl.load_items()
    
    # Check Greatsword (2H, 80 Acc)
    gs = dl.items.get('weapon_greatsword')
    if not gs:
        print("FAIL: weapon_greatsword not found")
    else:
        print(f"Greatsword Hands: {gs.hands} (Expected 2)")
        print(f"Greatsword Accuracy: {gs.accuracy} (Expected 80)")
        if gs.hands == 2 and gs.accuracy == 80:
            print("PASS: Greatsword loaded correctly")
        else:
            print("FAIL: Greatsword stats incorrect")

    # Check Dagger (1H, 110 Acc)
    dagger = dl.items.get('weapon_dagger')
    if dagger:
        print(f"Dagger Hands: {dagger.hands} (Expected 1)")
        print(f"Dagger Accuracy: {dagger.accuracy} (Expected 110)")
        if dagger.hands == 1 and dagger.accuracy == 110:
            print("PASS: Dagger loaded correctly")
    
    return dl

def test_enemy_equipment(dl):
    dl.load_enemies()
    # Check Bandit (weapon_dagger;armor_leather)
    bandit = dl.enemies.get('mob_bandit')
    if bandit:
        print(f"Bandit Equipment: {[i.name for i in bandit.equipment.values()]}")
        if 'r_hand' in bandit.equipment and 'body' in bandit.equipment:
            print("PASS: Bandit has weapon and armor")
        else:
            print("FAIL: Bandit missing equipment")
    
    # Check Skeleton (weapon_sword;armor_chain)
    skel = dl.enemies.get('mob_skeleton')
    if skel:
         # print(f"Skeleton Equipment: {[i.name for i in skel.equipment.values()]}")
         # Check by keyword
         has_sword = False
         for item in skel.equipment.values():
             if 'sword' in item.keyword.lower():
                 has_sword = True
                 break
         
         if has_sword:
             print("PASS: Skeleton has sword")

    return dl

def test_room_limits(dl):
    print("Testing Room Mutation Limits...")
    # Mock settings to force mutation
    dl.settings['mutation_chance'] = 1.0 
    dl.settings['max_special_rooms'] = 3
    
    dl.load_rooms()
    
    mutated_count = 0
    for room in dl.rooms.values():
        for enemy in room.enemies:
            if 'mutated' in str(enemy.id):
                mutated_count += 1
    
    print(f"Total Mutated Enemies: {mutated_count}")
    if mutated_count <= 3: # Might be less if randomness or few enemies
        # But chance is 1.0, so should be exactly 3 if we process enough rooms
        # There are >400 rooms in forest.
        print("PASS: Mutation Limit respected")
    else:
        print(f"FAIL: Mutation Limit exceeded ({mutated_count} > 3)")

def test_player_equip():
    game = Game()
    p = game.player
    # Give player items
    sword = Weapon("Sword", "Desc", 100, "sword", 10, 20, slot='r_hand', hands=1)
    shield = Item("Shield", "Desc", 50, "shield", rarity="Common") # no offhand class yet?
    # Wait, offhand items are usually armor or weapon?
    # Let's say we equip a second sword in offhand for dual wield test (if supported)
    # Or just an item in l_hand.
    # Player.equip doesn't exist? Game.handle_wear_item logic handles it.
    
    # Mock Game.handle_wear_item logic?
    # Actually I should call game.handle_wear_item if I can simulate it.
    # But game loop isn't running.
    # I can call game.handle_wear_item("sword")
    
    p.inventory.append(sword)
    game.handle_wear_item("sword")
    print(f"Equipped 1H Sword. R_Hand: {p.equipment['r_hand'].name if p.equipment['r_hand'] else 'None'}")
    
    gs = Weapon("Greatsword", "Desc", 500, "greatsword", 30, 40, slot='r_hand', hands=2)
    p.inventory.append(gs)
    
    # Equip offhand item first to test unequip
    # Force equip to l_hand manually since no item class for 'l_hand' slot easily available without DB
    p.equipment['l_hand'] = sword # Hack
    print("Forced Offhand Equip: Sword")
    
    game.handle_wear_item("greatsword")
    print(f"Equipped 2H Greatsword. R_Hand: {p.equipment['r_hand'].name if p.equipment['r_hand'] else 'None'}")
    print(f"L_Hand: {p.equipment['l_hand'].name if p.equipment['l_hand'] else 'None'}")
    
    if p.equipment['r_hand'] == gs and p.equipment['l_hand'] is None:
        print("PASS: 2H Weapon unequipped offhand")
    else:
        print("FAIL: 2H Logic incorrect")

if __name__ == "__main__":
    try:
        dl = test_items_loading()
        test_enemy_equipment(dl)
        test_room_limits(dl)
        test_player_equip()
    except Exception as e:
        print(f"Test Failed with Error: {e}")
        import traceback
        traceback.print_exc()
