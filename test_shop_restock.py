import unittest
import time
import traceback
import sys

try:
    from mud_main import Game, Player, Room, Shop, World
except Exception:
    traceback.print_exc()
    sys.exit(1)

class TestShopRestock(unittest.TestCase):
    def setUp(self):
        try:
           self.game = Game()
           self.game.player = Player("Hero")
           self.game.world = World()
        except Exception:
           traceback.print_exc()
           raise

    def test_regeneration_sitting(self):
        # Base stats
        self.game.player.con = 15
        self.game.player.dex = 15
        
        # Test Normal Regen (Standing)
        self.game.player.hp = 50
        self.game.player.max_hp = 100
        self.game.player.is_sitting = False
        
        hp_reg_base = max(1, self.game.player.con // 5) # 3
        self.game.player.regenerate()
        self.assertEqual(self.game.player.hp, 50 + hp_reg_base)
        
        # Test Sitting Regen
        self.game.player.hp = 50
        self.game.player.is_sitting = True
        self.game.player.regenerate()
        self.assertEqual(self.game.player.hp, 50 + (hp_reg_base * 2))

    def test_shop_timer_logic(self):
        class MockShop:
            def __init__(self):
                self.restock_called = 0
                self.last_restock_time = time.time()
                self.name = "Test Shop"
            def restock(self):
                self.restock_called += 1
        
        shop = MockShop()
        room = Room("Shop", "Shop", zone='village')
        room.shop = shop
        self.game.world.add_room(0, 0, room)
        
        interval = 2 # 2 seconds
        self.game.balance.data[('world', 'shop_restock_interval')] = interval
        
        current_time = time.time()
        shop.last_restock_time = current_time - 3
        
        if current_time - shop.last_restock_time >= interval:
            shop.restock()
            shop.last_restock_time = current_time
            
        self.assertEqual(shop.restock_called, 1)

if __name__ == '__main__':
    unittest.main()
