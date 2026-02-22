import unittest
from mud_main import Game, Player, Room, World

class TestCostScaling(unittest.TestCase):
    def setUp(self):
        # Patch data loading to avoid CSV issues
        with unittest.mock.patch('mud_main.DataLoader') as MockLoader:
            self.game = Game()
            self.game.loader = MockLoader()
            
        # Mock loader skill data for testing
        self.game.skills_data = {
            'basic_attack': {'name': 'Attack', 'cost_value': 10, 'cost_type': 'mv'},
            'heal': {'name': 'Heal', 'cost_value': 20, 'cost_type': 'mp'},
            'kick': {'name': 'Kick', 'cost_value': 15, 'cost_type': 'mv'}
        }
        self.game.player = Player("Hero")
        self.game.player.level = 1
        self.game.world = World()
        # Add a default room at (0,0)
        self.room_start = Room("Start", "Start room", zone='village')
        self.game.world.add_room(0, 0, self.room_start)
        self.game.player.x = 0
        self.game.player.y = 0

    def test_base_cost_level_1(self):
        # Level 1, Village (1.0 mult)
        cost, ctype = self.game.get_skill_cost('basic_attack')
        self.assertEqual(cost, 10)
        self.assertEqual(ctype, 'mv')

    def test_level_scaling(self):
        # Level 51 (1 + 50*0.02 = 2.0 mult)
        self.game.player.level = 51
        cost, ctype = self.game.get_skill_cost('basic_attack')
        self.assertEqual(cost, 20) # 10 * 2.0

    def test_zone_scaling(self):
        # Level 1, Nexus (1.5 mult)
        nexus_room = Room("Nexus", "Nexus room", zone='nexus')
        self.game.world.add_room(10, 10, nexus_room)
        self.game.player.x = 10
        self.game.player.y = 10
        
        cost, ctype = self.game.get_skill_cost('basic_attack')
        self.assertEqual(cost, 15) # 10 * 1.5

    def test_combined_scaling(self):
        # Level 51 (2.0 mult), Nexus (1.5 mult) -> 3.0 mult
        self.game.player.level = 51
        nexus_room = Room("Nexus", "Nexus room", zone='nexus')
        self.game.world.add_room(10, 10, nexus_room)
        self.game.player.x = 10
        self.game.player.y = 10
        
        cost, ctype = self.game.get_skill_cost('basic_attack')
        self.assertEqual(cost, 30) # 10 * 2.0 * 1.5

if __name__ == '__main__':
    unittest.main()
