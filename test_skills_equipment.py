import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("d:/dev/projects/MUD_the_age"))

from mud_main import Game, Player, Enemy, LootGenerator, Item, Weapon, Armor

class TestSkillsAndEquipment(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.player = Player("TestHero")
        self.game.log = MagicMock()

    def test_enemy_type_loading(self):
        # Mock DataLoader to test Enemy creation with type
        # We can test Enemy class directly
        e = Enemy("Wolf", "A wolf", 100, (10, 20), 50, 10, enemy_type="beast")
        self.assertEqual(e.type, "beast")
        self.assertIn("charge", e.skills)
        
        e2 = Enemy("Orc", "An orc", 100, (10, 20), 50, 10, enemy_type="humanoid")
        self.assertEqual(e2.type, "humanoid")
        self.assertIn("slash", e2.skills)

    def test_enemy_skills_elite(self):
        # Elite Beast
        e = Enemy("Elite Wolf", "A wolf", 400, (10, 20), 50, 10, enemy_type="beast")
        self.assertIn("bite", e.skills)
        
        # Elite Humanoid
        e2 = Enemy("Elite Orc", "An orc", 400, (10, 20), 50, 10, enemy_type="humanoid")
        self.assertIn("smash", e2.skills)

    def test_loot_generator_necklace(self):
        # Test Rare Necklace
        proto = Armor("Amulet", "Desc", 100, "amulet", 0, slot="neck")
        item = LootGenerator.generate(proto, force_rarity="Rare")
        self.assertEqual(item.rarity, "Rare")
        self.assertTrue(item.bonuses.get('hp') > 0)
        
        # Test Epic Ring
        proto2 = Armor("Ring", "Desc", 100, "ring", 0, slot="finger")
        item2 = LootGenerator.generate(proto2, force_rarity="Epic")
        self.assertEqual(item2.rarity, "Epic")
        self.assertTrue(item2.bonuses.get('mp') > 0)

    def test_player_skill_blind(self):
        # Mock target
        target = Enemy("Goblin", "Desc", 100, (5, 10), 10, 10)
        self.game.player.mp = 50
        self.game.player.skills['blind'] = 100 # Max proficiency for success
        
        # Mock check_skill_success to return True
        with patch.object(self.game, 'check_skill_success', return_value=True):
             self.game.world.get_room = MagicMock()
             self.game.world.get_room.return_value.enemies = [target]
             
             self.game.handle_skill("blind goblin")
             
             # Check effect
             self.assertIn('def_down', target.debuffs)
             self.assertEqual(target.debuffs['def_down'], 3)

    def test_player_skill_kick(self):
        target = Enemy("Goblin", "Desc", 100, (5, 10), 10, 10)
        self.game.player.mv = 50
        self.game.player.skills['kick'] = 100
        
        with patch.object(self.game, 'check_skill_success', return_value=True):
             self.game.world.get_room = MagicMock()
             self.game.world.get_room.return_value.enemies = [target]
             
             original_hp = target.hp
             self.game.handle_skill("kick goblin")
             
             # Check damage (HP should be lower)
             self.assertTrue(target.hp < original_hp)
             # Check debuff
             self.assertIn('def_down', target.debuffs)

    def test_enemy_defense_calculation(self):
        target = Enemy("Goblin", "Desc", 100, (5, 10), 10, 10)
        # Equip armor
        armor = Armor("Plate", "Desc", 100, "plate", 10, slot="body")
        target.equip(armor)
        
        # Base defense = 10
        self.assertEqual(target.get_defense(), 10)
        
        # Apply Debuff
        target.debuffs['def_down'] = 1
        # Result should be 10 - 5 = 5
        self.assertEqual(target.get_defense(), 5)

if __name__ == '__main__':
    unittest.main()
