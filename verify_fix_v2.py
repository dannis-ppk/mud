
import sys
import os
import io

# Modify path to import mud_main
sys.path.append(os.path.abspath("d:/dev/projects/MUD_the_age"))

# Capture stdout to suppress game init noise
old_stdout = sys.stdout
sys.stdout = io.StringIO()

try:
    import mud_main
except Exception as e:
    sys.stdout = old_stdout
    print(f"Failed to import mud_main: {e}")
    sys.exit(1)

# Restore stdout
sys.stdout = old_stdout

def verify():
    results = []
    
    # Check BOM
    try:
        with open("d:/dev/projects/MUD_the_age/data/skills.csv", "rb") as f:
            header = f.read(3)
            if header == b'\xef\xbb\xbf':
                results.append("PASS: skills.csv has BOM.")
            else:
                results.append(f"FAIL: skills.csv BOM missing. Found: {header}")
    except Exception as e:
        results.append(f"FAIL: Error reading file: {e}")

    # Check Damage Logic
    try:
        # Suppress prints again for game init if any lazy loading happens
        sys.stdout = io.StringIO()
        
        game = mud_main.Game()
        p = game.player
        p.str = 10
        weapon = mud_main.Weapon("Test Sword", "Desc", 100, "sword", 10, 20)
        p.equipment['r_hand'] = weapon
        
        # Mock Logic to avoid randomness
        game.calculate_player_damage = lambda: 20
        
        # Mock Log
        logs = []
        def mock_log(msg):
            logs.append(msg)
        game.log = mock_log
        
        # Ensure skill data loaded
        if 'power' not in game.skills_data:
            results.append("FAIL: Power skill not found in data.")
        else:
            old_stdout_debug = sys.stdout
            sys.stdout = sys.__stdout__ # Force print to real stdout for debug
            print(f"DEBUG SKILL DATA: {game.skills_data['power']}")
            sys.stdout = old_stdout_debug
            
            # Setup Target
            enemy = mud_main.Enemy("Target", "Desc", 100, (1,1), 0, 0)
            game.world.get_room(0,0).enemies.append(enemy)
            enemy.take_damage = lambda dmg: logs.append(f"Target took {dmg} damage") # Mock take_damage to avoid combat loop side effects?
            # Actually mud_main generic perform_attack calls target.take_damage AND logs.
            # But the combat resolution logic (resolve_turn) might be complex.
            # Let's just mock 'perform_attack' to simplify testing DAMAGE FORMULA only.
            
            # Mock perform_attack to capture the damage value passed to it
            def mock_perform_attack(target, damage, prefix, color=None):
                logs.append(f"PERFORM_ATTACK: {damage}")
            
            game.perform_attack = mock_perform_attack
            
            # Setup Player
            p.mv = 100
            p.mp = 100
            p.level = 10
            
            # Test Power
            sys.stdout = old_stdout # Restore for debugging if needed, but keeping suppressed is safer
            game.handle_skill("power Target")
            
            # Check logs
            power_dmg = 30 # 20 * 1.5
            found = False
            for log in logs:
                if f"PERFORM_ATTACK: {power_dmg}" in log:
                    found = True
                    break
            
            if found:
                results.append(f"PASS: Power caused {power_dmg} damage.")
            else:
                results.append(f"FAIL: Power damage incorrect. Logs: {logs}")

            # Test Berserk
            logs.clear()
            berserk_dmg = 60 # 20 * 3.0
            game.handle_skill("berserk Target")
             
            found = False
            for log in logs:
                 if f"PERFORM_ATTACK: {berserk_dmg}" in log:
                     found = True
                     break
            
            if found:
                results.append(f"PASS: Berserk caused {berserk_dmg} damage.")
            else:
                results.append(f"FAIL: Berserk damage incorrect. Logs: {logs}")

    except Exception as e:
        sys.stdout = old_stdout
        results.append(f"FAIL: Exception during test: {e}")
        import traceback
        traceback.print_exc()

    sys.stdout = old_stdout
    
    # Write results to file
    with open("d:/dev/projects/MUD_the_age/test_results.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(results))
    
    print("\n".join(results))

if __name__ == "__main__":
    verify()
