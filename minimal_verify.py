import time
from mud_main import Player

def test_recovery():
    p = Player("Hero")
    p.con = 15
    p.hp = 50
    p.max_hp = 100
    p.is_sitting = False
    
    p.regenerate()
    stand_hp = p.hp
    print(f"Standing HP: {stand_hp} (Expected 53)")
    
    p.hp = 50
    p.is_sitting = True
    p.regenerate()
    sit_hp = p.hp
    print(f"Sitting HP: {sit_hp} (Expected 56)")
    
    if sit_hp > stand_hp:
        print("RECOVERY TEST PASSED")
    else:
        print("RECOVERY TEST FAILED")

if __name__ == "__main__":
    try:
        test_recovery()
    except Exception as e:
        import traceback
        traceback.print_exc()
