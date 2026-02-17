
import sys
import os

# Modify path to import mud_main
sys.path.append(os.path.abspath("d:/dev/projects/MUD_the_age"))

try:
    import mud_main
except Exception as e:
    print(f"Failed to import mud_main: {e}")
    sys.exit(1)

def test_csv_encoding():
    with open("d:/dev/projects/MUD_the_age/data/skills.csv", "rb") as f:
        header = f.read(3)
        if header == b'\xef\xbb\xbf':
            print("PASS: skills.csv has BOM.")
        else:
            print(f"FAIL: skills.csv BOM missing. Found: {header}")

def test_damage_logic():
    # Setup minimal game state
    game = mud_main.Game()
    p = game.player
    p.str = 10
    
    # Mock Weapon
    weapon = mud_main.Weapon("Test Sword", "Desc", 100, "sword", 10, 20) # 10-20 dmg
    p.equipment['r_hand'] = weapon
    
    # Base Damage (approximate)
    # Str 10 -> +5 dmg
    # Weapon -> +10~20
    # Total Base -> 15~25
    
    # Test Power: base * 1.5 -> 22~37
    # Test Berserk: base * 3.0 -> 45~75
    
    # Mock Helper to capture log
    class MockGame:
        def __init__(self):
            self.logs = []
            self.skills_data = game.skills_data
            self.player = p
            self.loader = game.loader
        def log(self, msg):
            self.logs.append(msg)
        def calculate_player_damage(self):
            return 20 # Fixed base damage for testing
            
    mock_game = MockGame()
    # Inject mock game into player so it can find things if needed? 
    # Actually handle_skill is a method of Game class.
    # So we need to bind handle_skill to our mock or just run it on game instance with mocked log.
    
    game.log = mock_game.log
    
    # Override calculate_player_damage to return fixed value for deterministic test
    game.calculate_player_damage = lambda: 20
    
    print("\nTesting Power (Base 20 * 1.5 = 30)...")
    # Verify skill data
    if 'power' not in game.skills_data:
        print("FAIL: Power skill not found in data.")
        return

    # Call handle_skill
    # We need a target.
    enemy = mud_main.Enemy("Target", "Desc", 100, (1,1), 0, 0)
    game.world.get_room(0,0).enemies.append(enemy)
    
    # We need to bypass validation?
    # handle_skill checks p.mv < cost.
    p.mv = 100
    p.mp = 100
    p.level = 10 # Ensure level req met
    
    game.handle_skill("power target")
    
    # Check logs for damage
    found_damage = False
    for log in mock_game.logs:
        if "造成了" in log and "30" in log:
            print(f"PASS: Power caused 30 damage. Log: {log}")
            found_damage = True
            break
            
    if not found_damage:
        print("FAIL: Power damage not 30.")
        print("Logs:", mock_game.logs)
        
    # Test Berserk
    mock_game.logs = []
    print("\nTesting Berserk (Base 20 * 3.0 = 60)...")
    game.handle_skill("berserk target")
    
    found_damage = False
    for log in mock_game.logs:
        if "造成了" in log and "60" in log:
            print(f"PASS: Berserk caused 60 damage. Log: {log}")
            found_damage = True
            break
            
    if not found_damage:
        print("FAIL: Berserk damage not 60.")
        print("Logs:", mock_game.logs)

if __name__ == "__main__":
    test_csv_encoding()
    test_damage_logic()
