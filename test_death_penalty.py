import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("d:/dev/projects/MUD_the_age"))

from mud_main import Game, Player, Room, Enemy

class TestDeathPenalty(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.setup_world()
        self.game.player = Player("Hero")
        self.game.player.max_hp = 100
        self.game.player.hp = 10
        self.game.player.xp = 1000
        self.game.player.x = 1
        self.game.player.y = 1
        
        # Mock world grid
        self.current_room = Room("Dangerous Room", "Dangerous", ".")
        self.current_room.x = 1
        self.current_room.y = 1
        self.enemy = Enemy("Boss", "Boss", 100, (10, 20), 100, 100)
        self.current_room.enemies.append(self.enemy)
        
        self.safe_neighbor = Room("Safe Room", "Safe", ".")
        self.safe_neighbor.x = 1
        self.safe_neighbor.y = 2
        
        self.village = Room("Village", "Safe Village", "V")
        self.village.x = 0
        self.village.y = 0
        
        self.game.world.grid = {
            (1, 1): self.current_room,
            (1, 2): self.safe_neighbor,
            (0, 0): self.village
        }
        
    def test_death_trigger_and_relocation(self):
        # Trigger death via combat damage
        # Player has 10 HP. Damage 20.
        
        # Mock finding safe room to be deterministic
        # self.game._find_safe_room = MagicMock(return_value=self.safe_neighbor)
        
        # Manually call handle_enemy_turn would require setup
        # Let's call handle_death directly to test the LOGIC of death
        
        self.game.handle_death()
        
        # Check HP Restored
        self.assertEqual(self.game.player.hp, 100)
        
        # Check XP Penalty (5%)
        # 1000 - 50 = 950
        self.assertEqual(self.game.player.xp, 950)
        
        # Check Relocation
        # Should move to (1, 2) as it is the only neighbor in grid
        # Wait, _find_safe_room looks at world.get_room which uses world.grid
        # (1, 2) is a neighbor of (1, 1) (dy=+1) YES. 
        # And it has no enemies.
        
        self.assertEqual(self.game.player.x, 1)
        self.assertEqual(self.game.player.y, 2)
        
    def test_death_fallback_village(self):
        # Grid with NO safe neighbors
        self.game.world.grid = {
            (1, 1): self.current_room,
            (0, 0): self.village
        }
        # Village likely at 0,0 not in grid? 
        # code sets x=0, y=0.
        
        self.game.handle_death()
        self.assertEqual(self.game.player.x, 0)
        self.assertEqual(self.game.player.y, 0)

if __name__ == '__main__':
    unittest.main()
