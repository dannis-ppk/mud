import unittest
import os
import csv
from mud_main import BalanceManager, Player, Enemy, LootGenerator, Item, Weapon, Armor

class TestBalance(unittest.TestCase):
    def setUp(self):
        self.test_csv = "test_balance.csv"
        with open(self.test_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["category", "key", "value", "description"])
            writer.writerow(["player", "hp_per_con", "20", "Modified HP per CON"])
            writer.writerow(["player", "hp_per_level", "15", "Modified HP per level"])
            writer.writerow(["player", "hp_base", "100", "Modified base HP"])
            writer.writerow(["enemy", "scaling_factor", "0.2", "Extreme scaling"])
            writer.writerow(["rarity", "epic_dmg_min", "50", "Extreme Epic bonus"])
            writer.writerow(["rarity", "epic_dmg_max", "60", "Extreme Epic bonus"])
        
        self.bm = BalanceManager(self.test_csv)

    def tearDown(self):
        if os.path.exists(self.test_csv):
            os.remove(self.test_csv)

    def test_player_stats(self):
        # Basic Player Stats
        p = Player("Hero", balance_manager=self.bm)
        # Recalculate - Default stats are usually 10 for all
        # Formula: HP = CON * 20 + Level * 15 + 100
        # Default CON is 10, Level is 1.
        # Exp: 10 * 20 + 1 * 15 + 100 = 200 + 15 + 100 = 315
        p.recalculate_stats()
        self.assertEqual(p.max_hp, 315)

    def test_enemy_scaling(self):
        e = Enemy("Goblin", "Small", 10, (1, 2), 10, 10, balance_manager=self.bm)
        # Scale to Level 5
        # Formula: Scale = 1.0 + (5-1) * 0.2 = 1.0 + 0.8 = 1.8
        # HP: 10 * 1.8 = 18
        e.scale_to_player(5)
        self.assertEqual(e.max_hp, 18)

    def test_loot_generation(self):
        # Test Epic Rarity
        proto = Weapon("Sword", "Dull", 10, "sword", 1, 5)
        item = LootGenerator.generate(proto, force_rarity="Epic", balance_manager=self.bm)
        # Epic DMG bonus should be 50-60
        # Original min 1, max 5.
        # New min: 1 + (50 to 60)
        self.assertTrue(51 <= item.min_dmg <= 61)

if __name__ == "__main__":
    unittest.main()
