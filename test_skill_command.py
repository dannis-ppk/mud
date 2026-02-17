import unittest
from unittest.mock import MagicMock
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath("d:/dev/projects/MUD_the_age"))

from mud_main import Game, DataLoader

class TestSkillCommand(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        # Mock loader to avoid full data loading if possible, or key parts
        # Actually initializing Game() loads data.
        # We need to verify commands loaded from CSV.
        
    def test_skill_command_loaded(self):
        # Verify 'skill' is in commands map
        self.assertIn('skill', self.game.commands)
        self.assertIn('sk', self.game.aliases)
        
    def test_process_skill_no_args(self):
        # Mock handle_skill
        self.game.handle_skill = MagicMock()
        
        # Test 'skill' 
        self.game.process_command('skill')
        self.game.handle_skill.assert_called_with('', is_spell=False)
        
    def test_process_skill_with_args(self):
        self.game.handle_skill = MagicMock()
        
        self.game.process_command('skill blind')
        self.game.handle_skill.assert_called_with('blind', is_spell=False)

    def test_process_skill_alias(self):
        self.game.handle_skill = MagicMock()
        
        # 'sk' is alias for 'skill'
        self.game.process_command('sk')
        self.game.handle_skill.assert_called_with('', is_spell=False)

if __name__ == '__main__':
    unittest.main()
