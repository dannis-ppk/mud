import os
import sys
import random
import time
import copy
import csv
import json
import os
import time
import msvcrt
import random
from datetime import datetime
# Rich Imports
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table
from rich import box
from rich.align import Align

# Windows clear screen command (Deprecated with Rich Live, but kept for fallback)
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class BalanceManager:
    """Manages game balance parameters loaded from CSV."""
    def __init__(self, filepath=None):
        self.params = {} # (category, key) -> value
        if filepath and os.path.exists(filepath):
            self.load(filepath)

    def load(self, filepath):
        try:
            with open(filepath, mode='r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    category = row['category'].strip()
                    key = row['key'].strip()
                    try:
                        # Convert to float if possible, then int if it's a whole number
                        val = float(row['value'].strip())
                        if val.is_integer():
                            val = int(val)
                    except ValueError:
                        val = row['value'].strip()
                    self.params[(category, key)] = val
        except Exception as e:
            print(f"Error loading balance.csv: {e}")

    def get(self, category, key, default=None):
        return self.params.get((category, key), default)

class Color:
    # Rich Markup placeholders
    RESET = "[/]"
    RED = "[red]"
    GREEN = "[green]"
    YELLOW = "[yellow]"
    BLUE = "[blue]"
    MAGENTA = "[magenta]"
    CYAN = "[cyan]"
    WHITE = "[white]"
    ORANGE = "[orange3]"

    @staticmethod
    def colorize(text, color):
        # If color is closing tag, handling is different, but for simple wrapping:
        return f"{color}{text}[/]"

class Enemy:
    def __init__(self, name, description, hp, damage_range, xp_reward, gold_reward, loot_table=None, id=None, respawn_time=30, enemy_type="beast", level=1, is_thief=False, balance_manager=None):
        self.balance = balance_manager
        self.id = id
        self.respawn_time = respawn_time
        self.name = name
        self.description = description
        self.base_max_hp = hp # Store original
        self.base_damage_range = damage_range
        self.base_xp_reward = xp_reward
        self.base_gold_reward = gold_reward
        
        self.last_attack_time = 0.0 # Ready to attack
        self.max_hp = hp
        self.base_max_hp = hp
        self.base_damage_range = damage_range
        self.hp = hp
        self.damage_range = damage_range  # (min, max)
        self.xp_reward = xp_reward
        self.gold_reward = gold_reward
        self.loot_table = loot_table if loot_table else [] # List of (Item, drop_chance_float)
        
        # Flavor Text based on Type
        self.type = enemy_type
        if self.type == "humanoid":
            self.attack_flavor = ["揮砍", "刺擊", "狠打", "踢擊"]
        else:
            self.attack_flavor = ["咬了", "抓了", "撞擊", "猛攻"]
            
        self.proto_id = None # ID for respawning
        self.is_aggressive = False # Becomes true on attack
        self.aggro_chance = 0.0 # Chance to auto-attack on player entry
        self.equipment = {} # slot -> Item
        self.debuffs = {} # {type: duration} (e.g., 'blind': 3, 'def_down': 3)
        self.level = level
        self.base_max_hp = hp
        self.base_damage_range = damage_range
        self.base_xp_reward = xp_reward
        self.base_gold_reward = gold_reward
        
        # Skill Configuration
        self.skills = []
        is_boss = (id and id.startswith('boss_')) if id else False
        is_mutated = (id and "mutated" in id) if id else False
        is_elite = self.max_hp >= 300 or is_mutated
        
        # Assign Skills based on Type & Rarity
        if self.type == "beast":
             self.skills.append("charge") # Normal
             if is_elite or is_boss: self.skills.append("bite")
        elif self.type == "humanoid":
             self.skills.append("slash") # Normal
             if is_elite or is_boss: self.skills.append("smash")
             
        if is_boss:
             self.skills.append("triple_attack")
             
        self.is_thief = is_thief
        self.stolen_gold = 0
        self.inventory = [] # Items picked up / stolen (for Boss persistence)

    def scale_to_player(self, player_level):
        """Scales enemy stats based on player level."""
        # Logic: Effective Level = max(BaseLevel, PlayerLevel)
        if player_level <= 1: return
        
        scaling_factor = 0.05
        if hasattr(self, 'balance') and self.balance:
            scaling_factor = self.balance.get('enemy', 'scaling_factor', 0.05)

        scale_factor = 1.0 + (player_level - 1) * scaling_factor
        
        self.max_hp = int(self.base_max_hp * scale_factor)
        self.hp = self.max_hp # Heal to full
        
        min_d = int(self.base_damage_range[0] * scale_factor)
        max_d = int(self.base_damage_range[1] * scale_factor)
        self.damage_range = (min_d, max_d)
        
        self.xp_reward = int(self.base_xp_reward * scale_factor)
        self.gold_reward = int(self.base_gold_reward * scale_factor)



    def is_alive(self):
        return self.hp > 0

    def take_damage(self, amount):
        self.hp -= amount
        if self.hp < 0: self.hp = 0

    def get_defense(self):
        # Base defense (could be based on level, but for now 0)
        defense = 0
        # Equipment defense
        for item in self.equipment.values():
            if hasattr(item, 'defense'):
                 defense += item.defense
        
        # Debuff Modification
        if self.has_status('def_down'):
            defense -= 5 # Lower defense by 5
        if self.has_status('blind'):
            defense -= 3 # Blind also slightly reduces defense
            
        return max(0, defense)

    def has_status(self, status_name):
        """Check if enemy has an active status effect (致盲/擊倒等)"""
        return self.debuffs.get(status_name, 0) > 0

    def tick_debuffs(self):
        """Decrement all debuff timers. Remove expired ones. Auto-stand from knockdown."""
        expired = []
        for key in list(self.debuffs.keys()):
            self.debuffs[key] -= 1
            if self.debuffs[key] <= 0:
                expired.append(key)
        for key in expired:
            del self.debuffs[key]
        return expired # Return list of expired debuffs for logging
        
    def use_skill(self):
        import random
        # Chance to use skill: 30% for Elite, 50% for Boss, 10% Normal
        is_boss = (self.proto_id and self.proto_id.startswith('boss_'))
        is_mutated = (self.id and "mutated" in self.id)
        is_elite = self.max_hp >= 300 or is_mutated
        
        chance = 0.1
        if self.balance:
            chance = self.balance.get('rarity', 'normal_skill_chance', 0.1)
            if is_elite: chance = self.balance.get('rarity', 'elite_skill_chance', 0.3)
            if is_boss: chance = self.balance.get('rarity', 'boss_skill_chance', 0.5)
        else:
            if is_elite: chance = 0.3
            if is_boss: chance = 0.5
        
        if self.skills and random.random() < chance:
             skill = random.choice(self.skills)
             
             base_dmg = random.randint(self.damage_range[0], self.damage_range[1])
             # Check Weapon
             if 'r_hand' in self.equipment:
                 w = self.equipment['r_hand']
                 if hasattr(w, 'min_dmg'):
                     base_dmg += random.randint(w.min_dmg, w.max_dmg)
             
             if skill == "charge":
                 dmg = int(base_dmg * 1.5)
                 return dmg, f"使用了 [bold red]衝撞 (Charge)[/]!", "charge"
             elif skill == "bite":
                 dmg = int(base_dmg * 1.2)
                 return dmg, f"使用了 [bold red]撕咬 (Bite)[/]!", "bite"
             elif skill == "slash":
                 dmg = int(base_dmg * 1.2)
                 return dmg, f"使用了 [bold red]揮砍 (Slash)[/]!", "slash"
             elif skill == "smash":
                 dmg = int(base_dmg * 1.5)
                 return dmg, f"使用了 [bold red]重擊 (Smash)[/]!", "smash"
             elif skill == "triple_attack":
                 dmg = int(base_dmg * 3.0) # Simplified 3 hits as one big hit for now
                 return dmg, f"使用了 [bold magenta]三連擊 (Triple Attack)[/]!", "triple"
                 
        return None

    def attack(self):
        # Base damage
        dmg = random.randint(self.damage_range[0], self.damage_range[1])
        # Add weapon damage if equipped
        if 'r_hand' in self.equipment:
            w = self.equipment['r_hand']
            if hasattr(w, 'min_dmg'):
                dmg += random.randint(w.min_dmg, w.max_dmg)
        return dmg

    def equip(self, item):
        if hasattr(item, 'slot') and item.slot != 'none':
            self.equipment[item.slot] = item
            # Optional: Add stats to base stats? 
            # For now, attack() logic handles weapon dmg, take_damage logic should handle armor.
            if item.slot == 'body' and hasattr(item, 'defense'):
                 # We don't have defense stat on enemy yet, maybe strict logic later
                 pass

    def mutate(self):
        import random
        # 1. Choose Mutation Type
        types = ['Fast', 'Strong', 'Tough', 'Elite']
        m_type = random.choice(types)
        
        if m_type == 'Fast':
            self.name = f"[cyan]迅捷的[/] {self.name}"
            self.xp_reward = int(self.xp_reward * 1.2)
        elif m_type == 'Strong':
            self.name = f"[red]怪力的[/] {self.name}"
            self.damage_range = (int(self.damage_range[0] * 1.5), int(self.damage_range[1] * 1.5))
            self.xp_reward = int(self.xp_reward * 1.3)
        elif m_type == 'Tough':
            self.name = f"[blue]強壯的[/] {self.name}"
            self.max_hp = int(self.max_hp * 1.5)
            self.hp = self.max_hp
            self.xp_reward = int(self.xp_reward * 1.3)
        elif m_type == 'Elite':
            self.name = f"[yellow]精英[/] {self.name}"
            self.max_hp = int(self.max_hp * 2)
            self.hp = self.max_hp
            self.damage_range = (int(self.damage_range[0] * 1.2), int(self.damage_range[1] * 1.2))
            self.xp_reward = int(self.xp_reward * 2.0)
            self.gold_reward = int(self.gold_reward * 2.0)
            
        self.description = f"這是一個變異的敵人。{self.description}"


class Item:
    def __init__(self, name, description, value, keyword, rarity="Common", color="white", bonuses=None, english_name="", max_durability=0, set_id="", is_unique=False):
        self.name = name
        self.description = description
        self.value = value
        self.keyword = keyword
        self.english_name = english_name
        self.drop_time = None 
        
        self.rarity = rarity # Common, Fine, Rare, Epic, Unique
        self.color = color   # white, green, blue, magenta
        self.bonuses = bonuses if bonuses else {}
        
        self.max_durability = max_durability
        self.current_durability = max_durability # Default to full
        self.set_id = set_id       # Set bonus group ID (套裝 ID)
        self.is_unique = is_unique # Only one can exist globally (唯一性)

    def get_display_name(self):
        if self.english_name:
            return f"[{self.color}]{self.name} ({self.english_name})[/]"
        return f"[{self.color}]{self.name}[/]"

    def to_dict(self):
        return {
            "type": "item",
            "name": self.name,
            "description": self.description,
            "value": self.value,
            "keyword": self.keyword,
            "english_name": self.english_name,
            "rarity": self.rarity,
            "color": self.color,
            "bonuses": self.bonuses if self.bonuses else {},
            "max_durability": self.max_durability,
            "current_durability": self.current_durability,
            "set_id": self.set_id,
            "is_unique": self.is_unique
        }
    
    @staticmethod
    def from_dict(data):
        if data['type'] == 'weapon':
            item = Weapon(data['name'], data['description'], data['value'], data['keyword'], 
                          data['min_dmg'], data['max_dmg'], data['slot'], 
                          data.get('rarity', "Common"), data.get('color', "white"), 
                          data.get('bonuses', {}), data.get('english_name', ""),
                          hands=data.get('hands', 1), accuracy=data.get('accuracy', 100),
                          max_durability=data.get('max_durability', 0),
                          set_id=data.get('set_id', ""), is_unique=data.get('is_unique', False))
        elif data['type'] == 'armor':
            item = Armor(data['name'], data['description'], data['value'], data['keyword'], 
                         data['defense'], data['slot'], 
                         data.get('rarity', "Common"), data.get('color', "white"), 
                         data.get('bonuses', {}), data.get('english_name', ""),
                         max_durability=data.get('max_durability', 0),
                         set_id=data.get('set_id', ""), is_unique=data.get('is_unique', False))
        else:
            item = Item(data['name'], data['description'], data['value'], data['keyword'], 
                        data.get('rarity', "Common"), data.get('color', "white"), 
                        data.get('bonuses', {}), data.get('english_name', ""),
                        max_durability=data.get('max_durability', 0),
                        set_id=data.get('set_id', ""), is_unique=data.get('is_unique', False))
        
        if 'max_durability' not in data or data['max_durability'] == 0:
            # Legacy Save Fix: Default to 100 if not present
            item.max_durability = 100
            
        # Load current durability if present (for saves), else default to max
        if 'current_durability' in data:
            item.current_durability = data['current_durability']
        else:
            item.current_durability = item.max_durability
            
        return item

class Weapon(Item):
    def __init__(self, name, description, value, keyword, min_dmg, max_dmg, slot='r_hand', rarity="Common", color="white", bonuses=None, english_name="", hands=1, accuracy=100, max_durability=100, set_id="", is_unique=False):
        super().__init__(name, description, value, keyword, rarity, color, bonuses, english_name, max_durability, set_id, is_unique)
        self.min_dmg = min_dmg
        self.max_dmg = max_dmg
        self.slot = slot
        self.hands = hands
        self.accuracy = accuracy
        
        # Apply Rarity Bonuses
        if self.bonuses.get('dmg'):
            self.min_dmg += self.bonuses['dmg']
            self.max_dmg += self.bonuses['dmg']
        if self.bonuses.get('acc'):
            self.accuracy += self.bonuses['acc']

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "type": "weapon",
            "min_dmg": self.min_dmg - self.bonuses.get('dmg', 0), # Store raw base stats to avoid double application
            "max_dmg": self.max_dmg - self.bonuses.get('dmg', 0),
            "slot": self.slot,
            "hands": self.hands,
            "accuracy": self.accuracy - self.bonuses.get('acc', 0)
        })
        return data

class Armor(Item):
    def __init__(self, name, description, value, keyword, defense, slot='body', rarity="Common", color="white", bonuses=None, english_name="", max_durability=100, set_id="", is_unique=False):
        super().__init__(name, description, value, keyword, rarity, color, bonuses, english_name, max_durability, set_id, is_unique)
        self.defense = defense
        self.slot = slot
        
        # Apply Rarity Bonuses
        if self.bonuses.get('def'):
            self.defense += self.bonuses['def']

    def to_dict(self):
        data = super().to_dict()
        data.update({
            "type": "armor",
            "defense": self.defense - self.bonuses.get('def', 0), # Store raw base
            "slot": self.slot
        })
        return data

class LootGenerator:
    @staticmethod
    def generate(item_proto, force_rarity=None, balance_manager=None):
        """Generates a new item instance based on prototype with chance for rarity upgrade."""
        import copy
        import random
        
        new_item = copy.deepcopy(item_proto)
        b = balance_manager
        
        # Skip rarity generation for consumables (they don't benefit from stat bonuses)
        if isinstance(new_item, Item) and not isinstance(new_item, (Weapon, Armor)):
            return new_item
        
        # Randomize initial durability (50% - 100%)
        if new_item.max_durability > 0:
            import math
            min_dur = math.ceil(new_item.max_durability * 0.5)
            new_item.current_durability = random.randint(min_dur, new_item.max_durability)
        
        roll = random.random()
        rarity_type = "Common"
        
        if force_rarity:
            rarity_type = force_rarity
        else:
             # Random Generation
             # Epic (1%), Rare (5%), Fine (20%)
             if roll < 0.01: rarity_type = "Epic"
             elif roll < 0.06: rarity_type = "Rare"
             elif roll < 0.26: rarity_type = "Fine"
        
        # Apply Rarity
        # Apply Rarity
        if rarity_type == "Epic":
            new_item.rarity = "Epic"
            new_item.color = "bold magenta"
            new_item.name = f"史詩的 {new_item.name}"
            new_item.value = int(new_item.value * 5)
            new_item.keyword += ";epic;purple"
            
            if isinstance(new_item, Weapon):
                # Epic Dmg: +8 ~ +12
                min_b = b.get('rarity', 'epic_dmg_min', 8) if b else 8
                max_b = b.get('rarity', 'epic_dmg_max', 12) if b else 12
                bonus_dmg = random.randint(min_b, max_b)
                new_item.bonuses['dmg'] = bonus_dmg
                new_item.min_dmg += bonus_dmg
                new_item.max_dmg += bonus_dmg
                new_item.description += f" (傷害 +{bonus_dmg})"
                
                # Add Stat Bonus (Two Stats)
                # Epic Stat: +3 ~ +5 (x2)
                min_s = b.get('rarity', 'epic_stat_min', 3) if b else 3
                max_s = b.get('rarity', 'epic_stat_max', 5) if b else 5
                stats = random.sample(['str', 'dex', 'luk', 'con'], 2)
                for stat in stats:
                    val = random.randint(min_s, max_s)
                    new_item.bonuses[stat] = val
                    new_item.description += f" ({stat.upper()} +{val})"
                
            elif isinstance(new_item, Armor):
                # Epic Def: +6 ~ +10
                min_b = b.get('rarity', 'epic_def_min', 6) if b else 6
                max_b = b.get('rarity', 'epic_def_max', 10) if b else 10
                bonus_def = random.randint(min_b, max_b)
                new_item.bonuses['def'] = bonus_def
                new_item.defense += bonus_def
                new_item.description += f" (防禦 +{bonus_def})"
                
                # Epic Stat: +3 ~ +5 (x2)
                min_s = b.get('rarity', 'epic_stat_min', 3) if b else 3
                max_s = b.get('rarity', 'epic_stat_max', 5) if b else 5
                stats = random.sample(['con', 'dex', 'int', 'str'], 2)
                for stat in stats:
                    val = random.randint(min_s, max_s)
                    new_item.bonuses[stat] = val
                    new_item.description += f" ({stat.upper()} +{val})"
            
            # Necklace/Ring Logic (Epic)
            if new_item.slot == 'neck':
                hp_min = b.get('rarity', 'epic_neck_hp_min', 81) if b else 81
                hp_max = b.get('rarity', 'epic_neck_hp_max', 150) if b else 150
                def_min = b.get('rarity', 'epic_neck_def_min', 3) if b else 3
                def_max = b.get('rarity', 'epic_neck_def_max', 5) if b else 5
                bonus_hp = random.randint(hp_min, hp_max)
                bonus_def = random.randint(def_min, def_max)
                new_item.bonuses['hp'] = new_item.bonuses.get('hp', 0) + bonus_hp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                new_item.description += f" (HP +{bonus_hp}, Def +{bonus_def})"
            elif new_item.slot == 'finger':
                mp_min = b.get('rarity', 'epic_ring_mp_min', 81) if b else 81
                mp_max = b.get('rarity', 'epic_ring_mp_max', 150) if b else 150
                def_min = b.get('rarity', 'epic_ring_def_min', 3) if b else 3
                def_max = b.get('rarity', 'epic_ring_def_max', 5) if b else 5
                bonus_mp = random.randint(mp_min, mp_max)
                bonus_def = random.randint(def_min, def_max)
                new_item.bonuses['mp'] = new_item.bonuses.get('mp', 0) + bonus_mp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                new_item.description += f" (MP +{bonus_mp}, Def +{bonus_def})"

        elif rarity_type == "Rare":
            new_item.rarity = "Rare"
            new_item.color = "bold blue"
            new_item.name = f"高級 {new_item.name}"
            new_item.value = int(new_item.value * 3)
            
            if isinstance(new_item, Weapon):
                # Rare Dmg: +4 ~ +7
                min_b = b.get('rarity', 'rare_dmg_min', 4) if b else 4
                max_b = b.get('rarity', 'rare_dmg_max', 7) if b else 7
                bonus_dmg = random.randint(min_b, max_b)
                new_item.bonuses['dmg'] = bonus_dmg
                new_item.min_dmg += bonus_dmg
                new_item.max_dmg += bonus_dmg
                new_item.description += f" (傷害 +{bonus_dmg})"
                
                # Add Stat Bonus
                # Rare Stat: +3 ~ +4
                min_s = b.get('rarity', 'rare_stat_min', 3) if b else 3
                max_s = b.get('rarity', 'rare_stat_max', 4) if b else 4
                stat = random.choice(['str', 'dex', 'luk'])
                val = random.randint(min_s, max_s)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"
                
            elif isinstance(new_item, Armor):
                # Rare Def: +3 ~ +5
                min_b = b.get('rarity', 'rare_def_min', 3) if b else 3
                max_b = b.get('rarity', 'rare_def_max', 5) if b else 5
                bonus_def = random.randint(min_b, max_b)
                new_item.bonuses['def'] = bonus_def
                new_item.defense += bonus_def
                new_item.description += f" (防禦 +{bonus_def})"
                
                # Add Stat Bonus
                min_s = b.get('rarity', 'rare_stat_min', 3) if b else 3
                max_s = b.get('rarity', 'rare_stat_max', 4) if b else 4
                stat = random.choice(['con', 'dex', 'int'])
                val = random.randint(min_s, max_s)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"

            # Necklace/Ring Logic (Rare)
            if new_item.slot == 'neck':
                hp_min = b.get('rarity', 'rare_neck_hp_min', 31) if b else 31
                hp_max = b.get('rarity', 'rare_neck_hp_max', 80) if b else 80
                def_min = b.get('rarity', 'rare_neck_def_min', 1) if b else 1
                def_max = b.get('rarity', 'rare_neck_def_max', 2) if b else 2
                bonus_hp = random.randint(hp_min, hp_max)
                bonus_def = random.randint(def_min, def_max)
                new_item.bonuses['hp'] = new_item.bonuses.get('hp', 0) + bonus_hp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                new_item.description += f" (HP +{bonus_hp}, Def +{bonus_def})"
            elif new_item.slot == 'finger':
                mp_min = b.get('rarity', 'rare_ring_mp_min', 31) if b else 31
                mp_max = b.get('rarity', 'rare_ring_mp_max', 80) if b else 80
                def_min = b.get('rarity', 'rare_ring_def_min', 1) if b else 1
                def_max = b.get('rarity', 'rare_ring_def_max', 2) if b else 2
                bonus_mp = random.randint(mp_min, mp_max)
                bonus_def = random.randint(def_min, def_max)
                new_item.bonuses['mp'] = new_item.bonuses.get('mp', 0) + bonus_mp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                new_item.description += f" (MP +{bonus_mp}, Def +{bonus_def})"
        
        elif rarity_type == "Fine":
            new_item.rarity = "Fine"
            new_item.color = "green"
            new_item.name = f"精良的 {new_item.name}"
            new_item.value = int(new_item.value * 1.5)
            new_item.keyword += ";fine"
            
            if isinstance(new_item, Weapon):
                # Fine Dmg: +1 ~ +3
                min_b = b.get('rarity', 'fine_dmg_min', 1) if b else 1
                max_b = b.get('rarity', 'fine_dmg_max', 3) if b else 3
                bonus_dmg = random.randint(min_b, max_b)
                new_item.bonuses['dmg'] = bonus_dmg
                new_item.min_dmg += bonus_dmg
                new_item.max_dmg += bonus_dmg
                new_item.description += f" (傷害 +{bonus_dmg})"
                
                # Add Stat Bonus
                # Fine Stat: +1 ~ +2
                min_s = b.get('rarity', 'fine_stat_min', 1) if b else 1
                max_s = b.get('rarity', 'fine_stat_max', 2) if b else 2
                stat = random.choice(['str', 'dex'])
                val = random.randint(min_s, max_s)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"
                
            elif isinstance(new_item, Armor):
                # Fine Def: +1 ~ +2
                min_b = b.get('rarity', 'fine_def_min', 1) if b else 1
                max_b = b.get('rarity', 'fine_def_max', 2) if b else 2
                bonus_def = random.randint(min_b, max_b)
                new_item.bonuses['def'] = bonus_def
                new_item.defense += bonus_def
                new_item.description += f" (防禦 +{bonus_def})"
                
                # Add Stat Bonus
                min_s = b.get('rarity', 'fine_stat_min', 1) if b else 1
                max_s = b.get('rarity', 'fine_stat_max', 2) if b else 2
                stat = random.choice(['con', 'dex'])
                val = random.randint(min_s, max_s)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"

            # Necklace/Ring Logic (Fine)
            if new_item.slot == 'neck':
                hp_min = b.get('rarity', 'fine_neck_hp_min', 10) if b else 10
                hp_max = b.get('rarity', 'fine_neck_hp_max', 30) if b else 30
                def_min = b.get('rarity', 'fine_neck_def_min', 0) if b else 0
                def_max = b.get('rarity', 'fine_neck_def_max', 1) if b else 1
                bonus_hp = random.randint(hp_min, hp_max)
                bonus_def = random.randint(def_min, def_max)
                new_item.bonuses['hp'] = new_item.bonuses.get('hp', 0) + bonus_hp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                if bonus_def > 0:
                    new_item.description += f" (HP +{bonus_hp}, Def +{bonus_def})"
                else:
                    new_item.description += f" (HP +{bonus_hp})"
            elif new_item.slot == 'finger':
                mp_min = b.get('rarity', 'fine_ring_mp_min', 10) if b else 10
                mp_max = b.get('rarity', 'fine_ring_mp_max', 30) if b else 30
                def_min = b.get('rarity', 'fine_ring_def_min', 0) if b else 0
                def_max = b.get('rarity', 'fine_ring_def_max', 1) if b else 1
                bonus_mp = random.randint(mp_min, mp_max)
                bonus_def = random.randint(def_min, def_max)
                new_item.bonuses['mp'] = new_item.bonuses.get('mp', 0) + bonus_mp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                if bonus_def > 0:
                    new_item.description += f" (MP +{bonus_mp}, Def +{bonus_def})"
                else:
                    new_item.description += f" (MP +{bonus_mp})"
        return new_item

class Shop:
    def __init__(self, name, description, prototypes, balance_manager=None):
        self.balance = balance_manager
        self.name = name
        self.description = description
        self.prototypes = prototypes  # List of Item prototypes
        self.inventory = []
        import time
        self.last_restock_time = time.time()
        self.restock()

    def restock(self):
        # 1. Limit Inventory
        max_items = 30
        if len(self.inventory) >= max_items:
            # Optional: Remove oldest common items to make space? 
            # For now, just stop restocking if full.
            return

        # 2. Ensure Quotas
        # Target: 1 Epic (Purple) - Chance, 3 Fine (Green), 2 Rare (Blue)
        counts = {"Epic": 0, "Fine": 0, "Rare": 0, "Common": 0}
        for item in self.inventory:
            counts[item.rarity] = counts.get(item.rarity, 0) + 1
            
        import random
        
        # Epic Chance (10% if none exist)
        if counts["Epic"] == 0 and random.random() < 0.1:
             equip_protos = [p for p in self.prototypes if isinstance(p, (Weapon, Armor))]
             if equip_protos:
                 proto = random.choice(equip_protos)
                 new_item = LootGenerator.generate(proto, force_rarity="Epic", balance_manager=self.balance)
                 self.inventory.append(new_item)
                 counts["Epic"] += 1
        
        # Fill Rare (Blue) - Target 2
        while counts["Rare"] < 2 and len(self.inventory) < max_items:
            # Pick random prototype that is equipment
            equip_protos = [p for p in self.prototypes if isinstance(p, (Weapon, Armor))]
            if not equip_protos: break
            
            proto = random.choice(equip_protos)
            new_item = LootGenerator.generate(proto, force_rarity="Rare", balance_manager=self.balance)
            self.inventory.append(new_item)
            counts["Rare"] += 1
            
        # Fill Fine (Green) - Target 3
        while counts["Fine"] < 3:
            equip_protos = [p for p in self.prototypes if isinstance(p, (Weapon, Armor))]
            if not equip_protos: break
            
            proto = random.choice(equip_protos)
            new_item = LootGenerator.generate(proto, force_rarity="Fine", balance_manager=self.balance)
            self.inventory.append(new_item)
            counts["Fine"] += 1
            
        # Fill Common - Target 25 (Consumables + Equipment)
        while counts["Common"] < 25:
            if not self.prototypes: break
            proto = random.choice(self.prototypes) # Any item
            # Common is default
            new_item = LootGenerator.generate(proto, force_rarity="Common", balance_manager=self.balance) 
            self.inventory.append(new_item)
            counts["Common"] += 1
            
        # Sort inventory for nicer display? (Optional, maybe by Price or Rarity)
        self.inventory.sort(key=lambda x: x.value)

class Room:
    def __init__(self, name, description, symbol=' . ', zone='none'):
        self.name = name
        self.description = description
        self.symbol = symbol
        self.zone = zone
        self.exits = {}  # {'n': (x, y), ...}
        self.enemies = []  # List of Enemy objects
        self.items = [] # List of Item objects
        self.shop = None # Shop object if present
        
        # Respawn Logic
        self.enemy_spawn_defs = [] # List of enemy_proto_ids that belong here
        self.respawn_queue = [] # List of (proto_id, respawn_time)

class World:
    def __init__(self):
        self.grid = {}  # (x, y) -> Room
        self.width = 0
        self.height = 0

    def add_room(self, x, y, room):
        self.grid[(x, y)] = room

    def get_room(self, x, y):
        return self.grid.get((x, y))

class Player:
    def __init__(self, name, start_x=0, start_y=0, balance_manager=None):
        self.balance = balance_manager
        self.name = name
        self.x = start_x
        self.y = start_y
        self.visited = set()
        self.visited.add((start_x, start_y))
        
        # Core Attributes
        self.str = 10  # Strength - Physical Damage
        self.dex = 10  # Dexterity - Defense / Hit Chance
        self.con = 10  # Constitution - Max HP / Stamina
        self.int = 10  # Intelligence - Magic Power / MP
        self.wis = 10  # Wisdom - Magic Defense / MP Regen
        self.cha = 10  # Charisma - Shop Prices / Persuasion
        self.luk = 10  # Luck - Critical Hits / Drops
        
        # Stats
        self.level = 1
        self.str = 10 # Strength (Phy Dmg)
        self.dex = 10 # Dexterity (Defense, MV, Stealth)
        self.con = 10 # Constitution (HP, Regen)
        self.int = 10 # Intelligence (MP, Magic)
        self.luk = 10 # Luck (Crit, Drop)
        self.wis = 10 # Wisdom (Legacy/Secondary)
        self.cha = 10 # Charisma (Legacy/Shop)
        
        # Equipment (Simplified)
        self.equipment = {
            'r_hand': None,
            'l_hand': None,
            'head': None,
            'neck': None,
            'body': None,
            'legs': None,
            'feet': None, 
            'finger': None
        }
        self.inventory = [] # List of Item objects
        
        # Stats (Derived)
        self.recalculate_stats()
        self.hp = self.max_hp
        self.mp = self.max_mp
        self.mv = self.max_mv

        self.xp = 0
        self.next_level_xp = 1000
        self.last_attack_time = 0.0 # Ready to attack
        self.gold = 200 # Starting gold
        self.stat_points = 0 # New: Points to allocate
        
        # Skills
        self.skills = {} # {skill_name: proficiency_percent}
        
        # Status Effects (blind, knockdown, etc.)
        self.status_effects = {} # {status_name: turns_remaining}
        
        # Resting State
        self.is_sitting = False  # Track if player is sitting down
        self.is_sneaking = False # Stealth mode (潛行)
        self.fountain_last_use = 0.0 # Fountain cooldown timestamp


    def get_stat(self, stat_name):
        val = getattr(self, stat_name, 0)
        bonus = 0
        for item in self.equipment.values():
            if item and item.bonuses: 
                bonus += item.bonuses.get(stat_name, 0)
        return val + bonus
        
    def get_stat_breakdown(self, stat_name):
        base = getattr(self, stat_name, 0)
        bonus = 0
        for item in self.equipment.values():
            if item and item.bonuses:
                bonus += item.bonuses.get(stat_name, 0)
        return base, bonus

    def recalculate_stats(self):
        # Base Stats from Attributes
        con = self.get_stat('con')
        int_stat = self.get_stat('int')
        wis = self.get_stat('wis')
        dex = self.get_stat('dex')
        
        hp_per_con = 10
        hp_per_level = 10
        hp_base = 50
        mp_per_int = 10
        mp_per_level = 5
        mv_per_dex = 10
        mv_per_con = 10
        mv_base = 300
        
        if self.balance:
            hp_per_con = self.balance.get('player', 'hp_per_con', 10)
            hp_per_level = self.balance.get('player', 'hp_per_level', 10)
            hp_base = self.balance.get('player', 'hp_base', 50)
            mp_per_int = self.balance.get('player', 'mp_per_int', 10)
            mp_per_level = self.balance.get('player', 'mp_per_level', 5)
            mv_per_dex = self.balance.get('player', 'mv_per_dex', 10)
            mv_per_con = self.balance.get('player', 'mv_per_con', 10)
            mv_base = self.balance.get('player', 'mv_base', 300)

        self.max_hp = con * hp_per_con + self.level * hp_per_level + hp_base
        self.max_mp = int_stat * mp_per_int + self.level * mp_per_level
        self.max_mv = dex * mv_per_dex + con * mv_per_con + mv_base
        
        # Add Direct Bonuses from Equipment (HP/MP from Necklace/Ring)
        for item in self.equipment.values():
            if item and item.bonuses:
                self.max_hp += item.bonuses.get('hp', 0)
                self.max_mp += item.bonuses.get('mp', 0)
                self.max_mv += item.bonuses.get('mv', 0)
        
        # Clamp current values if they exceed max
        if hasattr(self, 'hp'): self.hp = min(self.hp, self.max_hp)
        if hasattr(self, 'mp'): self.mp = min(self.mp, self.max_mp)
        if hasattr(self, 'mv'): self.mv = min(self.mv, self.max_mv)
    
    def get_attack_range(self):
        # Calculate Base Damage
        str_val = self.get_stat('str')
        min_d = 2 + (str_val // 2)
        max_d = 5 + (str_val // 2)
        
        # Check Weapons (Main Hand)
        r_hand = self.equipment.get('r_hand')
        if r_hand and hasattr(r_hand, 'min_dmg'):
            min_d += r_hand.min_dmg
            max_d += r_hand.max_dmg
            
        # Check Off Hand
        l_hand = self.equipment.get('l_hand')
        if l_hand and hasattr(l_hand, 'min_dmg'):
            min_d += l_hand.min_dmg
            max_d += l_hand.max_dmg
            
        return min_d, max_d

    def get_defense(self):
        defense = self.get_stat('dex') // 2
        for item in self.equipment.values():
            if item:
                # Add item defense (Armor objects have .defense)
                if hasattr(item, 'defense'):
                    defense += item.defense
                # Add bonus defense (from Rings/Necklaces/Shields if in bonus)
                if item.bonuses:
                    defense += item.bonuses.get('def', 0)
        return defense

    def regenerate(self):
        # Base Regen
        hp_reg = max(1, self.con // 5)
        mp_reg = max(1, self.wis // 5)
        mv_reg = max(1, self.dex // 5)
        
        # Sitting Bonus
        if self.is_sitting:
            mv_reg *= 3
            hp_reg *= 2 # Multiplicative bonus to HP regen
        
        self.hp = min(self.max_hp, self.hp + hp_reg)
        self.mp = min(self.max_mp, self.mp + mp_reg)
        self.mv = min(self.max_mv, self.mv + mv_reg)

    def gain_xp(self, amount):
        old_level = self.level
        self.xp += amount
        # Simple leveling formula
        while self.xp >= self.next_level_xp:
            self.xp -= self.next_level_xp
            self.level += 1
            self.next_level_xp = int(self.next_level_xp * 1.2)
            
            # Stat growth
            self.str += 1
            self.dex += 1
            self.con += 1
            self.int += 1
            self.luk += 1
            
            points = 2
            if self.balance:
                points = self.balance.get('player', 'stat_points_per_level', 2)
            self.stat_points += points # Points per level
            
            xp_multiplier = 1.2
            if self.balance:
                xp_multiplier = self.balance.get('player', 'xp_multiplier', 1.2)
            self.next_level_xp = int(self.next_level_xp * xp_multiplier)
            
            self.recalculate_stats()
            # Heal on level up
            self.hp = self.max_hp
            self.mp = self.max_mp
            self.mv = self.max_mv
            
        return self.level > old_level


    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        self.visited.add((self.x, self.y))
        # Movement cost
        self.mv = max(0, self.mv - 1)

    def has_status(self, status_name):
        """Check if player has an active status effect (致盲/擊倒等)"""
        return self.status_effects.get(status_name, 0) > 0

    def tick_status_effects(self):
        """Decrement all status effect timers. Remove expired ones."""
        expired = []
        for key in list(self.status_effects.keys()):
            self.status_effects[key] -= 1
            if self.status_effects[key] <= 0:
                expired.append(key)
        for key in expired:
            del self.status_effects[key]
        return expired

class SaveManager:
    SAVE_DIR = "saves"
    
    def __init__(self, game_instance):
        self.game = game_instance
        os.makedirs(self.SAVE_DIR, exist_ok=True)

    def _get_save_path(self, slot):
        return os.path.join(self.SAVE_DIR, f"save_{slot}.json")

    def save_game(self, slot):
        player_data = {
            "name": self.game.player.name,
            "x": self.game.player.x,
            "y": self.game.player.y,
            "visited": list(self.game.player.visited),
            "str": self.game.player.str,
            "dex": self.game.player.dex,
            "con": self.game.player.con,
            "int": self.game.player.int,
            "wis": self.game.player.wis,
            "cha": self.game.player.cha,
            "luk": self.game.player.luk,
            "level": self.game.player.level,
            "hp": self.game.player.hp,
            "mp": self.game.player.mp,
            "mv": self.game.player.mv,
            "xp": self.game.player.xp,
            "next_level_xp": self.game.player.next_level_xp,
            "gold": self.game.player.gold,
            "stat_points": self.game.player.stat_points,
            "equipment": {k: (v.to_dict() if v else None) for k, v in self.game.player.equipment.items()},
            "inventory": [item.to_dict() for item in self.game.player.inventory],
            "fountain_last_use": self.game.player.fountain_last_use,
        }

        world_data = {
            "game_time": self.game.game_time,
            "rooms": {}
        }
        for (x, y), room in self.game.world.grid.items():
            room_data = {
                "enemies": [{
                    "name": e.name, "hp": e.hp, "is_aggressive": e.is_aggressive,
                    "proto_id": e.proto_id, "debuffs": dict(e.debuffs),
                    "inventory": [item.to_dict() for item in e.inventory]
                } for e in room.enemies],
                "items": [(i.name, i.drop_time) for i in room.items],
                "respawn_queue": room.respawn_queue,
            }
            world_data["rooms"][f"{x},{y}"] = room_data

        save_data = {
            "player": player_data,
            "world": world_data,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "location_name": self.game.world.get_room(self.game.player.x, self.game.player.y).name
        }

        try:
            with open(self._get_save_path(slot), 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=4)
            self.game.log(f"[green]遊戲已儲存至 {slot} 槽位。[/]")
            return True
        except Exception as e:
            self.game.log(f"[red]儲存遊戲失敗: {e}[/]")
            return False

    def load_game(self, slot):
        import copy # Fix for UnboundLocalError
        save_path = self._get_save_path(slot)
        if not os.path.exists(save_path):
            self.game.log(f"[red]找不到 {slot} 槽位的存檔。[/]")
            return False

        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)

            # Reset game state before loading
            self.game.setup_world() # Re-initialize world structure
            
            player_data = save_data["player"]
            self.game.player = Player(player_data["name"], player_data["x"], player_data["y"])
            self.game.player.visited = set(tuple(v) for v in player_data["visited"]) # Convert list of lists to set of tuples
            self.game.player.str = player_data["str"]
            self.game.player.dex = player_data["dex"]
            self.game.player.con = player_data["con"]
            self.game.player.int = player_data["int"]
            self.game.player.wis = player_data["wis"]
            self.game.player.cha = player_data["cha"]
            self.game.player.luk = player_data["luk"]
            self.game.player.level = player_data["level"]
            self.game.player.hp = player_data["hp"]
            self.game.player.mp = player_data["mp"]
            self.game.player.mv = player_data["mv"]
            self.game.player.xp = player_data["xp"]
            self.game.player.next_level_xp = player_data["next_level_xp"]
            self.game.player.gold = player_data["gold"]
            self.game.player.stat_points = player_data["stat_points"]
            self.game.player.fountain_last_use = player_data.get("fountain_last_use", 0.0)
            self.game.player.recalculate_stats() # Ensure max_hp, etc. are correct

            # Load equipment
            for slot_name, item_data in player_data["equipment"].items():
                if item_data:
                    # Backward compatibility for old saves (string names)
                    if isinstance(item_data, str):
                        item = self.game.loader.get_item_by_name(item_data)
                    else:
                        item = Item.from_dict(item_data)
                        
                    if item:
                        self.game.player.equipment[slot_name] = item
                    else:
                        self.game.log(f"[yellow]警告: 找不到裝備物品 '{item_data}'。[/]")
            
            # Load inventory
            self.game.player.inventory = []
            for item_data in player_data["inventory"]:
                # Backward compatibility
                if isinstance(item_data, str):
                     item = self.game.loader.get_item_by_name(item_data)
                else:
                     item = Item.from_dict(item_data)

                if item:
                    self.game.player.inventory.append(item)
                else:
                    self.game.log(f"[yellow]警告: 找不到背包物品 '{item_data}'。[/]")

            # Load world state
            self.game.game_time = save_data["world"]["game_time"]
            
            # Optimization: Create a set for fast lookup
            visited_set = self.game.player.visited
            
            for coord_str, room_data in save_data["world"]["rooms"].items():
                x, y = map(int, coord_str.split(','))
                
                # Skip loading state for unvisited rooms.
                # This allow updates to rooms.csv (like new enemies) to take effect
                # for areas the player hasn't explored yet.
                if (x, y) not in visited_set:
                    continue

                room = self.game.world.get_room(x, y)
                if room:
                    room.enemies = []
                    for e_data in room_data["enemies"]:
                        # Backward compatible: old format is list/tuple, new is dict
                        if isinstance(e_data, dict):
                            e_proto_id = e_data['proto_id']
                            e_hp = e_data['hp']
                            e_aggro = e_data['is_aggressive']
                            e_debuffs = e_data.get('debuffs', {})
                            e_inventory_data = e_data.get('inventory', [])
                        else:
                            # Old tuple format: (name, hp, aggro, proto_id)
                            _, e_hp, e_aggro, e_proto_id = e_data
                            e_debuffs = {}
                            e_inventory_data = []
                        
                        proto_enemy = self.game.loader.enemies.get(e_proto_id)
                        if proto_enemy:
                            new_enemy = copy.deepcopy(proto_enemy)
                            new_enemy.hp = e_hp
                            new_enemy.is_aggressive = e_aggro
                            new_enemy.proto_id = e_proto_id
                            new_enemy.debuffs = e_debuffs
                            # Restore inventory
                            new_enemy.inventory = []
                            for inv_data in e_inventory_data:
                                inv_item = Item.from_dict(inv_data)
                                if inv_item:
                                    new_enemy.inventory.append(inv_item)
                            room.enemies.append(new_enemy)
                        else:
                            self.game.log(f"[yellow]警告: 找不到敵人原型 '{e_proto_id}'。[/]")
                            
                    room.items = []
                    for i_name, drop_time in room_data["items"]:
                        item = self.game.loader.get_item_by_name(i_name)
                        if item:
                            item.drop_time = drop_time
                            room.items.append(item)
                        else:
                             self.game.log(f"[yellow]警告: 找不到掉落物品 '{i_name}'。[/]")
                            
                    room.respawn_queue = room_data.get("respawn_queue", [])

                    # Retroactive Population Fix:
                    # If room has no enemies AND no respawn queue, but static data says it should have one (and it's not a boss room that was cleared),
                    # spawn it. This fixes "Empty North" in old saves.
                    # We need to distinguish "Legitimately Empty" (killed) from "Generated Empty" (old version).
                    # Since we don't have a "killed" flag other than respawn_queue...
                    # If respawn_queue is empty, it means either:
                    # 1. Never had enemy.
                    # 2. Enemy alive (should be in room.enemies).
                    # 3. Enemy killed long ago? (But respawn queue handles respawn... if timer expired, it spawns).
                    # So if enemies=[] and respawn_queue=[], it means "Empty".
                    # If static rooms.csv has enemy_id, we should populate it.
                    # Exception: Unique Bosses? If we want them to stay dead.
                    # But for now, let's repopulate everything to be safe for the user.
                    if not room.enemies and not room.respawn_queue:
                         # Check static definition
                         static_id = str(room.y * 1000 + room.x) # Wait, need ID lookup. 
                         # We don't have easy RoomID lookup by (x,y) in game.world usually, 
                         # but DataLoader.rooms has it by ID.
                         # We need to find the room in DataLoader to get its prototype enemy_id.
                         # This is slow O(N) search unless we optimize. 
                         # But load_game is one-time.
                         
                         # Better: DataLoader.rooms is keyed by ID string.
                         # room object doesn't know its ID?
                         # Let's search by coordinate in self.loader.rooms
                         
                         target_proto_id = None
                         for r_id, r_proto in self.game.loader.rooms.items():
                             if r_proto.x == x and r_proto.y == y:
                                 # Found static definition
                                 # Wait, r_proto.enemies is a list of instances now (in my modified loader)?
                                 # No, loader.load_rooms creates Room objects with initial enemies.
                                 # But we don't store the "Definition Enemy ID" on the Room object directly in a clean way?
                                 # Logic in load_rooms:
                                 # if row['enemy_id'] ... room.enemies.append(...)
                                 # It seems we didn't store raw enemy_id on the room.
                                 
                                 # Let's check Room class.
                                 pass
                                 
                         # Alternative: Just re-run the spawn logic from existing DataLoader rooms?
                         # Yes. DataLoader.rooms has the "fresh" state layout.
                         # We can match by coordinates.
                         
                         for r_id, static_room in self.game.loader.rooms.items():
                             if static_room.x == x and static_room.y == y:
                                 if static_room.enemies:
                                      # Valid enemy exists in static data
                                      # Copy them over!
                                      # Note: static_room.enemies already has fresh copies from load_rooms()
                                      # import copy # REMOVED: Causing UnboundLocalError
                                      for static_e in static_room.enemies:
                                          room.enemies.append(copy.deepcopy(static_e))
                                      # self.game.log(f"Repopulated ({x},{y})") # Debug
                                 break
                else:
                    self.game.log(f"[yellow]警告: 找不到座標 ({x},{y}) 的房間。[/]")

            self.game.log(f"[green]遊戲已從 {slot} 槽位載入。[/]")
            return True
        except Exception as e:
            self.game.log(f"[red]載入遊戲失敗: {e}[/]")
            import traceback
            traceback.print_exc()
            input("按 Enter 鍵繼續...")
            return False

    def get_save_info(self, slot):
        save_path = self._get_save_path(slot)
        if not os.path.exists(save_path):
            return None
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            player_level = save_data["player"]["level"]
            location_name = save_data["location_name"]
            timestamp = save_data["timestamp"]
            
            player_name = save_data["player"].get("name", "Unknown")
            player_str = save_data["player"].get("str", 0)
            player_dex = save_data["player"].get("dex", 0)
            player_con = save_data["player"].get("con", 0)
            player_luk = save_data["player"].get("luk", 0)

            return {
                "name": player_name,
                "level": player_level,
                "location_name": location_name,
                "str": player_str,
                "dex": player_dex,
                "con": player_con,
                "luk": player_luk,
                "time": timestamp
            }
        except Exception:
            return None

class Game:
    def __init__(self):
        print("DEBUG: Loaded MUD_Main (v8 - fix help display)")
        self.log_history = []  # List of strings/manageable objects
        self.aliases = {}
        self.commands = set()
        self.console = Console()
        self.world = World()
        self.data_dir = "data" # Assuming data directory
        self.loader = DataLoader(self.data_dir)
        self.balance = self.loader.balance
        self.skills_data = self.loader.load_skills(os.path.join(self.data_dir, 'skills.csv')) # Load Skills
        # Load from settings, default to 25 if not found
        self.max_log_lines = int(self.loader.settings.get('max_log_lines', 25))
        self.save_manager = SaveManager(self)
        self.setup_world()
        self.player = Player("Hero", balance_manager=self.balance) # Pass balance manager
        
        # Time System
        self.game_time = 360 # 6:00 AM (in minutes)
        self.running = True
        
    def get_time_str(self):
        hours = (self.game_time // 60) % 24
        mins = self.game_time % 60
        day = (self.game_time // 1440) + 1
        period = "Day" if 6 <= hours < 18 else "Night"
        return f"Day {day} {hours:02d}:{mins:02d} ({period})"

    def update_time(self, mins=1):
        self.game_time += mins
        # Aggression check (e.g. while waiting/resting)
        # We only check if we are NOT in the middle of processing a move (which calls this)
        # Actually it's fine. If we just moved, we check twice? 
        # process_move calls update_time BEFORE check_room_aggression.
        # So we can put it here to cover "wait", "rest", AND "move".
        # But process_move calls check_room_aggression explicitly at the end.
        # Let's avoid double trigger.
        # We can just keep it explicit in process_move.
        # But 'rest' and 'wait' commands call update_time?
        # Let's see. If I call check_room_aggression here, process_move calls it again.
        # That means double chance? or double attack?
        # Since check_room_aggression triggers handle_enemy_turn, double attack sucks.
        pass
        
    def check_aggression_periodic(self):
        # Helper for Wait/Rest commands
        self.check_room_aggression()

    def get_skill_cost(self, skill_id):
        """Calculates dynamic MP/MV cost based on base cost, level, and zone."""
        skill = self.skills_data.get(skill_id)
        if not skill:
            return 0, 'none'
            
        base_cost = int(skill.get('cost', 0))
        cost_type = skill.get('cost_type', 'none')
        
        if cost_type == 'none':
            return 0, 'none'
            
        # 1. Level-based scaling: 2% increase per level above 1
        level_mult = 1.0 + (self.player.level - 1) * 0.02
        
        # 2. Zone-based scaling
        curr_room = self.world.get_room(self.player.x, self.player.y)
        zone_mult = 1.0
        if curr_room:
            zone = getattr(curr_room, 'zone', 'none')
            if zone in ['mines', 'wasteland']:
                zone_mult = 1.2
            elif zone == 'nexus':
                zone_mult = 1.5
        
        final_cost = int(base_cost * level_mult * zone_mult)
        return final_cost, cost_type
        
    def setup_world(self):
        # Clear existing world data
        self.world = World()
        self.loader.load_all()
        self.aliases, self.commands, self.help_data = self.loader.load_commands()
        
        # Build World from Loaded Rooms
        for r_id, room in self.loader.rooms.items():
            if hasattr(room, 'x') and hasattr(room, 'y'):
                # Apply initial scaling to enemies in room
                for e in room.enemies:
                    e.scale_to_player(self.player.level if hasattr(self, 'player') else 1) # Player might not be ready in init, assume 1?
                
                self.world.add_room(room.x, room.y, room)
                
                if hasattr(room, '_raw_exits') and room._raw_exits:
                    for exit_def in room._raw_exits.split(';'):
                        if ':' in exit_def:
                            d, target_id = exit_def.split(':')
                            if target_id in self.loader.rooms:
                                target_room = self.loader.rooms[target_id]
                                if hasattr(target_room, 'x') and hasattr(target_room, 'y'):
                                    room.exits[d] = (target_room.x, target_room.y)

    def log(self, message):
        """Append message to log history."""
        # Split multiline messages
        for line in message.split('\n'):
            self.log_history.append(line)
            if len(self.log_history) > self.max_log_lines:
                self.log_history.pop(0) # Remove oldest line if history exceeds max
        
        # Debug File Log
        try:
            with open("debug.txt", "a", encoding="utf-8") as f:
                import datetime
                timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                # Strip rich tags for plain text log if possible, or just dump
                clean_msg = message.replace("[", "<").replace("]", ">") 
                f.write(f"[{timestamp}] {clean_msg}\n")
        except:
            pass

    def generate_layout(self):
        layout = Layout()
        layout.split_column(
            Layout(name="main", ratio=9),
            Layout(name="footer", size=3)
        )
        layout["main"].split_row(
            Layout(name="left", ratio=2),
            Layout(name="right", ratio=1)
        )
        layout["main"]["right"].split_column(
            Layout(name="status", size=10),
            Layout(name="equipment", size=10),
            Layout(name="map")
        )
        return layout

    def get_status_panel(self):
        p = self.player
        # Create a grid or table for status
        grid = Table.grid(expand=True)
        grid.add_column()
        grid.add_column(justify="right")
        
        grid.add_row(f"[bold]Level[/bold] {p.level}", f"[bold]XP[/bold] {p.xp}/{p.next_level_xp}")
        grid.add_row(f"[red]HP[/red]", f"{p.hp}/{p.max_hp}")
        grid.add_row(f"[blue]MP[/blue]", f"{p.mp}/{p.max_mp}")
        grid.add_row(f"[yellow]MV[/yellow]", f"{p.mv}/{p.max_mv}")
        grid.add_row("","")
        
        str_base, str_bonus = p.get_stat_breakdown('str')
        dex_base, dex_bonus = p.get_stat_breakdown('dex')
        con_base, con_bonus = p.get_stat_breakdown('con')
        int_base, int_bonus = p.get_stat_breakdown('int')
        luk_base, luk_bonus = p.get_stat_breakdown('luk')
        
        def fmt_stat(name, base, bonus):
            if bonus > 0: return f"[bold]{name}[/bold] [green]{base}+{bonus}[/]"
            return f"[bold]{name}[/bold] {base}"

        grid.add_row(fmt_stat("STR", str_base, str_bonus), fmt_stat("INT", int_base, int_bonus))
        grid.add_row(fmt_stat("DEX", dex_base, dex_bonus), fmt_stat("LUK", luk_base, luk_bonus))
        grid.add_row(fmt_stat("CON", con_base, con_bonus), "")
        
        if p.stat_points > 0:
             grid.add_row(f"[bold yellow]Points: {p.stat_points}[/]", "")
        
        str_display = f"{str_base} [green](+{str_bonus})[/]" if str_bonus > 0 else f"{str_base}"
        dex_display = f"{dex_base} [green](+{dex_bonus})[/]" if dex_bonus > 0 else f"{dex_base}"
        con_display = f"{con_base} [green](+{con_bonus})[/]" if con_bonus > 0 else f"{con_base}"
        
        grid.add_row("STR", str_display)
        grid.add_row("DEX", dex_display)
        grid.add_row("CON", con_display)
        
        # Derived Stats
        min_d, max_d = p.get_attack_range()
        defense = p.get_defense()
        grid.add_row("[red]ATK[/red]", f"{min_d}-{max_d}")
        grid.add_row("[blue]DEF[/blue]", str(defense))
        
        # grid.add_row("CON", str(p.con))
        # grid.add_row("INT", str(p.int))
        
        if p.is_sitting:
             grid.add_row("[yellow]Status[/yellow]", "[yellow]Sitting[/yellow]")

        curr_room = self.world.get_room(p.x, p.y)
        return Panel(
            grid,
            title=f"[bold]{p.name if hasattr(p, 'name') else 'Hero'} (Lv{p.level})[/bold]",
            subtitle=f"{curr_room.name if curr_room else 'Unknown'}",
            border_style="green"
        )

    def get_map_panel(self, radius=8): # Adjusted radius
        # Generate Map String
        output_lines = []
        for y in range(self.player.y + radius, self.player.y - radius - 1, -1):
            line = ""
            for x in range(self.player.x - radius, self.player.x + radius + 1):
                if x == self.player.x and y == self.player.y:
                    room = self.world.get_room(x, y)
                    if room and room.enemies:
                        line += "[bold red] @ [/]"
                    else:
                        line += "[bold white] @ [/]" 
                elif (x, y) in self.player.visited:
                    room = self.world.get_room(x, y)
                    if room:
                        if room.enemies:
                            # Boss Check (Robust)
                            is_boss = False
                            for e in room.enemies:
                                try:
                                    eid = getattr(e, 'id', '') or ''
                                    if eid.startswith('boss'):
                                        is_boss = True
                                        break
                                except AttributeError:
                                    print(f"DEBUG: Bad enemy in room ({x},{y}): {e}")
                                    
                            line += "<b>[bold red] B [/]</b>" if is_boss else " [red]E[/] "
                        else:
                            line += room.symbol
                    else:
                        line += " . " 
                else:
                    line += "   " 
            output_lines.append(line)
        
        return Panel(
            "\n".join(output_lines),
            title=f"Map ({self.player.x}, {self.player.y})",
            border_style="blue"
        )
    
    def get_equipment_panel(self):
        eq_text = ""
        slot_map = {
             'r_hand': 'E1', 'l_hand': 'E2',
             'head': 'E3', 'neck': 'E4', 
             'body': 'E5', 'legs': 'E6', 
             'feet': 'E7', 'finger': 'E8'
        }
        
        # Define standard order for display
        order = ['r_hand', 'l_hand', 'head', 'neck', 'body', 'legs', 'feet', 'finger']
        
        for slot in order:
            item = self.player.equipment.get(slot)
            slot_id = slot_map.get(slot, '??')
            
            item_name = item.name if item else "Empty"
            color = "white" if item else "dim"
            
            dur_str = ""
            if item and hasattr(item, 'max_durability') and item.max_durability > 0:
                pct = int((item.current_durability / item.max_durability) * 100)
                dur_color = "green"
                if pct < 20: dur_color = "red"
                elif pct < 50: dur_color = "yellow"
                dur_str = f" [{dur_color}]({pct}%)[/]"
            
            eq_text += f"[{slot_id}] {slot.capitalize()}: [{color}]{item_name}[/]{dur_str}\n"
        
        return Panel(
            eq_text.strip(),
            title="Equipment",
            border_style="magenta"
        )

    def update_layout(self, layout, cmd_buffer="", scroll_offset=0):
        # Left: Log
        # We join with newlines. 
        # Handle Scrolling: Show last N lines, shifted by scroll_offset
        visible_lines = self.max_log_lines
        total_lines = len(self.log_history)
        
        if total_lines <= visible_lines:
            display_slice = self.log_history
        else:
            # logic: if offset is 0, show last visible_lines
            # if offset > 0, show (last - offset - visible) to (last - offset)
            end_idx = total_lines - scroll_offset
            start_idx = max(0, end_idx - visible_lines)
            display_slice = self.log_history[start_idx:end_idx]

        log_text = "\n".join(display_slice)
        title = f"Game Log (Scroll: {scroll_offset})" if scroll_offset > 0 else "Game Log"
        layout["main"]["left"].update(Panel(log_text, title=title, border_style="white"))
        
        # Right: Status, Equipment, Map
        layout["main"]["right"]["status"].update(self.get_status_panel())
        layout["main"]["right"]["equipment"].update(self.get_equipment_panel())
        layout["main"]["right"]["map"].update(self.get_map_panel())
        
        # Footer: Input
        layout["footer"].update(Panel(f"> {cmd_buffer}", title="Input", border_style="yellow"))

    def main_menu(self):
        while True:
            self.console.clear()
            self.console.print(Panel(Align.center("[bold cyan]MUD: The Age[/]\n[white]A Text RPG Adventure[/]"), style="bold blue"))
            self.console.print(Align.center("[1] New Game"))
            
            # Show Load Slots
            for i in range(1, 4):
                info = self.save_manager.get_save_info(i)
                if info:
                    stats = f"Lv{info['level']} {info['location_name']}"
                    if 'str' in info: stats += f" (STR:{info['str']} DEX:{info['dex']})"
                    self.console.print(Align.center(f"[{i+1}] Slot {i}: {info['name']} - {stats}"))
                else:
                    self.console.print(Align.center(f"[{i+1}] Slot {i}: [Empty]"))
                    
            auto_info = self.save_manager.get_save_info("auto")
            if auto_info:
                 self.console.print(Align.center(f"[5] Auto-Save: {auto_info['name']} (Lv{auto_info['level']})"))
            
            self.console.print(Align.center("[Q] Quit"))
            
            key = msvcrt.getch()
            if key in (b'\xe0', b'\x00'): msvcrt.getch(); continue
            try: choice = key.decode('utf-8').lower()
            except: continue
            
            if choice == '1':
                self.new_game()
                return # Start Game
            elif choice in ['2', '3', '4']:
                slot = int(choice) - 1
                if self.save_manager.load_game(slot):
                    self.log(f"[green]Save loaded (Slot {slot})![/]")
                    return # Start Game
            elif choice == '5':
                 if self.save_manager.load_game("auto"):
                    self.log(f"[green]Auto-save loaded![/]")
                    return # Start Game
            elif choice == 'q':
                sys.exit()

    def new_game(self):
        self.console.clear()
        self.setup_world()
        
        # Name Registration
        self.console.print("[bold yellow]Enter your character name:[/]")
        while True:
            # Use python input for name, but we need to handle rich console context maybe?
            # Simple input is fine.
            name = input("> ").strip()
            if len(name) > 0:
                break
        
        self.player = Player(name)
        self.log(f"Welcome, {name}!")
        
        # Starter Items
        red_potion = self.loader.items.get('item_healing_potion_s')
        blue_potion = self.loader.items.get('item_mana_potion_s')
        if red_potion:
            for _ in range(5):
                self.player.inventory.append(copy.deepcopy(red_potion))
        if blue_potion:
            for _ in range(5):
                self.player.inventory.append(copy.deepcopy(blue_potion))
        
        self.game_time = 360

    def run(self):
        # Main Menu
        self.main_menu()
                
        # --- Game Loop ---
                
        # --- Game Loop ---
        self.running = True
        self.log(f"歡迎來到 [bold magenta]MUD: The Age[/]!")
        self.log("遊戲開始！使用方向鍵移動，或輸入指令後按 Enter (例如 'quit')。")
        self.log("[dim]提示: 使用 PageUp/PageDown 或 \\[ / ] 捲動訊息紀錄。[/]")
        
        self.layout = self.generate_layout()
        
        with Live(self.layout, console=self.console, screen=True, refresh_per_second=20) as live:
            self.live_context = live # Optional, mostly for knowing we are live
            
            cmd_buffer = ""
            cursor_visible = True
            last_cursor_toggle = time.time()
            scroll_offset = 0 # 0 means at bottom
            
            self.update_layout(self.layout, cmd_buffer + "_", scroll_offset)
            last_regen_time = time.time()
            last_decay_check_time = time.time()
            last_shop_check_time = time.time() # Shop restock timer
            
            while self.running:
                current_time = time.time()
                
                # Regeneration (Every 5 seconds)
                if current_time - last_regen_time > 5.0:
                    self.player.regenerate()
                    last_regen_time = current_time
                
                # Item Decay (Every 10 seconds check)
                if current_time - last_decay_check_time > 10.0:
                    for room in self.world.grid.values():
                        if not room.items: continue
                        
                        items_to_remove = []
                        for item in room.items:
                            if item.drop_time and (current_time - item.drop_time > 300): # 300s = 5 mins
                                items_to_remove.append(item)
                        
                        for item in items_to_remove:
                            room.items.remove(item)
                            # Log if player is present
                            if room.x == self.player.x and room.y == self.player.y:
                                self.log(f"[dim]{item.name} 風化消失了...[/]")
                                
                    last_decay_check_time = current_time

                # Shop Restocking (Every 30 seconds check)
                if current_time - last_shop_check_time > 30.0:
                    interval = self.balance.get('world', 'shop_restock_interval', 300)
                    for r in self.world.grid.values():
                        if r.shop:
                            if current_time - r.shop.last_restock_time >= interval:
                                r.shop.restock()
                                r.shop.last_restock_time = current_time
                                if r.x == self.player.x and r.y == self.player.y:
                                    self.log(f"[bold yellow]{r.shop.name} 的貨架更新了！[/]")
                    last_shop_check_time = current_time

                # Respawn Logic (Check every 10 seconds or every loop? Every loop is fine, low overhead)
                # But to avoid spam checking every room every frame, maybe check once per second?
                # Let's check current room and maybe global every 5s.
                # Actually, iterate all rooms is fast enough for small map.
                if current_time % 5.0 < 0.1: # Rough check every 5s
                    for r in self.world.grid.values():
                        if r.respawn_queue:
                            temp_queue = []
                            for proto_id, respawn_at in r.respawn_queue:
                                if current_time >= respawn_at:
                                    # Respawn!
                                    if proto_id in self.loader.enemies:
                                        new_enemy = copy.deepcopy(self.loader.enemies[proto_id])
                                        new_enemy.proto_id = proto_id
                                        # Scale Enemy Logic
                                        new_enemy.scale_to_player(self.player.level)
                                        r.enemies.append(new_enemy)
                                        # Log if player in room
                                        if r.x == self.player.x and r.y == self.player.y:
                                             self.log(f"[bold red]一隻 {new_enemy.name} 出現了![/]")
                                else:
                                    temp_queue.append((proto_id, respawn_at))
                            r.respawn_queue = temp_queue

                # Blinking Cursor Logic
                if time.time() - last_cursor_toggle > 0.5:
                    cursor_visible = not cursor_visible
                    last_cursor_toggle = time.time()
                
                # Auto-Attack Logic (Player and Enemies in current room)
                curr_room = self.world.get_room(self.player.x, self.player.y)
                attack_interval = self.balance.get('combat', 'attack_interval', 1.0)
                
                if curr_room and curr_room.enemies:
                    # Player Auto-Attack
                    active_enemy = None
                    for e in curr_room.enemies:
                        if e.is_aggressive:
                            active_enemy = e
                            break
                    
                    if active_enemy and current_time - self.player.last_attack_time >= attack_interval:
                        # Dynamic Cost for Basic Attack
                        cost, c_type = self.get_skill_cost('basic_attack')
                        if getattr(self.player, c_type, 0) >= cost:
                            # Deduct Cost
                            if c_type == 'mp': self.player.mp -= cost
                            elif c_type == 'mv': self.player.mv -= cost
                            elif c_type == 'hp': self.player.hp -= cost

                            self.player.last_attack_time = current_time
                            p_dmg = self.calculate_player_damage()
                            self.log(f"[bold cyan]你自動攻擊了 {active_enemy.name}! (消耗 {cost} {c_type.upper()})[/]")
                            self.perform_attack(active_enemy, p_dmg, f"造成了")
                            if not active_enemy.is_alive():
                                self.resolve_turn(active_enemy, curr_room)
                        else:
                            self.log(f"[yellow]你太累了，無法發動攻擊！ (需要 {cost} {c_type.upper()})[/]")
                            self.player.last_attack_time = current_time # Still reset timer
                    
                    # Enemies Auto-Attack
                    for e in curr_room.enemies:
                        if e.is_aggressive and e.is_alive():
                            if current_time - e.last_attack_time >= attack_interval:
                                e.last_attack_time = current_time
                                self.handle_enemy_turn(e, curr_room)

                cursor_char = "_" if cursor_visible else " "
                
                # Update UI
                self.update_layout(self.layout, cmd_buffer + cursor_char, scroll_offset)
                live.refresh()
                
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    
                    # Special Key Handling
                    if ch in (b'\x00', b'\xe0'):
                        code = msvcrt.getch()
                        direction = None
                        
                        # Arrow Keys for Movement
                        if code == b'H': direction = 'n'
                        elif code == b'P': direction = 's'
                        elif code == b'K': direction = 'w'
                        elif code == b'M': direction = 'e'
                        
                        # Scrolling (PageUp=I, PageDown=Q)
                        elif code == b'I': 
                            scroll_offset += 5
                            max_scroll = max(0, len(self.log_history) - self.max_log_lines)
                            scroll_offset = min(scroll_offset, max_scroll)
                        elif code == b'Q':
                            scroll_offset -= 5
                            scroll_offset = max(0, scroll_offset)
                        
                        if direction:
                            self.process_move(direction)
                            scroll_offset = 0

                    # Fallback Scrolling Keys: [ (PageUp) and ] (PageDown)
                    elif ch == b'[':
                        scroll_offset += 5
                        max_scroll = max(0, len(self.log_history) - self.max_log_lines)
                        scroll_offset = min(scroll_offset, max_scroll)
                    elif ch == b']':
                        scroll_offset -= 5
                        scroll_offset = max(0, scroll_offset)
                        
                    elif ch == b'\r': # Enter
                        self.log(f"> {cmd_buffer}")
                        self.process_command(cmd_buffer.strip().lower())
                        cmd_buffer = ""
                        scroll_offset = 0
                    elif ch == b'\x08':
                        if len(cmd_buffer) > 0:
                            cmd_buffer = cmd_buffer[:-1]

                    # Ctrl+C
                    elif ch == b'\x03':
                        self.running = False
                        return

                    # Char
                    else:
                        try:
                            char_str = ch.decode('utf-8', errors='ignore')
                            if char_str.isprintable():
                                cmd_buffer += char_str
                        except:
                            pass
    
    def describe_room(self):
        curr_room = self.world.get_room(self.player.x, self.player.y)
        self.log(f"[bold yellow]{curr_room.name}[/]")
        self.log(curr_room.description)
        
        # Fountain Display at (0,0)
        if self.player.x == 0 and self.player.y == 0:
            import time
            elapsed = time.time() - self.player.fountain_last_use
            cooldown = 7200 # 2 hours
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                m, s = divmod(remaining, 60)
                h, m = divmod(m, 60)
                self.log(f"[cyan]此處有一座宏偉的噴水池... (冷卻中: {h:02d}:{m:02d}:{s:02d})[/]")
            else:
                self.log("[bold cyan]此處有一座宏偉的噴水池，池水清澈見底，散發著微弱的光芒。你可以喝點水 (drink water)。[/]")

        
        aggro_triggered = False
        if curr_room.enemies:
            names = []
            for e in curr_room.enemies:
                status = "[bold red]!![/]" if e.is_aggressive else ""
                names.append(f"{status}[red]{e.name}[/]")
                if e.is_aggressive: aggro_triggered = True
            self.log(f"生物: {', '.join(names)}")
            
        if curr_room.items:
            names = [i.get_display_name() for i in curr_room.items]
            self.log(f"物品: {', '.join(names)}")

        # Trigger Aggro Attack if any
        if aggro_triggered:
            # Check individual aggro chances
            for e in curr_room.enemies:
                if e.is_aggressive:
                    # Calculate chance based on XP (difficulty)
                    # Low XP (<20) -> 30%
                    # Med XP (<50) -> 50%
                    # High XP (>=50) -> 100%
                    chance = 0.3
                    if e.xp_reward >= 50: chance = 1.0
                    elif e.xp_reward >= 20: chance = 0.5
                    
                    if random.random() < chance:
                        self.log(f"[bold red]原本平靜的 {e.name} 突然認出了你！發動攻擊！[/]")
                        self.handle_enemy_turn(e, curr_room)
                    else:
                        self.log(f"[dim]{e.name} 似乎還記得你，但猶豫了一下沒有攻擊。[/]")
            
        # Calculate Exits - Grid Based
        exits = []
        if self.world.get_room(self.player.x, self.player.y + 1): exits.append("N")
        if self.world.get_room(self.player.x, self.player.y - 1): exits.append("S")
        if self.world.get_room(self.player.x + 1, self.player.y): exits.append("E")
        if self.world.get_room(self.player.x - 1, self.player.y): exits.append("W")
        
        exits_str = ", ".join(exits)
        self.log(f"出口: [cyan]{exits_str}[/]")

    # Redraw screen is no longer needed as run loop updates layout
    # keeping empty placeholder if referenced, or removing. 
    # References: process_command "look" calls redraw_screen.
    def redraw_screen(self, current_buffer=""):
        pass # Now handled by Live loop

    def check_room_aggression(self):
        """Checks if any enemy in the current room initiates combat."""
        curr_room = self.world.get_room(self.player.x, self.player.y)
        if not curr_room.enemies: return

        import random
        for enemy in curr_room.enemies:
            # If already aggressive, or rolls under aggro_chance
            if enemy.is_aggressive or random.random() < enemy.aggro_chance:
                if not enemy.is_aggressive:
                     self.log(f"[bold red]{enemy.name} 咆哮著向你發動了攻擊！[/]")
                     enemy.is_aggressive = True
                
                # Initiate Combat (Single round or just set flag? handle_combat does one round)
                # We need to make sure we don't trigger multiple attacks per turn instantly?
                # Just trigger one combat round per active enemy?
                # Or just let them be aggressive, and wait for handle_enemy_turn?
                # handle_enemy_turn is usually called by combat loop or wait.
                # Here we just want to NOTIFY player and maybe take a hit?
                # User request: "The Wolf attacks you!" implies immediate action.
                self.handle_enemy_turn(enemy, curr_room)
                # logic usually continues? If we get hit, we stop 'resting' etc.
                return True # Combat triggered
        return False

    def process_move(self, direction):
        # Sitting / Knockdown Check
        if self.player.is_sitting:
            self.log("[yellow]你坐著不能移動！請先站起來。(stand up)[/]")
            return
        if self.player.has_status('knockdown'):
            self.log("[yellow]你被擊倒在地，無法移動！請先站起來。(stand up)[/]")
            return

        # 1. Player Escape Check
        curr_room = self.world.get_room(self.player.x, self.player.y)
        if any(e.is_aggressive for e in curr_room.enemies):
            import random
            if random.random() < 0.3:
                self.log(f"[red]你試圖逃跑，但是敵人擋住了你的去路！(Escape Failed)[/]")
                # Optional: Free hit checks?
                self.update_time(1) # Penalize time
                self.check_room_aggression() # Provoke attacks
                return

        dx, dy = 0, 0
        if direction in ['n', 'north']: dy = 1
        elif direction in ['s', 'south']: dy = -1
        elif direction in ['e', 'east']: dx = 1
        elif direction in ['w', 'west']: dx = -1
        else: return # Unknown direction
        
        target_x = self.player.x + dx
        target_y = self.player.y + dy
        
        target_room = self.world.get_room(target_x, target_y)
        
        if target_room:
            self.player.move(dx, dy)
            self.player.visited.add((self.player.x, self.player.y))
            # Auto-Save on room change (Already in run loop but good to have)
            # Time Pass
            self.update_time(5) 
            self.describe_room()
            
            # 2. Check Aggression on Entry
            self.check_room_aggression()
        else:
            self.log("[red]那個方向沒有路。[/]")

    def get_item_and_index(self, collection, keyword):
        """
        Returns (item, index_in_collection) or (None, -1).
        Supports keyword matching or index (1-based).
        """
        keyword = keyword.strip()
        
        # 1. Index
        if keyword.isdigit():
            idx = int(keyword) - 1
            if 0 <= idx < len(collection):
                return collection[idx], idx
            return None, -1

        # 2. Keyword with Rarity Priority
        candidates = []
        for i, item in enumerate(collection):
            # Check keyword match
            if keyword.lower() in item.name.lower() or (item.keyword and keyword.lower() in item.keyword.lower()):
                 candidates.append((item, i))
        
        if candidates:
            # Sort by Rarity: Rare > Fine > Common
            rarity_score = {"Rare": 3, "Fine": 2, "Common": 1}
            # key: rarity score (desc), then index (asc) to keep order stable
            candidates.sort(key=lambda x: (rarity_score.get(getattr(x[0], 'rarity', 'Common'), 1) * -1, x[1]))
            
            return candidates[0] # Return best match

        return None, -1

    def handle_help(self):
        page_size = int(self.loader.settings.get('help_page_size', 10))
        sorted_help = sorted(self.help_data, key=lambda x: x['command'])
        total_items = len(sorted_help)
        total_pages = (total_items + page_size - 1) // page_size
        
        for page in range(total_pages):
            self.log("[bold yellow]=== 遊戲指令說明 ===[/]")
            self.log(f"{'指令':<15} {'別名':<10} {'說明'} (頁數: {page+1}/{total_pages})")
            self.log("-" * 60)
            
            start_idx = page * page_size
            end_idx = min(start_idx + page_size, total_items)
            
            for i in range(start_idx, end_idx):
                item = sorted_help[i]
                cmd = item['command']
                aliases = ",".join(item['aliases'])
                desc = item['description']
                usage = item['usage']
                
                self.log(f"[bold cyan]{cmd:<15}[/] {aliases:<10} {desc}")
                # if usage:
                #      self.log(f"  [dim]用法: {usage}[/]")
            
            self.log("-" * 60)
            
            if page < total_pages - 1:
                self.log(f"顯示第 {page+1}/{total_pages} 頁. 按任意鍵繼續...")
                # Force refresh to show the prompt because we are blocking the main loop
                self.update_layout(self.layout, "", 0)
                self.live_context.refresh()
                
                # Wait for key press
                msvcrt.getch()

    def process_command(self, cmd_str):
        if not cmd_str: return
        
        # Multi-command support: "3 sp rabbit"
        parts = cmd_str.split(' ', 1)
        if parts[0].isdigit():
            count = int(parts[0])
            if count > 0 and len(parts) > 1:
                real_cmd = parts[1]
                self.log(f"[bold cyan]執行 {count} 次指令: {real_cmd}[/]")
                for _ in range(count):
                    self.process_command(real_cmd)
                    if not self.running: break
                return # Stop processing this wrapper command
        
        # Debug Log
        # self.log(f"[dim]Debug: Raw cmd='{cmd_str}'[/]")
        
        cmd = cmd_str.strip().lower()

        # Check aliases
        # Allow input like "p a rabbit" -> alias "p a" -> "skill power" -> rest "rabbit"
        # Or simple first word alias? "exa" -> "examine"
        # The aliases in CSV are full phrases like "p a". 
        # But user input might be "p a rabbit".
        # We should check if the command STARTS with an alias.
        # Longest match first.
        
        target_cmd = cmd
        
        # Simple Movement Commands
        if target_cmd in ['n', 's', 'e', 'w', 'north', 'south', 'east', 'west']:
            if self.player.is_sitting:
                self.log("[yellow]你坐著不能移動！請先站起來。(stand up)[/]")
                return
            self.process_move(target_cmd)
            return

        if not cmd:
            return

        # 1. Check if it is a valid full command directly
        if cmd in self.commands:
             self.process_move(cmd) # Check move (n, s, e, w) - Fallback logic handles this but good to have
             # Actually, just bypass alias expansion
             target_cmd = cmd
        else:
             # Sort aliases by length (descending) to match longest alias first
             sorted_aliases = sorted(self.aliases.keys(), key=len, reverse=True)
             target_cmd = cmd # Default
            
             for alias in sorted_aliases:
                 if cmd == alias or cmd.startswith(alias + " "):
                     # Replace alias with full command
                     replacement = self.aliases[alias]
                     # Keep arguments
                     args = cmd[len(alias):]
                     target_cmd = replacement + args
                     break

        cmd = target_cmd.strip()
        
        if cmd in ['q', 'quit', 'exit']:
            self.running = False
            self.log("再見！")
            return

        if cmd in ['h', 'help', '?']:
            self.handle_help()
            return
            
        if cmd.startswith('scan'): # scan or scan n
            args = cmd.split(' ', 1)
            direction = 'all'
            if len(args) > 1:
                target = args[1].lower().strip()
                if target in ['n', 's', 'e', 'w', 'north', 'south', 'east', 'west']:
                    direction = target[0]
                    self.handle_sneak_scout(direction)
                    return
                else:
                    # Not a direction! Treat as inspection if sneaking
                    if self.player.is_sneaking:
                        self.handle_inspect_enemy(target)
                        return
                    else:
                        # Basic scan logic (directional) or hint
                        self.log("你可以用 'sn', 'ss', 'se', 'sw' 來潛行偵查。")
                        return
            else:
                # Bare 'scan'
                if self.player.is_sneaking:
                    self.handle_scan_equipment()
                    return
                else:
                    self.log("你需要處於潛行狀態才能仔細偵查敵人的裝備。")
                    return
            return

        # Scan/Sneak Scouting Shortcuts
        if cmd in ['sn', 'scan north']: self.handle_sneak_scout('n'); return
        if cmd in ['ss', 'scan south']: self.handle_sneak_scout('s'); return
        if cmd in ['se', 'scan east']: self.handle_sneak_scout('e'); return
        if cmd in ['sw', 'scan west']: self.handle_sneak_scout('w'); return
            
        # Handle manual move commands as fallback
        if cmd in ['n', 'north', 's', 'south', 'e', 'east', 'w', 'west']:
            # Map full words to simple chars
            d_map = {'north':'n', 'south':'s', 'east':'e', 'west':'w'}
            d = d_map.get(cmd, cmd)
            self.process_move(d)
            return

        # Look Command
        if cmd in ['l', 'look']:
            self.describe_room()
            return

        # Drink Command
        if cmd.startswith('drink ') or cmd.startswith('quaff '):
            target_name = cmd.split(' ', 1)[1]
            self.handle_drink(target_name)
            return

        # Skill Command
        if cmd.startswith('train'):
             self.handle_train(cmd.split(' ', 1)[1] if ' ' in cmd else "")
             return


        # Combat Commands
        if cmd.startswith('k ') or cmd.startswith('kill '):
            if self.player.is_sitting:
                self.log("[yellow]你坐著不能戰鬥！請先站起來。(stand up)[/]")
                return
            target_name = cmd.split(' ', 1)[1]
            self.handle_combat(target_name)
            return

        # Shop / Inventory Commands
        elif cmd.startswith('get ') or cmd.startswith('take '):
            self.handle_get_item(cmd.split(' ', 1)[1])
            return
        elif cmd.startswith('shop '):
            self.handle_shop(cmd.split(' ', 1)[1])
            return
        elif cmd == 'shop':
            self.handle_shop("list")
            return
        elif cmd.startswith('repair ') or cmd.startswith('rep '):
            self.handle_repair(cmd.split(' ', 1)[1])
            return
        elif cmd == 'inv' or cmd == 'inventory' or cmd == 'i':
            self.show_inventory()
            return
            
        # RPG Commands
        elif cmd.startswith('train '):
            self.handle_train(cmd.split(' ', 1)[1])
            return
        elif cmd.startswith('cast '):
            skill_arg = cmd.split(' ', 1)[1]
            # Relax sit for heal/ch
            if self.player.is_sitting and not any(h in skill_arg.lower() for h in ['heal', 'ch']):
                self.log("[yellow]你坐著不能施展戰鬥法術！請先站起來。(stand up)[/]")
                return
            self.handle_skill(skill_arg, is_spell=True)
            return
        elif cmd == 'skill' or cmd.startswith('skill '):
            # Sit allowed for skills
            args = ""
            if len(cmd) > 6:
                args = cmd[6:]
            self.handle_skill(args, is_spell=False)
            return

        if cmd.startswith('drop '):
            item_keyword = cmd.split(' ', 1)[1]
            self.handle_drop_item(item_keyword)
            return

        # Save / Load Commands
        if cmd.startswith('save '):
            slot = cmd.split(' ', 1)[1]
            if slot in ['1', '2', '3']:
                self.save_manager.save_game(slot)
            else:
                self.log("[red]請輸入 save 1, save 2 或 save 3。[/]")
            return

        if cmd.startswith('load '):
            slot = cmd.split(' ', 1)[1]
            if slot in ['1', '2', '3']:
                # Confirm?
                self.log(f"[yellow]確定要讀取進度 {slot} 嗎? 未儲存的進度將會遺失。 (y/n)[/]")
                # Simple confirmation logic could be added here, but for now direct load
                if self.save_manager.load_game(slot):
                     self.log(f"[green]讀取成功! (Slot {slot})[/]")
            else:
                self.log("[red]請輸入 load 1, load 2 或 load 3。[/]")
            return

        # Shop Shortcuts
        if cmd in ['list', 'li']:
            self.handle_shop("list")
            return
        
        if cmd.startswith('buy '):
            self.handle_shop(cmd)
            return
        
        if cmd.startswith('sell '):
            self.handle_shop(cmd)
            return

        # Equipment Commands
        if cmd in ['eq', 'equipment']:
            self.show_equipment()
            return

        if cmd.startswith('wear ') or cmd.startswith('equip '):
            item_keyword = cmd.split(' ', 1)[1]
            self.handle_wear_item(item_keyword)
            return

        if cmd.startswith('remove '):
            item_keyword = cmd.split(' ', 1)[1]
            self.handle_remove_item(item_keyword)
            return

        # Consumable Commands
        if cmd.startswith('eat '):
            item_keyword = cmd.split(' ', 1)[1]
            self.handle_eat(item_keyword)
            return

        # Scroll Commands
        if cmd.startswith('read '):
            item_keyword = cmd.split(' ', 1)[1]
            self.handle_read(item_keyword)
            return

        # Resting Commands
        if cmd in ['sit down', 'sit d', 'sit']:
            self.handle_sit()
            return

        if cmd in ['stand up', 'sta u', 'stand']:
            self.handle_stand()
            return

        if cmd in ['sneak', 'sne']:
            self.handle_sneak()
            return
        if cmd.startswith('sne ') or cmd.startswith('sneak '):
            target_name = cmd.split(' ', 1)[1]
            self.handle_inspect_enemy(target_name)
            return

        if cmd in ['wait', 'rest']:
            self.handle_wait()
            return

        # Placeholder for future interactions
        
        # Debug Command: aliases
        if cmd == 'aliases':
             self.log(f"Aliases: {list(self.aliases.keys())}")
             return

        self.log(f"未知指令 '{cmd}'。")

    def handle_combat(self, target_name):
        curr_room = self.world.get_room(self.player.x, self.player.y)
        target = None
        
        # Simple name matching (case insensitive partial match)
        for enemy in curr_room.enemies:
            if target_name.lower() in enemy.name.lower():
                target = enemy
                break
        
        if not target:
            self.log(f"你在這裡沒看到 '{target_name}'。")
            return

        # Debug
        # self.log(f"[dim]Debug: Combat with '{target.name}'[/]")

    def handle_sneak_scout(self, direction='all'):
        """Directional scout that triggers stealth mode if successful (潛行偵查)"""
        import random
        curr_room = self.world.get_room(self.player.x, self.player.y)
        
        # Base scout score: (DEX + LUK) * 2
        dex = self.player.get_stat('dex')
        luk = self.player.get_stat('luk')
        score = (dex + luk) * 2
        
        # Small boost to score if already sneaking
        score += 20 if self.player.is_sneaking else 0
        
        self.log(f"[italic]你壓低身姿，警覺地向{direction.upper()}方觀察... (偵查值: {score})[/]")
        
        # Directions to check
        directions = []
        d_map = {'n':(0,1), 's':(0,-1), 'e':(1,0), 'w':(-1,0)}
        if direction == 'all':
             directions = [('n', 0, 1), ('s', 0, -1), ('e', 1, 0), ('w', -1, 0)]
        elif direction in d_map:
             directions = [(direction, *d_map[direction])]
        else:
             self.log(f"[red]無效的方向 '{direction}'。[/]")
             return
        
        found_any = False
        success_count = 0
        for d_name, dx, dy in directions:
             nx, ny = self.player.x + dx, self.player.y + dy
             room = self.world.get_room(nx, ny)
             if room:
                 if not room.enemies:
                     self.log(f"[{d_name.upper()}]: {room.name} - [green]安全[/]")
                     success_count += 1
                     continue
                 
                 # Level difference penalty
                 avg_lv = sum(e.level for e in room.enemies) / len(room.enemies)
                 difficulty = 35 + int(avg_lv * 4)
                 
                 roll = random.randint(1, 100) + score
                 if roll >= difficulty:
                     success_count += 1
                     found_any = True
                     from collections import Counter
                     name_counts = Counter(e.name for e in room.enemies)
                     type_str = ', '.join(f"{name} x{cnt}" if cnt > 1 else name 
                                          for name, cnt in name_counts.items())
                     self.log(f"[{d_name.upper()}]: {room.name} - 發現敵人: {type_str}")
                 else:
                     self.log(f"[{d_name.upper()}]: 你看不清那邊的情況。")
                     # If not already sneaking, there's a small chance to get noticed if very unlucky?
                     # Let's keep it safe for now as per user requested "belongs to sneak"
        
        # If successfully scouted at least one direction OR room was safe
        if success_count > 0:
             self.player.is_sneaking = True
             self.log("[bold green]你成功進入了潛行狀態。[/]")
        else:
             self.player.is_sneaking = False
             self.log("[yellow]偵查失敗，你暴露了自己的位置。[/]")

    def handle_scan_equipment(self):
        """Detailed in-room equipment inspection (需處於潛行狀態)"""
        if not self.player.is_sneaking:
            self.log("[yellow]你需要先進入潛行狀態 (使用 sn/ss/se/sw 偵查敵情) 才能進行裝備偵查。[/]")
            return

        import random
        curr_room = self.world.get_room(self.player.x, self.player.y)
        if not curr_room.enemies:
            self.log("這裡沒有敵人可以偵查。")
            return

        dex = self.player.get_stat('dex')
        luk = self.player.get_stat('luk')
        score = (dex + luk) * 2
        
        self.log(f"[italic]你隱藏在陰影中，仔細觀察房間內的敵人... (偵查值: {score})[/]")
        
        for e in curr_room.enemies:
            # Difficulty based on enemy level
            difficulty = 40 + (e.level * 5)
            roll = random.randint(1, 100) + score
            
            if roll >= difficulty:
                equip_list = []
                for slot, item in e.equipment.items():
                    if item:
                        # Durability check
                        dur_str = ""
                        if hasattr(item, 'max_durability') and item.max_durability > 0:
                            pct = int((item.current_durability / item.max_durability) * 100)
                            dur_str = f" [({pct}%)]"
                        equip_list.append(f"{item.get_display_name()}{dur_str}")
                
                status_list = []
                for s_name, turns in e.debuffs.items():
                    status_list.append(f"[bold yellow]{s_name}[/]({turns}t)")
                
                info = f"[bold cyan]{e.name}[/]:"
                if equip_list:
                    info += f" 裝備 [{', '.join(equip_list)}]"
                else:
                    info += " 無裝備"
                
                if status_list:
                    info += f" | 狀態 [{', '.join(status_list)}]"
                
                self.log(info)
            else:
                self.log(f"你看不清 [cyan]{e.name}[/] 的具體裝備。")
         
        if not found_any and direction == 'all':
             self.log("你什麼也沒發現。")

    def get_damage_description(self, damage, is_crit=False):
        if damage <= 0: return "完全沒有造成傷害 (Miss)"
        if damage < 5: return "輕微地擦傷了 (Grazed)"
        if damage < 10: return "擊中了 (Hit)"
        if damage < 20: return "重重地擊中了 (Hard Hit)"
        if damage < 40: return "造成了毀滅性的一擊 (Smashed)"
        return "將目標打成了碎片! (Obliterated)"



    def calculate_player_damage(self):
        # Calculate Base Damage using Player Stats (including bonuses)
        str_val = self.player.get_stat('str')
        
        min_base = self.balance.get('combat', 'player_min_dmg_base', 2)
        max_base = self.balance.get('combat', 'player_max_dmg_base', 5)
        dmg_per_str = self.balance.get('combat', 'player_dmg_per_str', 0.5)
        
        min_d = min_base + int(str_val * dmg_per_str)
        max_d = max_base + int(str_val * dmg_per_str)
        
        # Check Right Hand Weapon
        r_hand = self.player.equipment.get('r_hand')
        if r_hand and hasattr(r_hand, 'min_dmg'):
            min_d += r_hand.min_dmg
            max_d += r_hand.max_dmg

        # Check Left Hand Weapon
        l_hand = self.player.equipment.get('l_hand')
        if l_hand and hasattr(l_hand, 'min_dmg'):
            min_d += l_hand.min_dmg
            max_d += l_hand.max_dmg
        
        return random.randint(min_d, max_d)

    def alert_group(self, target):
        """Alerts other enemies of the same type in the room."""
        curr_room = self.world.get_room(self.player.x, self.player.y)
        if not curr_room: return
        
        for enemy in curr_room.enemies:
            if enemy != target and enemy.proto_id == target.proto_id and not enemy.is_aggressive:
                enemy.is_aggressive = True
                self.log(f"[bold red]原本平靜的 {enemy.name} 看到了同伴被攻擊，憤怒地加入了戰鬥！[/]")

    def perform_attack(self, target, damage_in, flavor_text="攻擊了", color=None):
        if not target.is_alive(): return
        
        # Group Aggro
        self.alert_group(target)
        
        # Accuracy Check
        base_hit = self.balance.get('combat', 'base_hit_chance', 100)
        hit_chance = base_hit
        
        # Player attacking Enemy
        weapon = self.player.equipment.get('r_hand')
        if weapon and hasattr(weapon, 'accuracy'):
            hit_chance = weapon.accuracy
            
        # Stat Modifiers
        hit_per_dex = self.balance.get('combat', 'player_hit_per_dex', 0.5)
        hit_chance += (self.player.get_stat('dex') * hit_per_dex)
        
        # Target Avoidance
        evade_base = self.balance.get('combat', 'enemy_evade_base', 10)
        evade_per_dmg = self.balance.get('combat', 'enemy_evade_per_dmg', 0.5)
        evade_mult = self.balance.get('combat', 'evade_multiplier', 0.5)
        
        target_agi = evade_base + (target.damage_range[1] * evade_per_dmg) # Estimate
        hit_chance -= (target_agi * evade_mult)
        
        # Roll
        roll = random.randint(1, 100)
        if roll > hit_chance:
            self.log(f"[yellow]你攻擊 {target.name}，但是[bold red]失手了[/]! (Roll: {roll} > Chance: {int(hit_chance)})[/]")
            return

        damage = damage_in
        
        # Apply Damage Mitigation (Defense)
        defense = 0
        if hasattr(target, 'get_defense'):
            defense = target.get_defense()
            
        actual_damage = max(1, damage - defense)
        target.take_damage(actual_damage)
        
        # Colorize damage
        dmg_color = "[red]" if actual_damage > 10 else "[white]"
        
        prefix_color = f"[{color}]" if color else ""
        prefix_end = "[/]" if color else ""
        
        self.log(f"{prefix_color}{flavor_text}{prefix_end} [bold]{target.name}[/] 造成了 {dmg_color}{actual_damage}[/] 點傷害。")
        
        # Weapon Durability Loss (Player Attacking)
        weapon = self.player.equipment.get('r_hand')
        if weapon and hasattr(weapon, 'max_durability') and weapon.max_durability > 0:
             # Chance: 10% + 5% per level diff
             chance = 0.1
             if target.level > self.player.level:
                 chance += (target.level - self.player.level) * 0.05
             
             if random.random() < chance:
                 weapon.current_durability -= 1
                 if weapon.current_durability <= 0:
                     self.log(f"[bold red]你的 {weapon.name} 損壞了![/]")
                     del self.player.equipment['r_hand']
                     self.player.recalculate_stats()
                 # Warn at 10%
                 elif weapon.current_durability <= weapon.max_durability * 0.1:
                      self.log(f"[bold red]你的 {weapon.name} 快要壞了! ({weapon.current_durability}/{weapon.max_durability})[/]")
        


    def check_skill_success(self, skill_name):
        prob = self.player.skills.get(skill_name, 0)
        # Base failure chance decreases as proficiency increases
        # Initial: 0 prof -> 30% success? Or always succeed but effect varies?
        # User said: "proficiency 0-100".
        # Let's say base success is 40% + (prof * 0.6). Max 100%.
        chance = 40 + (prob * 0.6)
        
        import random
        if random.randint(1, 100) <= chance:
            # Success! Improve proficiency
            if prob < 100:
                self.player.skills[skill_name] = prob + 1
            return True
        return False

    def handle_skill(self, args_str, is_spell=False):
        if not args_str:
            # Display Skill List
            self.log("[bold yellow]--- 角色技能 (Skills) ---[/]")
            
            # 1. Spells / Level Based
            spells = []
            
            # Use loaded skills data
            if hasattr(self, 'skills_data'):
                # Sort by level then name
                sorted_skills = sorted(self.skills_data.values(), key=lambda x: (x.get('req_lv', 1), x.get('name')))
                
                for sk in sorted_skills:
                    if sk.get('type') == 'enemy': continue # Don't show enemy skills
                    
                    name = sk.get('name')
                    sid = [k for k,v in self.skills_data.items() if v == sk][0]
                    req_lv = sk.get('req_lv', 1)
                    cost_val, c_type = self.get_skill_cost(sid)
                    cost_str = f"{cost_val} {c_type.upper()}"
                    
                    if self.player.level >= req_lv:
                         spells.append(f"[green]{name}[/] ({sid}) - {cost_str}")
                    else:
                         spells.append(f"[dim]{name} - (需 Lv{req_lv})[/]")
            
            if spells:
                self.log("[bold]技能列表 (Skills):[/]")
                for s in spells: self.log(f"  {s}")
            else:
                self.log("[dim]尚未學會任何技能。[/]")

            self.log("") 
            # 2. Basic Combat Skills
            self.log("[bold]戰鬥技能 (Combat):[/]")
            self.log("  [yellow]強力攻擊 (Power, pa)[/] - 5 MV")
            self.log("  [red]狂暴攻擊 (Berserk, ba)[/] - 10 MV, Low Acc")
            
            # 3. Proficiency Skills
            self.log("")
            self.log("[bold]熟練度技能 (Proficiency):[/]")
            
            blind_prof = self.player.skills.get('blind', 0)
            kick_prof = self.player.skills.get('kick', 0)
            
            self.log(f"  [cyan]致盲 (Blind, bl)[/] - 5 MP : [white]{blind_prof}%[/] 熟練度")
            self.log(f"  [green]踢擊 (Kick, kn)[/]   - 5 MV : [white]{kick_prof}%[/] 熟練度")
            
            self.log("")
            self.log("使用方式: [bold]skill <name> <target>[/] 或簡寫 (例如 [bold]bl bat[/])")
            return

        # Sanitize input (replace NBSP and tabs)
        # Use regex to split by ANY whitespace including unicode spaces
        import re
        parts = re.split(r'\s+', args_str.strip(), 1)
        skill_key = parts[0].lower()
        target_name = parts[1] if len(parts) > 1 else None
        
        curr_room = self.world.get_room(self.player.x, self.player.y)
        target = None
        
        # Special Case: Heal (Self)
        if skill_key == 'heal':
            cost, c_type = self.get_skill_cost('heal')
            if self.player.level < 3:
                self.log("[red]你還沒學會 Heal (需要 Lv3)。[/]")
                return
            if getattr(self.player, c_type, 0) < cost:
                self.log(f"[red]{c_type.upper()}不足! (需要 {cost} {c_type.upper()})[/]")
                return
            if c_type == 'mp': self.player.mp -= cost
            elif c_type == 'mv': self.player.mv -= cost
            
            self.player.hp = min(self.player.max_hp, self.player.hp + 30)
            self.log(f"[green]你施放了治療術! 生命回復了 30 點。 (消耗 {cost} {c_type.upper()})[/]")
            return

        # Target Selection for Offensive Skills
        if target_name:
             for enemy in curr_room.enemies:
                if target_name.lower() in enemy.name.lower():
                    target = enemy
                    break
             if not target:
                 self.log(f"這裡沒看到 '{target_name}'。")
                 return
        else:
             if curr_room.enemies:
                 target = curr_room.enemies[0]
             else:
                 self.log("這裡沒有目標。")
                 return

        # Offensive Skills Logic
        p = self.player
        damage = 0
        
        if skill_key == "power":
            # Redundant check removed, handled by generic block below
            pass
            
        # Check Skill Data (Validation Layer)
        if hasattr(self, 'skills_data') and skill_key in self.skills_data:
            sk_data = self.skills_data[skill_key]
            # print(f"DEBUG: Found skill data for {skill_key}")
            
            # 1. Level Check
            if p.level < sk_data.get('req_lv', 1):
                 self.log(f"[red]你還沒學會 {sk_data['name']} (需要 Lv{sk_data['req_lv']})。[/]")
                 return

            # 2. Cost Check (Scaled)
            cost, ctype = self.get_skill_cost(skill_key)
            
            if ctype != 'none':
                if getattr(p, ctype, 0) < cost:
                    self.log(f"[red]{ctype.upper()}不足! 需要 {cost} {ctype.upper()}。[/]")
                    return
                # Deduct
                if ctype == 'mv': p.mv -= cost
                elif ctype == 'mp': p.mp -= cost
                elif ctype == 'hp': p.hp -= cost
                
        # Calculate Base Damage once for use in formulas
        # This includes Weapon Damage!
        base_dmg = self.calculate_player_damage()
        
        # Evaluate Damage Formula from CSV
        if hasattr(self, 'skills_data') and skill_key in self.skills_data:
             sk_data = self.skills_data[skill_key]
             formula = sk_data.get('dmg_formula', '0')
             
             # Safe Eval
             try:
                 # Context variables for eval
                 # base: weapon damage + str bonus (normal attack)
                 # int: player int stat
                 # str: player str stat
                 # level: player level
                 
                 # Prepare safe local namespace
                 local_ns = {
                     'base': base_dmg, 
                     'int': p.get_stat('int'),
                     'str': p.get_stat('str'),
                     'dex': p.get_stat('dex'),
                     'level': p.level
                 }
                 
                 damage = int(eval(str(formula), {"__builtins__": {}}, local_ns))
             except Exception as e:
                 self.log(f"[red]技能傷害計算錯誤: {e}[/]")
                 damage = 0
                 
             if damage > 0:
                 # Output Flavor Text based on Skill
                 # We can store flavor text in CSV too, but for now map it or use generic
                 if skill_key == 'power':
                      self.log(f"你使出 [bold cyan]強力攻擊[/]!")
                 elif skill_key == 'berserk':
                      self.log(f"你進入 [bold red]狂暴狀態[/] 瘋狂攻擊!")
                 elif skill_key == 'double':
                      self.log(f"你使出 [bold yellow]雙重打擊[/]!")

        # Fallback / Overrides for Specific Complex Logic (like Multi-hit or AOE)
        # But for simple damage skills (power, berserk), the above eval covers it.
        # We need to skip the old if/elif blocks for these if handled above.
        
        # ... checking if specific extra logic is needed ...
        
        if skill_key == "fireball":
            # Checks handled by validation
            # damage calculated by formula above (20+int*2)
            self.log(f"你詠唱咒語，發射出一顆 [bold red]火球[/]!")
            

        elif skill_key == "firestorm":
            # Checks handled by validation
            self.log(f"你詠唱古老的咒語，召喚出 [bold red]烈焰風暴[/]! (AOE)")
            
            # AOE Logic
            enemies_to_hit = list(curr_room.enemies) # Copy list
            if not enemies_to_hit:
                self.log("但是周圍沒有敵人。")
                return

            total_hits = 0
            for enemy in enemies_to_hit:
                if enemy.is_alive():
                    # AOE Damage 
                    base_dmg = random.randint(int(15 + p.int), int(30 + p.int * 1.5))
                    self.perform_attack(enemy, base_dmg, "烈焰吞噬了", color="red")
                    
                    if enemy.is_alive():
                        # Manually trigger return fire if alive
                        self.handle_enemy_turn(enemy, curr_room)
                    else:
                        self.resolve_turn(enemy, curr_room)
                        
            return

        elif skill_key == 'ultimate' or skill_key == 'armageddon':
            # Checks handled by validation
            damage = 500 + p.int * 5
            self.log(f"[bold magenta]末日審判降臨! 毀滅性的能量吞噬了 {target.name}![/]")
            self.perform_attack(target, damage, "完全毀滅了") 
            self.resolve_turn(target, curr_room)
            return

        elif skill_key == "blind" or skill_key == "bl":
            if not target:
                self.log("你需要指定目標 (blind <target>)。")
                return
            
            # Cost Check
            cost, ctype = self.get_skill_cost('blind')
            if getattr(p, ctype, 0) < cost:
                self.log(f"[red]{ctype.upper()}不足! (需要 {cost} {ctype.upper()})[/]")
                return
            if ctype == 'mp': p.mp -= cost
            elif ctype == 'mv': p.mv -= cost
            
            if self.check_skill_success('blind'):
                target.debuffs['blind'] = 3 # 3 Turns
                self.log(f"你不想讓敵人看見，對 {target.name} 使用了 [bold cyan]致盲 (Blind)[/]!")
                self.log(f"[bold yellow]{target.name} 被致盲了! 命中率與防禦力下降! (3回合)[/]")
                damage = 0
            else:
                 self.log(f"你試圖致盲 {target.name}，但是失敗了!")
                 return
                 
        elif skill_key == "kick" or skill_key == "kn" or skill_key == "kp":
            cost, c_type = self.get_skill_cost('kick')
            if getattr(p, c_type, 0) < cost:
                self.log(f"[red]{c_type.upper()}不足! (需要 {cost} {c_type.upper()})[/]")
                return
            if c_type == 'mp': p.mp -= cost
            elif c_type == 'mv': p.mv -= cost

            if not target:
                self.log("你需要指定目標 (kick <target>)。")
                return

            # Checks handled by validation
            
            if self.check_skill_success('kick'):
                 # Damage + Knockdown
                 base_dmg = random.randint(2 + p.str // 3, 5 + p.str // 3)
                 damage = base_dmg
                 target.debuffs['knockdown'] = 2 # 2 Turns
                 self.log(f"你飛起一腳，對 {target.name} 使用了 [bold green]踢擊 (Kick)[/]!")
                 self.log(f"[bold yellow]{target.name} 被踢倒在地! (擊倒 2回合, 下次打落成功率提升)[/]")
            else:
                 self.log(f"你試圖踢擊 {target.name}，但是滑倒了 (失敗)!")
                 return

        elif skill_key in ["power", "berserk", "double", "triple_attack"]:
             # Handled by generic formula evaluator above
             pass

        elif skill_key == "disarm" or skill_key == "da" or skill_key == "di":
            if not target:
                self.log("你需要指定目標 (disarm <target>)。")
                return
                
            # Cost Check
            cost, ctype = self.get_skill_cost('disarm')
            if getattr(p, ctype, 0) < cost:
                self.log(f"[red]{ctype.upper()}不足! (需要 {cost} {ctype.upper()})[/]")
                return
            if ctype == 'mp': p.mp -= cost
            elif ctype == 'mv': p.mv -= cost
            
            self.handle_disarm(target, curr_room)
            return # handle_disarm manages its own resolve

        elif skill_key == "sunder" or skill_key == "su" or skill_key == "sd":
            if not target:
                self.log("你需要指定目標 (sunder <target>)。")
                return

            # Cost Check
            cost, ctype = self.get_skill_cost('sunder')
            if getattr(p, ctype, 0) < cost:
                self.log(f"[red]{ctype.upper()}不足! (需要 {cost} {ctype.upper()})[/]")
                return
            if ctype == 'mp': p.mp -= cost
            elif ctype == 'mv': p.mv -= cost
            
            self.handle_sunder(target, curr_room)
            return # handle_sunder manages its own resolve

        else:
            self.log(f"未知的技能: {skill_key}")
            return

        # Apply Player Attack
        self.perform_attack(target, damage, f"你對 {target.name} 造成了")
        self.resolve_turn(target, curr_room)

    def calculate_disarm_success(self, target):
        """Calculate disarm success rate against target (計算打落成功率)"""
        p = self.player
        base_chance = 0.30  # 30% base

        # Bonus from target status effects
        if target.has_status('blind'):
            base_chance += 0.25  # +25% if blind
        if target.has_status('knockdown'):
            base_chance += 0.20  # +20% if knocked down

        # Attribute modifier: (atk DEX*0.02 + atk LUK*0.01) - (tgt estimate*0.02)
        atk_bonus = p.dex * 0.02 + p.luk * 0.01
        # Estimate target DEX/LUK from level
        tgt_dex_est = target.level * 2 if hasattr(target, 'level') else 5
        tgt_luk_est = target.level if hasattr(target, 'level') else 3
        tgt_penalty = tgt_dex_est * 0.02 + tgt_luk_est * 0.01

        final_chance = base_chance + atk_bonus - tgt_penalty
        return max(0.05, min(0.90, final_chance))  # Clamp 5% ~ 90%

    def handle_disarm(self, target, curr_room):
        """Handle disarm skill: unequip target weapon → room floor → snatch race (打落技能處理)"""
        p = self.player

        # Check if target has a weapon
        weapon = target.equipment.get('r_hand')
        if not weapon:
            self.log(f"{target.name} 沒有可以打落的武器!")
            return

        # Calculate success
        chance = self.calculate_disarm_success(target)
        roll = random.random()

        self.log(f"你嘗試打落 {target.name} 的 {weapon.name}! (成功率: {int(chance*100)}%)")

        if roll < chance:
            # Success: unequip weapon → drop to room
            del target.equipment['r_hand']
            curr_room.items.append(weapon)
            weapon.drop_time = time.time()
            self.log(f"[bold green]成功! {target.name} 的 {weapon.get_display_name()} 掉落在地![/]")

            # Trigger Snatch Logic
            self.execute_snatch_logic(target, weapon, curr_room)
        else:
            self.log(f"[bold red]打落失敗! {target.name} 緊握住了武器![/]")

        # Enemy retaliates
        self.resolve_turn(target, curr_room)

    def execute_snatch_logic(self, enemy, weapon, curr_room):
        """Snatch race: DEX/LUK weighted pick-up competition (搶奪邏輯)"""
        p = self.player

        # Calculate weights
        p_weight = p.dex * 0.7 + p.luk * 0.3
        # Estimate enemy stats from level
        e_dex = enemy.level * 2 if hasattr(enemy, 'level') else 5
        e_luk = enemy.level if hasattr(enemy, 'level') else 3
        e_weight = e_dex * 0.7 + e_luk * 0.3

        # Blind / Knockdown → weight drops to 0 (can't snatch)
        if enemy.has_status('blind') or enemy.has_status('knockdown'):
            e_weight = 0.0
        if p.has_status('blind') or p.has_status('knockdown'):
            p_weight = 0.0

        total = p_weight + e_weight
        if total <= 0:
            self.log(f"[dim]雙方都無法搶奪武器，{weapon.name} 留在地上。[/]")
            return

        p_chance = p_weight / total
        roll = random.random()

        if roll < p_chance:
            # Player wins the snatch
            if weapon in curr_room.items:
                curr_room.items.remove(weapon)
            p.inventory.append(weapon)
            self.log(f"[bold green]你搶先一步撿起了 {weapon.get_display_name()}![/]")
        else:
            # Enemy wins the snatch
            if weapon in curr_room.items:
                curr_room.items.remove(weapon)
            enemy.inventory.append(weapon)
            self.log(f"[bold red]{enemy.name} 搶先撿回了 {weapon.name}![/]")
            # Re-equip the weapon
            enemy.equipment['r_hand'] = weapon
            enemy.inventory.remove(weapon)
            self.log(f"[bold red]{enemy.name} 重新裝備了 {weapon.name}![/]")

    def handle_sunder(self, target, curr_room):
        """Handle sunder skill: deal durability damage to target equipment (破甲技能處理)"""
        p = self.player

        # Find target's equipment that can be sundered
        sunder_candidates = []
        for slot, item in target.equipment.items():
            if hasattr(item, 'current_durability') and item.current_durability > 0:
                sunder_candidates.append((slot, item))

        if not sunder_candidates:
            self.log(f"{target.name} 沒有可以破壞的裝備!")
            return

        # Pick random equipment piece
        slot, item = random.choice(sunder_candidates)

        # Deal 50% base damage
        base_dmg = self.calculate_player_damage()
        damage = max(1, base_dmg // 2)

        # Durability damage: 3~8 base + STR bonus
        dur_damage = random.randint(3, 8) + p.str // 5
        old_dur = item.current_durability
        item.current_durability = max(0, item.current_durability - dur_damage)

        slot_name_map = {'r_hand': '武器', 'l_hand': '盾牌', 'body': '護甲', 'head': '頭盔', 'legs': '護腿', 'feet': '靴子'}
        slot_cn = slot_name_map.get(slot, slot)

        self.log(f"你對 {target.name} 使用 [bold yellow]破甲 (Sunder)[/]!")
        self.log(f"你猛擊 {target.name} 的 {item.name}! 耐久度 {old_dur} → {item.current_durability}")

        if item.current_durability <= 0:
            # Equipment destroyed!
            del target.equipment[slot]
            self.log(f"[bold red]{target.name} 的 {item.name} 碎裂了! ({slot_cn}消失)[/]")
        elif item.current_durability <= item.max_durability * 0.2:
            self.log(f"[bold yellow]{target.name} 的 {item.name} 快要碎裂了! ({item.current_durability}/{item.max_durability})[/]")

        # Apply the 50% damage hit
        self.perform_attack(target, damage, f"破甲同時造成了")
        self.resolve_turn(target, curr_room)

    def handle_combat(self, target_name):
        curr_room = self.world.get_room(self.player.x, self.player.y)
        target = None
        
        for enemy in curr_room.enemies:
            if target_name.lower() in enemy.name.lower():
                target = enemy
                break
        
        if not target:
            self.log(f"你在這裡沒看到 '{target_name}'。")
            return
            
        # Basic Attack Cost check
        cost, c_type = self.get_skill_cost('basic_attack')
        if getattr(self.player, c_type, 0) < cost:
            self.log(f"[yellow]你太累了，無法發動攻擊！ (需要 {cost} {c_type.upper()})[/]")
            return

        # Deduct Cost
        if c_type == 'mp': self.player.mp -= cost
        elif c_type == 'mv': self.player.mv -= cost
        elif c_type == 'hp': self.player.hp -= cost

        # Set Aggressive Flag
        target.is_aggressive = True
        self.player.last_attack_time = time.time() # Reset timer on manual pull

        # Regular Attack
        # Calculate Damage
        p_dmg = self.calculate_player_damage() 
        
        self.log(f"你揮舞武器攻向 {target.name}!")
        self.perform_attack(target, p_dmg, f"造成了")

        # Resolve Turn
        self.resolve_turn(target, curr_room)

    def resolve_turn(self, target, curr_room):
        if not target.is_alive():
            self.log(f"[red]{target.name}[/] 慘叫一聲倒下了! (Died)")
            self.log(f"你獲得 [magenta]{target.xp_reward}[/] 經驗值 和 [yellow]{target.gold_reward}[/] 金幣!")
            # Gain XP logic including level up
            leveled_up = self.player.gain_xp(target.xp_reward)
            if leveled_up:
                self.log(f"[bold green]恭喜! 你升到了 {self.player.level} 級![/]")

            self.player.gold += target.gold_reward
            

            
            # Global Drop: Travel Scroll (1%)
            if random.random() < 0.01:
                scroll_proto = self.loader.items.get('item_scroll_town')
                if scroll_proto:
                    scroll = LootGenerator.generate(scroll_proto)
                    curr_room.items.append(scroll)
                    self.log(f"[bold cyan]奇蹟般地，敵人掉落了一個 {scroll.get_display_name()}![/]")

            # Epic Drop (Elite/Mutated only)
            is_boss = target.proto_id and target.proto_id.startswith('boss_')
            is_mutated = target.id and "mutated" in target.id
            is_elite = target.max_hp >= 300 or is_mutated
            
            if is_elite or is_boss: # Bosses also drop Epics
                # Chance: 20% for Elite, 100% for Boss? Or just 20% for now.
                # User asked for: Shops, Elite, Mutated drop Epics.
                drop_chance = 0.2
                if is_boss: drop_chance = 1.0 # Bosses always drop Epic?
                
                if random.random() < drop_chance:
                    # Pick random equipment
                    equip_protos = [i for i in self.loader.items.values() if isinstance(i, (Weapon, Armor))]
                    if equip_protos:
                        proto = random.choice(equip_protos)
                        epic_item = LootGenerator.generate(proto, force_rarity="Epic")
                        epic_item.drop_time = time.time()
                        curr_room.items.append(epic_item)
                        self.log(f"[bold magenta]光芒四射！{target.name} 掉落了史詩裝備: {epic_item.get_display_name()}![/]")

            # Loot
            for item, chance, rarity in target.loot_table:
                if random.random() < chance:
                    # Generate fresh loot with rarity
                    new_loot = LootGenerator.generate(item, force_rarity=rarity)
                    new_loot.drop_time = time.time() # Set drop time for loot
                    curr_room.items.append(new_loot)
                    self.log(f"掉落了 {new_loot.get_display_name()}!")

            # Remove enemy and Add to Respawn Queue
            curr_room.enemies.remove(target)
            if target.proto_id:
                # Respawn based on enemy data
                respawn_delay = getattr(target, 'respawn_time', 30.0)
                respawn_time = time.time() + float(respawn_delay)
                curr_room.respawn_queue.append((target.proto_id, respawn_time))
                self.log(f"[dim]提示: {target.name} 將在 {int(respawn_delay)} 秒後重生。[/]")
        else:
            # Tick enemy debuffs each combat round (敵人 debuff 每回合遞減)
            expired = target.tick_debuffs()
            for eff in expired:
                if eff == 'blind':
                    self.log(f"[dim]{target.name} 的致盲效果消退了。[/]")
                elif eff == 'knockdown':
                    self.log(f"[dim]{target.name} 從地上站了起來。[/]")
                elif eff == 'def_down':
                    self.log(f"[dim]{target.name} 的防禦下降效果消退了。[/]")
            
            self.handle_enemy_turn(target, curr_room)

    def handle_death(self):
        self.log("[red]你眼前一黑...[/]")
        self.log("[yellow]一陣溫暖的光芒包圍了你。你死而復生了！[/]")
        
        # Max HP
        self.player.hp = self.player.max_hp
        self.player.is_sitting = False # Force stand up
        
        # XP Penalty
        penalty = int(self.player.xp * 0.05)
        if penalty > 0:
            self.player.xp = max(0, self.player.xp - penalty)
            self.log(f"[red]因為死亡的代價，你失去了 {penalty} 點經驗值。[/]")
        else:
             self.log(f"[dim]幸運的是，你沒有足夠的經驗值可以失去。[/]")

        # Safe Room Relocation
        safe_room = self._find_safe_room()
        if safe_room:
            self.player.x = safe_room.x
            self.player.y = safe_room.y
            self.log(f"[cyan]靈魂飄蕩，你在一個安全的角落 ({safe_room.name}) 甦醒了。[/]")
        else:
            # Fallback to Village (0,0) if no safe neighbors
            self.player.x = 0
            self.player.y = 0
            self.log(f"[cyan]靈魂飄蕩，你在村莊甦醒了。[/]")
            
        self.player.visited.add((self.player.x, self.player.y))
        self.describe_room()

    def _find_safe_room(self):
        # Check current room first? No, if we died there it's bad.
        # Check neighbors: N, S, E, W
        cx, cy = self.player.x, self.player.y
        offsets = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        candidates = []
        for dx, dy in offsets:
            nx, ny = cx + dx, cy + dy
            room = self.world.get_room(nx, ny)
            if room:
                # Check for enemies
                # Safe if NO enemies or enemies are not aggressive? 
                # User said "no enemies".
                if not room.enemies:
                    candidates.append(room)
        
        import random
        if candidates:
            return random.choice(candidates)
        return None

    def handle_read(self, keyword):
        # Find item
        scroll = None
        target_kw = keyword.lower()
        
        for item in self.player.inventory:
            # Check if item is a scroll based on updated keywords or name
            # Note: We avoid checking item.id directly as it might not exist on all item instances
            if "scroll" in item.keyword.lower() or "town" in item.keyword.lower() or "卷軸" in item.name:
                # Check if this specific item matches the player's input
                if target_kw in item.keyword.lower() or target_kw in item.name.lower() or target_kw == 'tow':
                     scroll = item
                     break
        
        if not scroll:
            self.log(f"你身上沒有 '{keyword}' 或是那不是可以閱讀的卷軸。")
            return

        self.player.inventory.remove(scroll)
        self.log(f"你打開 {scroll.get_display_name()} 朗誦咒文...")
        
        # Town Scroll
        if "town" in scroll.keyword.lower() or "town" in scroll.name.lower() or "回城" in scroll.name:
            self.log("[cyan]光芒閃爍，空間扭曲了！(Teleport)[/]")
            self.player.x = 0
            self.player.y = 0
            self.player.visited.add((0, 0))
            self.update_time(0) 
            self.describe_room()
            
        # Stat Reset Scroll
        elif "reset" in scroll.keyword.lower() or "reset" in scroll.name.lower() or "重置" in scroll.name:
            self.log("[bold magenta]一股神秘的力量洗滌了你的靈魂... 屬性重置了！[/]")
            # Calculate Total Points based on Level
            # Initial (Lv1): 10 each = 50 total? No, base is 10.
            # Points gained per level: 2 * (Level - 1)
            total_points = (self.player.level - 1) * 2
            
            # Reset Stats to Base 10
            self.player.str = 10
            self.player.dex = 10
            self.player.con = 10
            self.player.int = 10
            self.player.luk = 10
            
            # Refund Points
            self.player.stat_points = total_points
            
            self.player.recalculate_stats()
            self.log(f"[green]你的屬性已重置為 10。獲得了 {total_points} 點屬性點。[/]")
            
        else:
             self.log("這卷軸似乎沒有任何效果...?")

    def handle_enemy_turn(self, target, curr_room):
        import random
        
        # Thief Logic
        if hasattr(target, 'is_thief') and target.is_thief:
            # Flee Chance (Low HP)
            if target.hp < target.max_hp * 0.5 and random.random() < 0.5:
                 self.log(f"[bold yellow]{target.name} 見勢不妙，腳底抹油溜走了! (Fled)[/]")
                 curr_room.enemies.remove(target)
                 return
                 
            # Steal (50% chance if not attacking strongly?)
            # Let's say 40% chance to steal instead of attack
            if random.random() < 0.4:
                # Steal Gold
                steal_amount = random.randint(1, 20) + (target.level * 5)
                if self.player.gold > 0:
                    actual_steal = min(self.player.gold, steal_amount)
                    self.player.gold -= actual_steal
                    target.stolen_gold += actual_steal
                    self.log(f"[red]{target.name} 趁你不注意，從你身上偷走了 {actual_steal} 金幣![/]")
                    return # Skip attack turn
                else:
                    self.log(f"[dim]{target.name} 試圖偷竊，但發現你身無分文。[/]")

        # Enemy Flee Logic
        # Condition: Elite (HP>=300 or Mutated) AND Not Boss AND Low HP (<20%)
        is_boss = target.proto_id and target.proto_id.startswith('boss_')
        is_mutated = target.id and "mutated" in target.id
        is_elite = target.max_hp >= 300 or is_mutated
        
        if not is_boss and is_elite and target.hp < target.max_hp * 0.2:
            if random.random() < 0.3:
                self.log(f"[bold yellow]{target.name} 驚恐地逃跑了! (Fled)[/]")
                curr_room.enemies.remove(target)
                return

        # Enemy Attack / Skill
        e_dmg = 0
        flavor = "攻擊"
        
        # Try Skill First
        skill_res = target.use_skill()
        if skill_res:
            e_dmg, flavor, _ = skill_res
        else:
            e_dmg = target.attack()
            flavor = random.choice(target.attack_flavor) if hasattr(target, 'attack_flavor') else "攻擊"
        
        # Defense calculation (Use Player Method)
        defense = self.player.get_defense()
        
        # Mitigate damage
        final_dmg = max(0, e_dmg - defense)
        
        self.player.hp -= final_dmg
        self.log(f"{target.name} {flavor}了你!")
        self.log(f"你受到了 [red]{final_dmg}[/] 點傷害! (減免: {defense})")
        
        # Armor Durability Loss (Player Taking Damage)
        if final_dmg > 0:
             # Valid armor slots
             armor_slots = ['body', 'head', 'legs', 'feet', 'l_hand'] # l_hand can be shield
             valid_items = []
             for slot in armor_slots:
                 item = self.player.equipment.get(slot)
                 if item and hasattr(item, 'max_durability') and item.max_durability > 0:
                     valid_items.append((slot, item))
             
             if valid_items:
                 slot, item = random.choice(valid_items)
                 
                 # Chance
                 chance = 0.1
                 if target.level > self.player.level:
                      chance += (target.level - self.player.level) * 0.05
                 
                 if random.random() < chance:
                     item.current_durability -= 1
                     if item.current_durability <= 0:
                         self.log(f"[bold red]你的 {item.name} 損壞了![/]")
                         del self.player.equipment[slot]
                         self.player.recalculate_stats()
                     elif item.current_durability <= item.max_durability * 0.1:
                          self.log(f"[bold red]你的 {item.name} 快要壞了! ({item.current_durability}/{item.max_durability})[/]")
        
        # Enemy Sunder Logic (Boss/Elite chance to damage player equipment durability)
        is_boss_e = target.proto_id and target.proto_id.startswith('boss_')
        is_mutated_e = target.id and "mutated" in target.id
        is_elite_e = target.max_hp >= 300 or is_mutated_e
        if is_boss_e or is_elite_e:
            if random.random() < 0.15:
                sunder_slots = ['body', 'head', 'legs', 'feet', 'r_hand', 'l_hand']
                p_sunder_cands = []
                for s in sunder_slots:
                    eq = self.player.equipment.get(s)
                    if eq and hasattr(eq, 'current_durability') and eq.current_durability > 0:
                        p_sunder_cands.append((s, eq))
                if p_sunder_cands:
                    s_slot, s_item = random.choice(p_sunder_cands)
                    s_dur = random.randint(2, 5)
                    s_old = s_item.current_durability
                    s_item.current_durability = max(0, s_item.current_durability - s_dur)
                    self.log(f"[bold red]{target.name} sunder! {s_item.name} durability {s_old} -> {s_item.current_durability}[/]")
                    if s_item.current_durability <= 0:
                        del self.player.equipment[s_slot]
                        self.player.recalculate_stats()
                        self.log(f"[bold red]{s_item.name} destroyed![/]")

        if self.player.hp <= 0:
            self.handle_death()
            return
        
        # Counter-Attack Logic
        if self.player.is_sitting:
            self.log(f"[bold yellow]你受到攻擊，驚跳起來反擊！(Stand Up)[/]")
            self.player.is_sitting = False
        
        # Tick player status effects each combat turn (玩家狀態每回合遞減)
        p_expired = self.player.tick_status_effects()
        for eff in p_expired:
            if eff == 'knockdown':
                self.log(f"[dim]你從擊倒中恢復了。[/]")
            elif eff == 'blind':
                self.log(f"[dim]你的視線恢復了。[/]")

        if self.player.hp > 0:
            # 50% Chance to Counter Attack unless dead
            if random.random() < 0.5:
                 # Counter Attack!
                 c_dmg = self.calculate_player_damage()
                 self.log(f"[bold cyan]反擊! (Counter Attack)[/]")
                 self.perform_attack(target, c_dmg, "你反擊了", color="cyan")
                 if not target.is_alive():
                     self.resolve_turn(target, curr_room) # Handle kill rewards if counter attack kills
            else:
                 self.log(f"[dim]你試圖反擊但失敗了。(Miss)[/]")

        if self.player.hp <= 0:
            self.handle_death()
            # self.running = False


    def show_inventory(self):
        self.log("[bold]背包 (Inventory)[/]")
        self.log(f"金幣: [yellow]{self.player.gold}[/]")
        if not self.player.inventory:
            self.log("你身上什麼都沒有。")
        else:
            for idx, item in enumerate(self.player.inventory):
                description = item.name
                if isinstance(item, Weapon):
                    description += f" (攻: {item.min_dmg}-{item.max_dmg})"
                elif isinstance(item, Armor):
                    description += f" (防: {item.defense})"
                
                # Format: 1. [Color]Name[/] (Eng) (Stats)
                display_name = item.get_display_name()
                stats_part = description.replace(item.name, "")
                self.log(f"{idx+1}. {display_name} {stats_part}")



    def handle_shop(self, cmd):
        curr_room = self.world.get_room(self.player.x, self.player.y)
        if not curr_room.shop:
            self.log("這裡沒有商店。")
            return

        parts = cmd.split(' ', 1)
        subcmd = parts[0]
        arg = parts[1] if len(parts) > 1 else ""

        if subcmd == "list":
            self.log(f"[bold yellow]{curr_room.shop.name}[/]")
            self.log("[bold]商品列表:[/bold]")
            for idx, item in enumerate(curr_room.shop.inventory):
                self.log(f"{idx+1}. {item.get_display_name()} : [yellow]{item.value} G[/] ({item.description})")
        
        elif subcmd == "buy":
            if not arg:
                self.log("你要買什麼? (buy <item name/index>)")
                return
            
            target_item, _ = self.get_item_and_index(curr_room.shop.inventory, arg)
            
            if not target_item:
                self.log(f"店裡沒有 '{arg}'。")
                return
            
            if self.player.gold < target_item.value:
                self.log("你的金幣不足!")
                return
                
            self.player.gold -= target_item.value
            curr_room.shop.inventory.remove(target_item)
            self.player.inventory.append(target_item)
            self.log(f"你購買了 {target_item.get_display_name()}，花費了 [yellow]{target_item.value}[/] 金幣。")
            
            # Immediate Restock
            curr_room.shop.restock()

        elif subcmd == "sell":
            if not arg:
                self.log("你要賣什麼? (sell <item name/index>, sell 1,2,3, or sell all <keyword>)")
                return
            
            items_to_sell = []
            
            # Case 1: "sell all <keyword>" or "sell all"
            if arg.lower().startswith("all"):
                keyword = arg[3:].strip().lower()
                if not keyword:
                    self.log("請指定要賣出的物品關鍵字 (例如: sell all meat)。為了安全起見，不支援直接 sell all。")
                    return

                # Find all matching items
                # Create a copy to avoid modification issues during iteration if we were removing
                for item in self.player.inventory:
                    if keyword in item.name.lower() or (item.keyword and keyword in item.keyword.lower()):
                        items_to_sell.append(item)
                
                if not items_to_sell:
                    self.log(f"你身上沒有任何符合 '{keyword}' 的物品。")
                    return

            # Case 2: Range "sell 1~5"
            elif '~' in arg:
                try:
                    parts = arg.split('~')
                    if len(parts) != 2: raise ValueError
                    
                    start_str, end_str = parts[0].strip(), parts[1].strip()
                    if not start_str.isdigit() or not end_str.isdigit(): raise ValueError
                    
                    start_idx = int(start_str) - 1
                    end_idx = int(end_str) - 1
                    
                    current_inv = list(self.player.inventory)
                    
                    # Clamp Bounds
                    start_idx = max(0, start_idx)
                    end_idx = min(len(current_inv) - 1, end_idx)
                    
                    if start_idx > end_idx:
                        self.log("[red]範圍無效 (起始 > 結束)。[/]")
                        return

                    for i in range(start_idx, end_idx + 1):
                        items_to_sell.append(current_inv[i])
                        
                    if not items_to_sell:
                         self.log("該範圍內沒有物品。")
                         return

                except ValueError:
                    self.log("[red]格式錯誤。請使用 sell <start>~<end> (例如: sell 1~5)。[/]")
                    return

            # Case 3: Comma separated indices/names "sell 1,2,3"
            elif ',' in arg:
                targets = arg.split(',')
                # We need to resolve indices to items FIRST because indices change as we remove items
                # Use a list of (item, index) to sort/validate?
                # Actually, just finding the item objects is enough.
                # But wait, if I have two "Daggers" and I say sell 1,2. 
                # If I resolve 1 -> DaggerA, 2 -> DaggerB.
                # Then I remove DaggerA. DaggerB is still DaggerB object. 
                # So resolving to objects first is safe.
                
                current_inv = list(self.player.inventory) # Snapshot for indexing
                
                for target_str in targets:
                    target_str = target_str.strip()
                    if not target_str: continue
                    
                    # Logic from get_item_and_index but applied to snapshot
                    found_item = None
                    
                    if target_str.isdigit():
                        idx = int(target_str) - 1
                        if 0 <= idx < len(current_inv):
                            found_item = current_inv[idx]
                    else:
                        # Keyword search in snapshot
                        for item in current_inv:
                            if target_str.lower() in item.name.lower() or (item.keyword and target_str.lower() in item.keyword.lower()):
                                found_item = item
                                break
                                
                    if found_item:
                        items_to_sell.append(found_item)
                    else:
                        self.log(f"[yellow]警告: 找不到 '{target_str}'。[/]")
            
            # Case 3: Single Item
            else:
                target_item, _ = self.get_item_and_index(self.player.inventory, arg)
                if target_item:
                    items_to_sell.append(target_item)
                else:
                     self.log(f"你身上沒有 '{arg}'。")
                     return

            # Execute Sell
            if not items_to_sell:
                return

            total_gold = 0
            sold_names = []
            
            for item in items_to_sell:
                if item in self.player.inventory: # Double check in case duplicates in list
                    val = item.value // 2
                    self.player.gold += val
                    self.player.inventory.remove(item)
                    total_gold += val
                    sold_names.append(f"{item.get_display_name()}")
            
            if total_gold > 0:
                self.log(f"你賣掉了 {len(sold_names)} 件物品: {', '.join(sold_names)}")
                self.log(f"總共獲得了 [bold yellow]{total_gold} G[/]。")
            else:
                self.log("沒有賣出任何物品。")

        else:
            self.log("商店指令: list, buy, sell")
        
    def handle_train(self, stat):
        # 1. Show Status if no arg
        if not stat:
            self.log(f"[bold]可用屬性點數: [green]{self.player.stat_points}[/][/]")
            self.log("使用方法: [cyan]train <stat>[/] (例如: train str, train dex, train con, train int, train luk)")
            return

        if self.player.stat_points <= 0:
            self.log("[red]你沒有剩餘的屬性點數。[/]")
            return
            
        stat = stat.lower()
        if stat in ['str', 'strength']:
            self.player.str += 1
            self.log(f"你的 [bold]力量 (STR)[/] 提升了! (目前: {self.player.str})")
        elif stat in ['dex', 'dexterity']:
            self.player.dex += 1
            self.log(f"你的 [bold]敏捷 (DEX)[/] 提升了! (目前: {self.player.dex})")
        elif stat in ['con', 'constitution']:
            self.player.con += 1
            self.log(f"你的 [bold]體質 (CON)[/] 提升了! (目前: {self.player.con})")
        elif stat in ['int', 'intelligence']:
            self.player.int += 1
            self.log(f"你的 [bold]智力 (INT)[/] 提升了! (目前: {self.player.int})")
        else:
            self.log("未知的屬性。可接受: str, dex, con, int。")
            return
            
        self.player.stat_points -= 1
        self.player.recalculate_stats()



    def handle_get_item(self, keyword):
        curr_room = self.world.get_room(self.player.x, self.player.y)
        
        if keyword == "all":
            if not curr_room.items:
                self.log("這裡沒有任何東西可以撿。")
                return
            
            # Get All Logic
            count = 0
            # Iterate a copy since we are modifying the list
            for item in list(curr_room.items):
                curr_room.items.remove(item)
                self.player.inventory.append(item)
                count += 1
            
            self.log(f"你撿起了 [bold cyan]所有物品[/] (共 {count} 件)。")
            return

        target_item, _ = self.get_item_and_index(curr_room.items, keyword)
        
        if target_item:
            curr_room.items.remove(target_item)
            self.player.inventory.append(target_item)
            self.log(f"你撿起了 {target_item.get_display_name()}。")
        else:
            self.log(f"這裡沒有 '{keyword}'。")


    def handle_drop_item(self, keyword):
        target_item, _ = self.get_item_and_index(self.player.inventory, keyword)
        
        if target_item:
            target_item.drop_time = time.time() # Set drop time
            self.player.inventory.remove(target_item)
            curr_room = self.world.get_room(self.player.x, self.player.y)
            curr_room.items.append(target_item)
            self.log(f"你丟下了 {target_item.get_display_name()}。")
        else:
            self.log(f"你身上沒有 '{keyword}'。")

    def handle_drink(self, keyword):
        """Drink a potion from inventory or water from the fountain"""
        # Fountain Override (0, 0)
        if keyword.lower() == "water" and self.player.x == 0 and self.player.y == 0:
            import time
            elapsed = time.time() - self.player.fountain_last_use
            cooldown = 7200 # 2 hours
            if elapsed < cooldown:
                remaining = int(cooldown - elapsed)
                m, s = divmod(remaining, 60)
                h, m = divmod(m, 60)
                self.log(f"[yellow]泉水似乎還在匯聚靈力... 你需要再等待 {h:02d}:{m:02d}:{s:02d} 才能再次飲用。[/]")
                return
            
            # Recovery
            self.player.hp = self.player.max_hp
            self.player.mp = self.player.max_mp
            self.player.mv = self.player.max_mv
            self.player.fountain_last_use = time.time()
            self.log("[bold cyan]你飲下了清涼的泉水，感覺全身充滿了力量！(HP/MP/MV 已完全恢復)[/]")
            return

        target_item, _ = self.get_item_and_index(self.player.inventory, keyword)
        
        if not target_item:
            self.log(f"你身上沒有 '{keyword}'。")
            return

        # Potion Logic - check keyword field since name is in Chinese
        if "red" in target_item.keyword.lower():
            self.player.inventory.remove(target_item)
            # Restore 50 HP + 20 MV
            recovered_hp = min(50, self.player.max_hp - self.player.hp)
            recovered_mv = min(20, self.player.max_mv - self.player.mv)
            self.player.hp += recovered_hp
            self.player.mv += recovered_mv
            self.log(f"你喝下了 [red]紅藥水[/]! 恢復了 {recovered_hp} HP 和 {recovered_mv} MV!")
            
        elif "blue" in target_item.keyword.lower():
            self.player.inventory.remove(target_item)
            # Restore 50 MP
            recovered_mp = min(50, self.player.max_mp - self.player.mp)
            self.player.mp += recovered_mp
            self.log(f"你喝下了 [blue]藍藥水[/]! 恢復了 {recovered_mp} MP!")
            
        else:
            self.log(f"你無法喝下 {target_item.name}。")

    def handle_eat(self, keyword):
        target_item, _ = self.get_item_and_index(self.player.inventory, keyword)
        
        if not target_item:
            self.log(f"你身上沒有 '{keyword}'。")
            return

        # Food Logic - check keyword field
        if "meat" in target_item.keyword.lower() or "bread" in target_item.keyword.lower():
            self.player.inventory.remove(target_item)
            
            if "meat" in target_item.keyword.lower():
                # Raw Meat restores 10 HP, 10 MP, 10 MV
                recovered_hp = min(10, self.player.max_hp - self.player.hp)
                recovered_mp = min(10, self.player.max_mp - self.player.mp)
                recovered_mv = min(10, self.player.max_mv - self.player.mv)
                self.player.hp += recovered_hp
                self.player.mp += recovered_mp
                self.player.mv += recovered_mv
                self.log(f"你吃下了 {target_item.get_display_name()}! 恢復了 {recovered_hp} HP、{recovered_mp} MP 和 {recovered_mv} MV!")
            elif "bread" in target_item.keyword.lower():
                # Bread restores only HP
                recovered_hp = min(20, self.player.max_hp - self.player.hp)
                self.player.hp += recovered_hp
                self.log(f"你吃下了 {target_item.get_display_name()}! 恢復了 {recovered_hp} HP!")
        else:
            self.log(f"你無法吃下 {target_item.name}。")

    def handle_shop_list(self):
        curr_room = self.world.get_room(self.player.x, self.player.y)
        if not curr_room.shop:
            self.log("這裡沒有商店。")
            return

        self.log(f"[bold]{curr_room.shop.name}[/]")
        self.log(curr_room.shop.description)
        for item in curr_room.shop.inventory:
            price = f"[yellow]{item.value}[/]"
            self.log(f"{item.get_display_name()} ({item.keyword}) - ${price}")

    def handle_shop_buy(self, keyword):
        curr_room = self.world.get_room(self.player.x, self.player.y)
        if not curr_room.shop:
            self.log("這裡沒有商店。")
            return

        target_item = None
        for item in curr_room.shop.inventory:
             if keyword.lower() in item.keyword.lower() or keyword.lower() in item.name.lower():
                target_item = item
                break
        
        if not target_item:
            self.log(f"店裡沒有 '{keyword}'。")
        elif self.player.gold < target_item.value:
            self.log("你的金幣不足!")
        else:
            self.player.gold -= target_item.value
            # Remove from shop inventory (Finite Stock)
            curr_room.shop.inventory.remove(target_item)
            self.player.inventory.append(target_item)
            self.log(f"你購買了 {target_item.get_display_name()}，花費了 [yellow]{target_item.value}[/] 金幣。")

    def handle_repair(self, target_str):
        # 1. Location Check (Town Square 0,0)
        if self.player.x != 0 or self.player.y != 0:
            self.log("[red]只有在城鎮廣場 (Start Point) 才能進行修理。[/]")
            return

        target_str = target_str.strip().lower()
        cost_per_point = 1
        
        items_to_repair = []
        
        if target_str == 'all':
            # Check Equipment
            for item in self.player.equipment.values():
                if item and hasattr(item, 'max_durability') and item.current_durability < item.max_durability:
                    items_to_repair.append(item)
            # Check Inventory
            for item in self.player.inventory:
                if item and hasattr(item, 'max_durability') and item.current_durability < item.max_durability:
                    items_to_repair.append(item)
            
            if not items_to_repair:
                self.log("你沒有任何需要修理的物品。")
                return
        else:
            # Single Item Repair
            slot_map = {
                 'e1': 'r_hand', 'e2': 'l_hand',
                 'e3': 'head', 'e4': 'neck', 
                 'e5': 'body', 'e6': 'legs', 
                 'e7': 'feet', 'e8': 'finger'
            }

            found = None
            # 1. Check Slot ID
            if target_str in slot_map:
                 real_slot = slot_map[target_str]
                 found = self.player.equipment.get(real_slot)
            else:
                 # 2. Check Equipment Name
                 for item in self.player.equipment.values():
                     if item and (target_str in item.name.lower() or (item.keyword and target_str in item.keyword.lower())):
                         found = item
                         break
                
                 # 3. Check Inventory Name
                 if not found:
                     found, _ = self.get_item_and_index(self.player.inventory, target_str)
            
            if not found:
                self.log(f"找不到 '{target_str}'。")
                return
            
            if not hasattr(found, 'max_durability') or found.max_durability <= 0:
                self.log(f"{found.name} 不這需要修理。")
                return
            
            if found.current_durability >= found.max_durability:
                self.log(f"{found.name} 完好無損。")
                return
                
            items_to_repair.append(found)

        # Calculate Total Cost
        total_cost = 0
        total_missing = 0
        for item in items_to_repair:
            missing = item.max_durability - item.current_durability
            total_cost += missing * cost_per_point
            total_missing += missing
            
        if total_cost == 0:
             self.log("不需要修理。")
             return

        self.log(f"修理這些物品需要 [yellow]{total_cost}[/] 金幣。")
        
        # Check Gold
        if self.player.gold < total_cost:
             self.log(f"[red]金幣不足! (需要: {total_cost}, 擁有: {self.player.gold})[/]")
             return
             
        # Execute Repair
        self.player.gold -= total_cost
        for item in items_to_repair:
            item.current_durability = item.max_durability
            
        self.log(f"[green]修理完成! 花費了 {total_cost} 金幣。[/]")

    def handle_train(self, stat_name):
        if self.player.stat_points <= 0:
            self.log("你沒有足夠的升級點數。")
            return
            
        stat_name = stat_name.lower().strip()
        valid_stats = ['str', 'dex', 'con', 'int', 'luk']
        
        if stat_name not in valid_stats:
            self.log(f"無效的屬性。可用: {', '.join(valid_stats)}")
            return
            
        # Increment Stat
        current_val = getattr(self.player, stat_name)
        setattr(self.player, stat_name, current_val + 1)
        self.player.stat_points -= 1
        self.player.recalculate_stats()
        
        self.log(f"[green]你的 {stat_name.upper()} 提升了! (點數剩餘: {self.player.stat_points})[/]")

    def show_equipment(self):
        self.log("[bold]裝備 (Equipment)[/]")
        for idx, (slot, item) in enumerate(self.player.equipment.items()):
            display = item.get_display_name() if item else "(Empty)"
            
            dur_str = ""
            if item and hasattr(item, 'max_durability') and item.max_durability > 0:
                dur_str = f" [dim](Dur: {item.current_durability}/{item.max_durability})[/]"
                
            self.log(f"{idx+1}. {slot.capitalize()}: {display}{dur_str}")

    def handle_wear_item(self, keyword):
        # 1. Parse explicit slot suffix
        explicit_slot = None
        parts = keyword.split()
        if len(parts) > 1:
            last_word = parts[-1].lower()
            if last_word in ['left', 'l', 'off', 'offhand']:
                explicit_slot = 'l_hand'
                keyword = " ".join(parts[:-1])
            elif last_word in ['right', 'r', 'main', 'mainhand']:
                explicit_slot = 'r_hand'
                keyword = " ".join(parts[:-1])

        target_item, _ = self.get_item_and_index(self.player.inventory, keyword)
        
        if not target_item:
            self.log(f"你身上沒有 '{keyword}'。")
            return

        if not hasattr(target_item, 'slot'):
             self.log(f"{target_item.name} 無法穿戴。")
             return
             
        slot = target_item.slot
        actual_slot = slot
        
        
        # Dual Wield / 2H / Explicit Hand Logic
        hands = getattr(target_item, 'hands', 1)
        
        if hands == 2:
             # 2H Logic (Always r_hand, blocks l_hand)
             # Unequip existing
             if self.player.equipment.get('r_hand'):
                self.player.inventory.append(self.player.equipment['r_hand'])
                self.player.equipment['r_hand'] = None
                self.log(f"你卸下了 {self.player.inventory[-1].name}。")
                
             if self.player.equipment.get('l_hand'):
                self.player.inventory.append(self.player.equipment['l_hand'])
                self.player.equipment['l_hand'] = None
                self.log(f"你卸下了 {self.player.inventory[-1].name} (因裝備雙手武器)。")
                
             actual_slot = 'r_hand'
             
        elif slot == 'l_hand':
             # Offhand Logic - Check if main hand is 2H
             r_hand = self.player.equipment.get('r_hand')
             if r_hand and getattr(r_hand, 'hands', 1) == 2:
                  self.log(f"[red]你正裝備著雙手武器，無法裝備副手物品。[/]")
                  return
             actual_slot = 'l_hand'
             
        elif slot == 'r_hand':
             # Weapon Logic
             if explicit_slot:
                 # User forced a hand
                 actual_slot = explicit_slot
             else:
                 # Auto Logic
                 if not self.player.equipment.get('r_hand'):
                     actual_slot = 'r_hand'
                 elif not self.player.equipment.get('l_hand') and getattr(self.player.equipment.get('r_hand'), 'hands', 1) < 2:
                     actual_slot = 'l_hand'
                 else:
                     actual_slot = 'r_hand' # Default swap main
                     
             # Check Conflicts
             if actual_slot == 'l_hand':
                 # If Main hand has 2H, cannot equip offhand
                 r_item = self.player.equipment.get('r_hand')
                 if r_item and (getattr(r_item, 'hands', 1) == 2 or r_item.slot == '2h'):
                     self.player.inventory.append(r_item)
                     self.player.equipment['r_hand'] = None
                     self.log("你收起了雙手武器以裝備副手。")

        else:
             # Armor etc.
             actual_slot = slot
        
        # Swap existing item
        if self.player.equipment.get(actual_slot):
             old_item = self.player.equipment[actual_slot]
             self.player.inventory.append(old_item)
             self.player.equipment[actual_slot] = None
             self.log(f"你脫下了 {old_item.get_display_name()}。")
        
        # Equip
        self.player.equipment[actual_slot] = target_item
        self.player.inventory.remove(target_item)
        self.log(f"你裝備了 [green]{target_item.get_display_name()}[/] ({actual_slot})。")
        self.player.recalculate_stats()


    def handle_remove_item(self, keyword):
        # Support index removal based on show_equipment order
        equipment_list = list(self.player.equipment.items())
        
        target_slot = None
        target_item = None
        
        keyword = keyword.strip().lower()
        
        # Slot Mapping (e1-e8)
        slot_map = {
             'e1': 'r_hand', 'e2': 'l_hand',
             'e3': 'head', 'e4': 'neck', 
             'e5': 'body', 'e6': 'legs', 
             'e7': 'feet', 'e8': 'finger'
        }
        
        if keyword in slot_map:
            target_slot = slot_map[keyword]
            target_item = self.player.equipment.get(target_slot)
        elif keyword.isdigit():
            idx = int(keyword) - 1
            if 0 <= idx < len(equipment_list):
                target_slot, target_item = equipment_list[idx]
        else:
            # Keyword match
            for slot, item in equipment_list:
                if item and (keyword.lower() in item.keyword.lower() or keyword.lower() in item.name.lower()):
                    target_slot = slot
                    target_item = item
                    break
            # Also check if keyword matches slot name? "remove head"
            if not target_slot and keyword in self.player.equipment:
                 target_slot = keyword
                 target_item = self.player.equipment.get(keyword)

        if target_slot and target_item:
            self.player.equipment[target_slot] = None
            self.player.inventory.append(target_item)
            self.player.recalculate_stats()
            self.log(f"你脫下了 {target_item.get_display_name()}。")
        elif target_slot and not target_item:
             self.log(f"{target_slot} 已經是空的了。")
        else:
            self.log(f"你沒有裝備 '{keyword}'。")

    def handle_wait(self):
        self.log("你原地休息了一會兒...")
        self.update_time(10)
        self.check_room_aggression()

    def handle_inspect_enemy(self, target_name):
        """Inspect enemy equipment in the same room (偵查敵人裝備 — sne <enemy>)"""
        curr_room = self.world.get_room(self.player.x, self.player.y)
        target = None
        
        for enemy in curr_room.enemies:
            if target_name.lower() in enemy.name.lower():
                target = enemy
                break
        
        if not target:
            self.log(f"你在這裡沒看到 '{target_name}'。")
            return
        
        self.log(f"[bold cyan]== 偵查 {target.name} ==[/]")
        self.log(f"等級: Lv.{target.level} | HP: {target.hp}/{target.max_hp} | 類型: {target.type}")
        
        if target.equipment:
            self.log("[bold]裝備:[/]")
            slot_names = {'r_hand': '右手', 'l_hand': '左手', 'body': '護甲', 
                         'head': '頭盔', 'legs': '護腿', 'feet': '靴子'}
            for slot, item in target.equipment.items():
                slot_cn = slot_names.get(slot, slot)
                dur_str = ""
                if hasattr(item, 'current_durability') and hasattr(item, 'max_durability'):
                    dur_pct = int(item.current_durability / item.max_durability * 100) if item.max_durability > 0 else 0
                    if dur_pct <= 20:
                        dur_str = f" [red](耐久: {item.current_durability}/{item.max_durability} - 即將損壞!)[/]"
                    elif dur_pct <= 50:
                        dur_str = f" [yellow](耐久: {item.current_durability}/{item.max_durability})[/]"
                    else:
                        dur_str = f" (耐久: {item.current_durability}/{item.max_durability})"
                
                display = item.get_display_name() if hasattr(item, 'get_display_name') else item.name
                self.log(f"  [{slot_cn}] {display}{dur_str}")
        else:
            self.log("[dim]沒有裝備。[/]")
        
        if target.debuffs:
            debuff_names = {'blind': '致盲', 'knockdown': '擊倒', 'def_down': '防禦下降'}
            debuff_str = ', '.join(f"{debuff_names.get(k,k)} ({v}回合)" for k, v in target.debuffs.items())
            self.log(f"[yellow]狀態: {debuff_str}[/]")

    def handle_sit(self):
        if self.player.is_sitting:
            self.log("你已經坐下了。")
            return
        
        self.player.is_sitting = True
        self.log("[green]你坐下來休息。體力恢復速度提升！[/]")

    def handle_sneak(self):
        """Toggle stealth mode (潛行模式切換)"""
        if self.player.is_sneaking:
            self.player.is_sneaking = False
            self.log("[dim]你停止潛行，恢復正常行動。[/]")
        else:
            self.player.is_sneaking = True
            self.log("[bold cyan]你開始潛行... 腳步輕盈 (偵查加成 +30, 失敗不觸發敵人)[/]")

    def handle_stand(self):
        # Check for knockdown recovery
        if self.player.has_status('knockdown'):
            del self.player.status_effects['knockdown']
            self.player.is_sitting = False
            self.log("[bold green]你掙扎著從地上爬了起來! (擊倒解除)[/]")
            return
        
        if not self.player.is_sitting:
            self.log("你已經站著了。")
            return
        
        self.player.is_sitting = False
        self.log("[green]你站了起來。[/]")

class DataLoader:

    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.items = {} # id -> Item
        self.enemies = {} # id -> Enemy (prototype)
        self.rooms = {} # id -> Room
        self.settings = {}
        self.balance = BalanceManager(os.path.join(self.data_dir, 'balance.csv'))
        self.load_settings()

    def load_settings(self):
        try:
            import csv
            with open(os.path.join(self.data_dir, 'settings.csv'), 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Try to convert to int/float if possible, otherwise string
                    val = row['value']
                    try:
                        if '.' in val: val = float(val)
                        else: val = int(val)
                    except ValueError:
                        pass
                    self.settings[row['key']] = val
            print("Settings loaded.")
        except Exception as e:
            print(f"Error loading settings: {e} (Using defaults)")

    def load_all(self):
        self.load_items()
        self.load_enemies()
        self.load_rooms()

    def load_skills(self, filepath):
        """Loads skills from CSV."""
        skills = {}
        if not os.path.exists(filepath):
            print(f"Warning: {filepath} not found.")
            return skills
            
        try:
            import csv
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    skill_id = row['id']
                    # Parse cost
                    try: cost_val = int(row['cost_value'])
                    except: cost_val = 0
                    
                    # Parse level
                    try: req_lv = int(row['req_level'])
                    except: req_lv = 1
                    
                    skills[skill_id] = {
                        "name": row['name'],
                        "cost_type": row['cost_type'], # mp, mv, none
                        "cost": cost_val,
                        "dmg_formula": row['damage_formula'],
                        "effect": row['effect'],
                        "desc": row['description'],
                        "req_lv": req_lv,
                        "type": row['type'] # active, spell, passive, enemy
                    }
        except Exception as e:
            print(f"Error loading skills: {e}")
        return skills

    def load_items(self):
        try:
            import csv
            # use utf-8-sig to handle Excel CSVs (which add BOM)
            with open(os.path.join(self.data_dir, 'items.csv'), 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames and 'hands' not in reader.fieldnames:
                     print(f"[items.csv] Warning: hands column missing")
                for row in reader:
                    # id,name,type,value,keyword,min_dmg,max_dmg,defense,slot,description,english_name,hands,accuracy,max_durability,rarity,set_id,is_unique
                    item_id = row['id']
                    name = row['name']
                    i_type = row['type']
                    value = row['value']
                    keyword = row['keyword']
                    slot = row['slot']
                    desc = row['description']
                    english_name = row.get('english_name', '')
                    
                    max_dur = int(row.get('max_durability', 0))
                    csv_rarity = row.get('rarity', 'Common').strip() or 'Common'
                    set_id = row.get('set_id', '').strip()
                    is_unique = row.get('is_unique', 'FALSE').strip().upper() == 'TRUE'

                    item = None
                    if i_type == 'weapon':
                        min_d = int(row.get('min_dmg', 0))
                        max_d = int(row.get('max_dmg', 0))
                        hands = int(row.get('hands', 1)) 
                        accuracy = int(row.get('accuracy', 100))
                        item = Weapon(name, desc, int(value), keyword, min_d, max_d, slot, rarity=csv_rarity, english_name=english_name, hands=hands, accuracy=accuracy, max_durability=max_dur, set_id=set_id, is_unique=is_unique)
                    elif i_type == 'armor' or i_type == 'helm': 
                        defense = int(row.get('defense', 0))
                        item = Armor(name, desc, int(value), keyword, int(defense), slot, rarity=csv_rarity, english_name=english_name, max_durability=max_dur, set_id=set_id, is_unique=is_unique)
                    else:
                        item = Item(name, desc, int(value), keyword, rarity=csv_rarity, english_name=english_name, max_durability=max_dur, set_id=set_id, is_unique=is_unique)
                    
                    self.items[item_id] = item
            print("Items loaded.")
        except Exception as e:
            print(f"Error loading items: {e}")

    def load_enemies(self):
        try:
            import csv
            with open(os.path.join(self.data_dir, 'enemies.csv'), 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # id,name,description,hp,min_dmg,max_dmg,xp,gold,loot_item_id,loot_chance
                    loot = []
                    # New Format: id|chance|rarity;id2|chance2|rarity2
                    loot_str = row.get('loot_item_id', '')
                    if loot_str:
                        # Check if it's the old single ID format (no | and check loot_chance col)
                        if '|' not in loot_str and ';' not in loot_str and row.get('loot_chance'):
                             if loot_str in self.items:
                                 loot.append((self.items[loot_str], float(row['loot_chance']), None))
                        else:
                            # Parse complex string
                            for entry in loot_str.split(';'):
                                entry = entry.strip()
                                if not entry: continue
                                
                                parts = entry.split('|')
                                item_id = parts[0]
                                chance = 1.0
                                rarity = None
                                
                                if len(parts) > 1: 
                                    try: chance = float(parts[1])
                                    except: chance = 1.0
                                if len(parts) > 2: rarity = parts[2]
                                
                                if item_id in self.items:
                                    loot.append((self.items[item_id], chance, rarity))
                    
                    level = int(row.get('level', 1))

                    is_thief = (row['id'] == 'mob_thief')

                    enemy = Enemy(
                        row['name'],
                        row['description'],
                        int(row['hp']),
                        (int(row['min_dmg']), int(row['max_dmg'])),
                        int(row['xp']),
                        int(row['gold']),
                        loot,
                        row['id'],
                        int(row['respawn_time']),
                        row['type'],
                        level,
                        is_thief=is_thief,
                        balance_manager=self.balance
                    )

                    
                    # Equip items
                    equip_str = row.get('equipment', '')
                    if equip_str:
                        item_ids = equip_str.split(';')
                        for i_id in item_ids:
                            i_id = i_id.strip()
                            if i_id and i_id in self.items:
                                # Clone item for enemy
                                import copy
                                item = copy.deepcopy(self.items[i_id])
                                enemy.equip(item)
                                # Also add to loot table (100% chance? or less? User said they drop it)
                                # Let's add with 50% chance to avoid economy flooding, or 100% if "Visible"
                                # User said: "seeing equipped items... imply probability to drop"
                                # Let's add to loot with 30% chance.
                                # Let's add with 50% chance to avoid economy flooding, or 100% if "Visible"
                                # User said: "seeing equipped items... imply probability to drop"
                                # Let's add to loot with 30% chance.
                                enemy.loot_table.append((item, 0.3, None))

                    self.enemies[row['id']] = enemy
            print(f"Enemies loaded: {len(self.enemies)}")
            # Debug: Check if new mobs are loaded
            for mob_id in ['mob_bat', 'mob_boar', 'mob_ent', 'mob_wisp']:
                if mob_id in self.enemies:
                    print(f"DEBUG: Found {mob_id}")
                else:
                    print(f"DEBUG: Missing {mob_id}!")
        except Exception as e:
            print(f"Error loading enemies: {e}")

    def load_commands(self):
        commands_map = {}
        commands_set = set()
        commands_help = []
        try:
            with open(os.path.join(self.data_dir, 'commands.csv'), 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cmd = row['command']
                    commands_set.add(cmd.lower())
                    
                    aliases = row['aliases'].split(';') if row['aliases'] else []
                    for alias in aliases:
                        if alias:
                            commands_map[alias.strip()] = cmd
                            
                    # Store help info
                    commands_help.append({
                        'command': cmd,
                        'aliases': aliases,
                        'description': row.get('description', ''),
                        'usage': row.get('usage', '')
                    })
        except Exception as e:
            print(f"Error loading commands: {e}")
        return commands_map, commands_set, commands_help

    def load_rooms(self):
        try:
            import csv
            mutation_count = 0
            max_mutations = self.settings.get('max_special_rooms', 3)
            mutation_chance = self.settings.get('mutation_chance', 0.15)
            
            with open(os.path.join(self.data_dir, 'rooms.csv'), 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # id,name,zone,x,y,description,exits,enemy_id,shop_item_ids
                    symbol = ' . '
                    zone = row['zone']
                    if zone == 'village': symbol = Color.colorize('[V]', Color.YELLOW)
                    elif zone == 'forest': symbol = Color.colorize('[F]', Color.GREEN)
                    elif zone == 'mines': symbol = Color.colorize('[M]', Color.MAGENTA)
                    elif zone == 'wasteland': symbol = Color.colorize('[W]', Color.ORANGE)
                    elif zone == 'nexus': symbol = Color.colorize('[O]', Color.CYAN)
                    
                    room = Room(row['name'], row['description'], symbol, zone=zone)
                    room.x = int(row['x'])
                    room.y = int(row['y'])
                    
                    # Enemies
                    # Enemies
                    if row['enemy_id'] and row['enemy_id'] in self.enemies:
                        # Clone enemy prototype
                        proto_id = row['enemy_id']
                        proto = self.enemies[proto_id]
                        import copy
                        import random
                        
                        # Determine Count (Swarm Logic)
                        # Determine Count (Swarm Logic)
                        count = 1
                        is_boss = proto_id.startswith('boss_')
                        is_elite = proto.max_hp >= 300 # Trolls, Bears, Orcs maybe
                        
                        if not is_boss:
                            # Mutation Chance for non-boss enemies
                            if mutation_count < max_mutations and random.random() < mutation_chance:
                                mutation_count += 1
                                new_enemy = copy.deepcopy(proto)
                                new_enemy.mutate()
                                new_enemy.id = f"{proto_id}_mutated_{random.randint(1000,9999)}"
                                try:
                                    room.enemies.append(new_enemy)
                                except AttributeError:
                                    room.enemies = [new_enemy]
                            else:
                                 new_enemy = copy.deepcopy(proto)
                                 room.enemies.append(new_enemy)
                    
                        # Apply Aggression Chance based on Depth
                        # Distance from (0,0) -> Y axis mostly
                        dist = int(((room.x ** 2) + (room.y ** 2)) ** 0.5)
                        
                        # Distance-based Scaling!
                        # Every 5 steps away, enemy level grows by 1.
                        bonus_level = dist // 5
                        if bonus_level > 0:
                            new_enemy.level += bonus_level
                            new_enemy.scale_to_player(new_enemy.level) # Re-scale to its own new level
                        
                        # Chance: 1% per step. Max 80%?
                        chance = min(0.8, dist * 0.01)
                        
                        # Apply to all enemies in room (even if multiple)
                        for e in room.enemies:
                            e.aggro_chance = chance 
                            if e.proto_id and e.proto_id.startswith('boss_'):
                                e.aggro_chance = 1.0
                        else:
                            # Bosses don't mutate (already strong)
                            if is_boss:
                                room.enemies.append(copy.deepcopy(proto))
                        
                        if not is_boss and not is_elite:
                            count = random.randint(1, 5)
                            
                        for _ in range(count):
                            new_enemy = copy.deepcopy(proto)
                            new_enemy.proto_id = proto_id # Store ID for respawn
                            room.enemies.append(new_enemy)
                            # Add to spawn definitions (one entry per spawn or just once?)
                            # Respawn logic iterates queue. If we want them to respawn individually, 
                            # we push to queue individually. 
                            # But wait, respawn queue is populated on death.
                            # So initial population is all we need here.
                            # room.enemy_spawn_defs is not used? Let's check.
                            # room.enemy_spawn_defs seems unused in run loop.
                            # The run loop uses room.respawn_queue which is filled on death.
                            # So initial population is all we need here.
                    
                    # Shop
                    if row.get('shop_item_ids'):
                        shop_items = []
                        for i_id in row['shop_item_ids'].split(';'):
                            if i_id in self.items:
                                shop_items.append(self.items[i_id])
                        if shop_items:
                            room.shop = Shop(f"{row['name']} Shop", "A local shop.", shop_items, balance_manager=self.balance)

                    self.rooms[row['id']] = room
                    room._raw_exits = row['exits']
            print("Rooms loaded.")

        except Exception as e:
            print(f"Error loading rooms: {e}")

    def get_item_by_name(self, item_name):
        """Search for an item by its Chinese name and return a copy of the prototype."""
        import copy
        for item_id, item in self.items.items():
            if item.name == item_name:
                return copy.deepcopy(item)
        return None


if __name__ == "__main__":
    # We need to adapt Game to use DataLoader or coordinates.
    # User asked for CSV. Let's start by just loading them.
    # To make it playable immediately with CSV, I'll add X,Y to CSV or hardcode map gen from CSV ID.
    # Let's add X,Y to rooms.csv in next step for proper map placement.
    game = Game()
    game.run()
