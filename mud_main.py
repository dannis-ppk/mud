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
    def __init__(self, name, description, hp, damage_range, xp_reward, gold_reward, loot_table=None, id=None, respawn_time=30, enemy_type="beast"):
        self.id = id
        self.respawn_time = respawn_time
        self.name = name
        self.description = description
        self.max_hp = hp
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
        if 'def_down' in self.debuffs:
            defense -= 5 # Lower defense by 5
            
        return max(0, defense)
        
    def use_skill(self):
        import random
        # Chance to use skill: 30% for Elite, 50% for Boss, 10% Normal
        is_boss = (self.proto_id and self.proto_id.startswith('boss_'))
        is_mutated = (self.id and "mutated" in self.id)
        is_elite = self.max_hp >= 300 or is_mutated
        
        chance = 0.1
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
    def __init__(self, name, description, value, keyword, rarity="Common", color="white", bonuses=None, english_name=""):
        self.name = name
        self.description = description
        self.value = value
        self.keyword = keyword
        self.english_name = english_name
        self.drop_time = None 
        
        self.rarity = rarity # Common, Fine, Rare
        self.color = color   # white, green, blue
        self.bonuses = bonuses if bonuses else {}

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
            "bonuses": self.bonuses if self.bonuses else {}
        }
    
    @staticmethod
    def from_dict(data):
        if data['type'] == 'weapon':
            item = Weapon(data['name'], data['description'], data['value'], data['keyword'], 
                          data['min_dmg'], data['max_dmg'], data['slot'], 
                          data.get('rarity', "Common"), data.get('color', "white"), 
                          data.get('bonuses', {}), data.get('english_name', ""))
        elif data['type'] == 'armor':
            item = Armor(data['name'], data['description'], data['value'], data['keyword'], 
                         data['defense'], data['slot'], 
                         data.get('rarity', "Common"), data.get('color', "white"), 
                         data.get('bonuses', {}), data.get('english_name', ""))
        else:
            item = Item(data['name'], data['description'], data['value'], data['keyword'], 
                        data.get('rarity', "Common"), data.get('color', "white"), 
                        data.get('bonuses', {}), data.get('english_name', ""))
        return item

class Weapon(Item):
    def __init__(self, name, description, value, keyword, min_dmg, max_dmg, slot='r_hand', rarity="Common", color="white", bonuses=None, english_name="", hands=1, accuracy=100):
        super().__init__(name, description, value, keyword, rarity, color, bonuses, english_name)
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
            "slot": self.slot
        })
        return data

class Armor(Item):
    def __init__(self, name, description, value, keyword, defense, slot='body', rarity="Common", color="white", bonuses=None, english_name=""):
        super().__init__(name, description, value, keyword, rarity, color, bonuses, english_name)
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
    def generate(item_proto, force_rarity=None):
        """Generates a new item instance based on prototype with chance for rarity upgrade."""
        import copy
        import random
        
        new_item = copy.deepcopy(item_proto)
        
        # Skip rarity generation for consumables (they don't benefit from stat bonuses)
        if isinstance(new_item, Item) and not isinstance(new_item, (Weapon, Armor)):
            return new_item
        
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
                bonus_dmg = random.randint(8, 12)
                new_item.bonuses['dmg'] = bonus_dmg
                new_item.min_dmg += bonus_dmg
                new_item.max_dmg += bonus_dmg
                new_item.description += f" (傷害 +{bonus_dmg})"
                
                # Add Stat Bonus (Two Stats)
                # Epic Stat: +3 ~ +5 (x2)
                stats = random.sample(['str', 'dex', 'luk', 'con'], 2)
                for stat in stats:
                    val = random.randint(3, 5)
                    new_item.bonuses[stat] = val
                    new_item.description += f" ({stat.upper()} +{val})"
                
            elif isinstance(new_item, Armor):
                # Epic Def: +6 ~ +10
                bonus_def = random.randint(6, 10)
                new_item.bonuses['def'] = bonus_def
                new_item.defense += bonus_def
                new_item.description += f" (防禦 +{bonus_def})"
                
                # Epic Stat: +3 ~ +5 (x2)
                stats = random.sample(['con', 'dex', 'int', 'str'], 2)
                for stat in stats:
                    val = random.randint(3, 5)
                    new_item.bonuses[stat] = val
                    new_item.description += f" ({stat.upper()} +{val})"
            
            # Necklace/Ring Logic (Epic)
            if new_item.slot == 'neck':
                bonus_hp = random.randint(81, 150)
                bonus_def = random.randint(3, 5)
                new_item.bonuses['hp'] = new_item.bonuses.get('hp', 0) + bonus_hp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                new_item.description += f" (HP +{bonus_hp}, Def +{bonus_def})"
            elif new_item.slot == 'finger':
                bonus_mp = random.randint(81, 150)
                bonus_def = random.randint(3, 5)
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
                bonus_dmg = random.randint(4, 7)
                new_item.bonuses['dmg'] = bonus_dmg
                new_item.min_dmg += bonus_dmg
                new_item.max_dmg += bonus_dmg
                new_item.description += f" (傷害 +{bonus_dmg})"
                
                # Add Stat Bonus
                # Rare Stat: +3 ~ +4
                stat = random.choice(['str', 'dex', 'luk'])
                val = random.randint(3, 4)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"
                
            elif isinstance(new_item, Armor):
                # Rare Def: +3 ~ +5
                bonus_def = random.randint(3, 5)
                new_item.bonuses['def'] = bonus_def
                new_item.defense += bonus_def
                new_item.description += f" (防禦 +{bonus_def})"
                
                # Add Stat Bonus
                stat = random.choice(['con', 'dex', 'int'])
                val = random.randint(3, 4)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"

            # Necklace/Ring Logic (Rare)
            if new_item.slot == 'neck':
                bonus_hp = random.randint(31, 80)
                # Rare Neck Def: +1 ~ +2
                bonus_def = random.randint(1, 2)
                new_item.bonuses['hp'] = new_item.bonuses.get('hp', 0) + bonus_hp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                new_item.description += f" (HP +{bonus_hp}, Def +{bonus_def})"
            elif new_item.slot == 'finger':
                bonus_mp = random.randint(31, 80)
                # Rare Ring Def: +1 ~ +2
                bonus_def = random.randint(1, 2)
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
                bonus_dmg = random.randint(1, 3)
                new_item.bonuses['dmg'] = bonus_dmg
                new_item.min_dmg += bonus_dmg
                new_item.max_dmg += bonus_dmg
                new_item.description += f" (傷害 +{bonus_dmg})"
                
                # Add Stat Bonus
                # Fine Stat: +1 ~ +2
                stat = random.choice(['str', 'dex'])
                val = random.randint(1, 2)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"
                
            elif isinstance(new_item, Armor):
                # Fine Def: +1 ~ +2
                bonus_def = random.randint(1, 2)
                new_item.bonuses['def'] = bonus_def
                new_item.defense += bonus_def
                new_item.description += f" (防禦 +{bonus_def})"
                
                # Add Stat Bonus
                stat = random.choice(['con', 'dex'])
                val = random.randint(1, 2)
                new_item.bonuses[stat] = val
                new_item.description += f" ({stat.upper()} +{val})"

            # Necklace/Ring Logic (Fine)
            if new_item.slot == 'neck':
                bonus_hp = random.randint(10, 30)
                # Fine Neck Def: +0 ~ +1
                bonus_def = random.randint(0, 1)
                new_item.bonuses['hp'] = new_item.bonuses.get('hp', 0) + bonus_hp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                if bonus_def > 0:
                    new_item.description += f" (HP +{bonus_hp}, Def +{bonus_def})"
                else:
                    new_item.description += f" (HP +{bonus_hp})"
            elif new_item.slot == 'finger':
                bonus_mp = random.randint(10, 30)
                # Fine Ring Def: +0 ~ +1
                bonus_def = random.randint(0, 1)
                new_item.bonuses['mp'] = new_item.bonuses.get('mp', 0) + bonus_mp
                new_item.bonuses['def'] = new_item.bonuses.get('def', 0) + bonus_def
                if hasattr(new_item, 'defense'): new_item.defense += bonus_def
                if bonus_def > 0:
                    new_item.description += f" (MP +{bonus_mp}, Def +{bonus_def})"
                else:
                     new_item.description += f" (MP +{bonus_mp})"
                
        return new_item

class Shop:
    def __init__(self, name, description, prototypes):
        self.name = name
        self.description = description
        self.prototypes = prototypes  # List of Item prototypes
        self.inventory = []
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
                 new_item = LootGenerator.generate(proto, force_rarity="Epic")
                 self.inventory.append(new_item)
                 counts["Epic"] += 1
        
        # Fill Rare (Blue) - Target 2
        while counts["Rare"] < 2 and len(self.inventory) < max_items:
            # Pick random prototype that is equipment
            equip_protos = [p for p in self.prototypes if isinstance(p, (Weapon, Armor))]
            if not equip_protos: break
            
            proto = random.choice(equip_protos)
            new_item = LootGenerator.generate(proto, force_rarity="Rare")
            self.inventory.append(new_item)
            counts["Rare"] += 1
            
        # Fill Fine (Green) - Target 3
        while counts["Fine"] < 3:
            equip_protos = [p for p in self.prototypes if isinstance(p, (Weapon, Armor))]
            if not equip_protos: break
            
            proto = random.choice(equip_protos)
            new_item = LootGenerator.generate(proto, force_rarity="Fine")
            self.inventory.append(new_item)
            counts["Fine"] += 1
            
        # Fill Common - Target 25 (Consumables + Equipment)
        while counts["Common"] < 25:
            if not self.prototypes: break
            proto = random.choice(self.prototypes) # Any item
            # Common is default
            new_item = LootGenerator.generate(proto, force_rarity="Common") 
            self.inventory.append(new_item)
            counts["Common"] += 1
            
        # Sort inventory for nicer display? (Optional, maybe by Price or Rarity)
        self.inventory.sort(key=lambda x: x.value)

class Room:
    def __init__(self, name, description, symbol=' . '):
        self.name = name
        self.description = description
        self.symbol = symbol
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
    def __init__(self, name, start_x=0, start_y=0):
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
        
        self.level = 1
        
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
        self.gold = 200 # Starting gold
        self.stat_points = 0 # New: Points to allocate
        
        # Skills
        self.skills = {} # {skill_name: proficiency_percent}
        
        # Resting State
        self.is_sitting = False  # Track if player is sitting down

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
        
        self.max_hp = con * 10 + self.level * 10 + 50
        self.max_mp = int_stat * 10 + wis * 5
        self.max_mv = dex * 10 + con * 10 + 300
        
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
            hp_reg += 1 # Small bonus to HP regen too
        
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
            self.stat_points += 5 # 5 Points per level
            
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
            "xp": self.game.player.xp,
            "next_level_xp": self.game.player.next_level_xp,
            "gold": self.game.player.gold,
            "stat_points": self.game.player.stat_points,
            "equipment": {k: (v.to_dict() if v else None) for k, v in self.game.player.equipment.items()},
            "inventory": [item.to_dict() for item in self.game.player.inventory],
        }

        world_data = {
            "game_time": self.game.game_time,
            "rooms": {}
        }
        for (x, y), room in self.game.world.grid.items():
            room_data = {
                "enemies": [(e.name, e.hp, e.is_aggressive, e.proto_id) for e in room.enemies],
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
                    for e_name, e_hp, e_aggro, e_proto_id in room_data["enemies"]:
                        proto_enemy = self.game.loader.enemies.get(e_proto_id)
                        if proto_enemy:
                            new_enemy = copy.deepcopy(proto_enemy)
                            new_enemy.hp = e_hp
                            new_enemy.is_aggressive = e_aggro
                            new_enemy.proto_id = e_proto_id
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
            
            return {
                "level": player_level,
                "location_name": location_name,
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
        self.skills_data = self.loader.load_skills(os.path.join(self.data_dir, 'skills.csv')) # Load Skills
        # Load from settings, default to 25 if not found
        self.max_log_lines = int(self.loader.settings.get('max_log_lines', 25))
        self.save_manager = SaveManager(self)
        self.setup_world()
        self.player = Player("Hero") # Temp
        
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
        
    def setup_world(self):
        # Clear existing world data
        self.world = World()
        self.loader.load_all()
        self.aliases, self.commands, self.help_data = self.loader.load_commands()
        
        # Build World from Loaded Rooms
        for r_id, room in self.loader.rooms.items():
            if hasattr(room, 'x') and hasattr(room, 'y'):
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
                        line += "[bold red]@[/]"
                    else:
                        line += "[bold white]@[/]" 
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
                                    
                            line += "<b>[bold red]B[/]</b>" if is_boss else "[red]E[/]"
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
        for slot, item in self.player.equipment.items():
            item_name = item.name if item else "Empty"
            color = "white" if item else "dim"
            eq_text += f"{slot.capitalize()}: [{color}]{item_name}[/]\n"
        
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

    def run(self):
        # --- Main Menu ---
        while True:
            self.console.clear()
            self.console.print(Panel(Align.center("[bold cyan]MUD: The Age[/]\n[white]A Text RPG Adventure[/]"), style="bold blue"))
            self.console.print(Align.center("[1] New Game"))
            
            # Show Load Slots
            for i in range(1, 4):
                info = self.save_manager.get_save_info(i)
                if info:
                    self.console.print(Align.center(f"[{i+1}] Load Slot {i}: Lv{info['level']} @ {info['location_name']} ({info['time']})"))
                else:
                    self.console.print(Align.center(f"[{i+1}] Load Slot {i}: [Empty]"))
                    
            auto_info = self.save_manager.get_save_info("auto")
            if auto_info:
                 self.console.print(Align.center(f"[5] Last Auto-Save: Lv{auto_info['level']} @ {auto_info['location_name']} ({auto_info['time']})"))
            
            self.console.print(Align.center("[Q] Quit"))
            
            # Handle msvcrt.getch() which may return special key codes
            key = msvcrt.getch()
            # Special keys like arrow keys start with 0xe0 or 0x00, skip them
            if key in (b'\xe0', b'\x00'):
                msvcrt.getch()  # Read and discard the second byte
                continue
            try:
                choice = key.decode('utf-8').lower()
            except UnicodeDecodeError:
                continue  # Skip invalid input
            if choice == '1':
                # New Game
                self.setup_world() # Reset world
                self.player = Player("Hero") # Reset player
                
                # Starter Items
                red_potion = self.loader.items.get('item_healing_potion_s')
                blue_potion = self.loader.items.get('item_mana_potion_s')
                if red_potion:
                    for _ in range(10):
                        self.player.inventory.append(copy.deepcopy(red_potion))
                if blue_potion:
                    for _ in range(10):
                        self.player.inventory.append(copy.deepcopy(blue_potion))
                        
                self.game_time = 360
                break
            elif choice in ['2', '3', '4']:
                slot = int(choice) - 1
                if self.save_manager.load_game(slot):
                    self.log(f"[green]Save loaded (Slot {slot})![/]")
                    break
                else:
                    self.log("[red]Empty slot![/]") # Might not see this due to clear, but loop continues
            elif choice == '5':
                 if self.save_manager.load_game("auto"):
                    self.log(f"[green]Auto-save loaded![/]")
                    break
            elif choice == 'q':
                sys.exit()
                
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
        elif cmd == 'inv' or cmd == 'inventory' or cmd == 'i':
            self.show_inventory()
            return
            
        # RPG Commands
        elif cmd.startswith('train '):
            self.handle_train(cmd.split(' ', 1)[1])
            return
        elif cmd.startswith('cast '):
            if self.player.is_sitting:
                self.log("[yellow]你坐著不能施法！請先站起來。(stand up)[/]")
                return
            self.handle_skill(cmd.split(' ', 1)[1], is_spell=True)
            return
        elif cmd == 'skill' or cmd.startswith('skill '):
            if self.player.is_sitting:
                self.log("[yellow]你坐著不能使用技能！請先站起來。(stand up)[/]")
                return
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

    def get_damage_description(self, damage, is_crit=False):
        if damage <= 0: return "完全沒有造成傷害 (Miss)"
        if damage < 5: return "輕微地擦傷了 (Grazed)"
        if damage < 10: return "擊中了 (Hit)"
        if damage < 20: return "重重地擊中了 (Hard Hit)"
        if damage < 40: return "造成了毀滅性的一擊 (Smashed)"
        return "將目標打成了碎片! (Obliterated)"

    def perform_attack(self, target, damage, msg_prefix, color="yellow"):
        target.take_damage(damage)
        desc = self.get_damage_description(damage)
        self.log(f"{msg_prefix} [{color}]{damage}[/] 點傷害! ({desc})")

    def calculate_player_damage(self):
        # Calculate Base Damage using Player Stats (including bonuses)
        str_val = self.player.get_stat('str')
        min_d = 2 + (str_val // 2)
        max_d = 5 + (str_val // 2)
        
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

    def perform_attack(self, target, damage_in, flavor_text="攻擊了", color=None):
        if not target.is_alive(): return
        # print("DEBUG: perform_attack called")

        # Accuracy Check
        hit_chance = self.loader.settings.get('base_hit_chance', 100)
        
        # Player attacking Enemy
        weapon = self.player.equipment.get('r_hand')
        if weapon and hasattr(weapon, 'accuracy'):
            hit_chance = weapon.accuracy
            
        # Stat Modifiers
        hit_chance += (self.player.get_stat('dex') * 0.5)
        # Target Avoidance
        target_agi = 10 + (target.damage_range[1] * 0.5) # Estimate
        hit_chance -= (target_agi * 0.5)
        
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
                    cost = f"{sk.get('cost')} {sk.get('cost_type').upper()}"
                    
                    if self.player.level >= req_lv:
                         spells.append(f"[green]{name}[/] ({sid}) - {cost}")
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
            if self.player.level < 3:
                self.log("[red]你還沒學會 Heal (需要 Lv3)。[/]")
                return
            if self.player.mp < 10:
                self.log("[red]魔力不足! (需要 10 MP)[/]")
                return
            self.player.mp -= 10
            self.player.hp = min(self.player.max_hp, self.player.hp + 30)
            self.log(f"[green]你施放了治療術! 生命回復了 30 點。[/]")
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
            # Cost handled in validation block if loaded, else manual fallback below for safety
            # Actually, let's remove manual cost check if data exists? 
            # For phase 1, we keep manual checks unless removed.
            # But we want to use CSV.
            pass
            
        # Check Skill Data (Validation Layer)
        if hasattr(self, 'skills_data') and skill_key in self.skills_data:
            sk_data = self.skills_data[skill_key]
            # print(f"DEBUG: Found skill data for {skill_key}")
            
            # 1. Level Check
            if p.level < sk_data.get('req_lv', 1):
                 self.log(f"[red]你還沒學會 {sk_data['name']} (需要 Lv{sk_data['req_lv']})。[/]")
                 return

            # 2. Cost Check
            cost = sk_data.get('cost', 0)
            ctype = sk_data.get('cost_type', 'none')
            
            if ctype == 'mv':
                if p.mv < cost:
                    self.log(f"[red]體力不足! 需要 {cost} MV。[/]")
                    return
                p.mv -= cost
            elif ctype == 'mp':
                if p.mp < cost:
                     self.log(f"[red]魔力不足! 需要 {cost} MP。[/]")
                     return
                p.mp -= cost
                
        if skill_key == "power":
            # Cost handled in validation block
            base_dmg = random.randint(5 + p.str // 2, 10 + p.str // 2) 
            damage = int(base_dmg * 1.5)
            self.log(f"你使出 [bold cyan]強力攻擊[/]!")

        elif skill_key == "berserk":
            # Cost handled in validation block
            base_dmg = random.randint(5 + p.str // 2, 10 + p.str // 2)
            damage = int(base_dmg * 3.0)
            self.log(f"你進入 [bold red]狂暴狀態[/] 瘋狂攻擊!")

        elif skill_key == "double":
            # Checks handled by validation
            dmg1 = random.randint(5 + p.str // 2, 8 + p.str // 2)
            dmg2 = random.randint(5 + p.str // 2, 8 + p.str // 2)
            damage = dmg1 + dmg2
            self.log(f"你使出 [bold yellow]雙重打擊[/]!")
            
        elif skill_key == "fireball":
            # Checks handled by validation
            damage = random.randint(20 + p.int, 40 + p.int * 2) # Buffed damage
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
            
            # Cost handled in validation block above
            
            if self.check_skill_success('blind'):
                target.debuffs['def_down'] = 3 # 3 Turns
                self.log(f"你不想讓敵人看見，對 {target.name} 使用了 [bold cyan]致盲 (Blind)[/]!")
                self.log(f"[bold yellow]{target.name} 被致盲了! 防禦力下降![/]")
                damage = 0
            else:
                 self.log(f"你試圖致盲 {target.name}，但是失敗了!")
                 return
                 
        elif skill_key == "kick" or skill_key == "kn" or skill_key == "kp":
            if not target:
                self.log("你需要指定目標 (kick <target>)。")
                return

            # Checks handled by validation
            
            if self.check_skill_success('kick'):
                 # Damage + Debuff
                 base_dmg = random.randint(2 + p.str // 3, 5 + p.str // 3)
                 damage = base_dmg
                 target.debuffs['def_down'] = 2 # 2 Turns
                 self.log(f"你飛起一腳，對 {target.name} 使用了 [bold green]踢擊 (Kick)[/]!")
                 self.log(f"[bold yellow]{target.name} 失去平衡! 防禦力下降![/]")
            else:
                 self.log(f"你試圖踢擊 {target.name}，但是滑倒了 (失敗)!")
                 return

        else:
            self.log(f"未知的技能: {skill_key}")
            return

        # Apply Player Attack
        self.perform_attack(target, damage, f"你對 {target.name} 造成了")
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
            
        # Set Aggressive Flag
        target.is_aggressive = True

        # Regular Attack
        # Calculate Damage
        p_dmg = self.calculate_player_damage() 
        
        self.log(f"你攻擊了 {target.name}!")
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
        self.log("[cyan]光芒閃爍，空間扭曲了！(Teleport)[/]")
        
        self.player.x = 0
        self.player.y = 0
        self.player.visited.add((0, 0))
        self.update_time(0) # Instant travel? Or takes time? Instant.
        self.describe_room()

    def handle_enemy_turn(self, target, curr_room):
        import random
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
        
        if self.player.hp <= 0:
            self.handle_death()
            return
        
        # Counter-Attack Logic
        if self.player.is_sitting:
            self.log(f"[bold yellow]你受到攻擊，驚跳起來反擊！(Stand Up)[/]")
            self.player.is_sitting = False

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

    def show_equipment(self):
        self.log("[bold]裝備 (Equipment)[/]")
        for idx, (slot, item) in enumerate(self.player.equipment.items()):
            display = item.get_display_name() if item else "(Empty)"
            self.log(f"{idx+1}. {slot.capitalize()}: {display}")

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
                 if not self.player.equipment.get('r_hand') or (self.player.equipment.get('r_hand') and self.player.equipment.get('r_hand').slot == '2h'):
                     actual_slot = 'r_hand'
                 elif not self.player.equipment.get('l_hand'):
                     actual_slot = 'l_hand'
                 else:
                     actual_slot = 'r_hand' # Default swap main
                     
             # Check Conflicts
             if actual_slot == 'l_hand':
                 # If Main hand has 2H, cannot equip offhand
                 r_item = self.player.equipment.get('r_hand')
                 if r_item and r_item.slot == '2h':
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
        
        keyword = keyword.strip()
        if keyword.isdigit():
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

    def handle_sit(self):
        if self.player.is_sitting:
            self.log("你已經坐下了。")
            return
        
        self.player.is_sitting = True
        self.log("[green]你坐下來休息。體力恢復速度提升！[/]")

    def handle_stand(self):
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
                    # id,name,type,value,keyword,min_dmg,max_dmg,defense,slot,description,english_name,hands,accuracy
                    item_id = row['id']
                    name = row['name']
                    i_type = row['type']
                    value = row['value']
                    keyword = row['keyword']
                    slot = row['slot']
                    desc = row['description']
                    english_name = row.get('english_name', '')
                    
                    item = None
                    if i_type == 'weapon':
                        min_d = int(row.get('min_dmg', 0))
                        max_d = int(row.get('max_dmg', 0))
                        hands = int(row.get('hands', 1)) 
                        accuracy = int(row.get('accuracy', 100))
                        item = Weapon(name, desc, int(value), keyword, min_d, max_d, slot, english_name=english_name, hands=hands, accuracy=accuracy)
                    elif i_type == 'armor' or i_type == 'helm': 
                        defense = int(row.get('defense', 0))
                        item = Armor(name, desc, int(value), keyword, int(defense), slot, english_name=english_name)
                    else:
                        item = Item(name, desc, int(value), keyword, english_name=english_name)
                    
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
                    
                    enemy = Enemy(
                        row['name'],
                        row['description'],
                        int(row['hp']),
                        (int(row['min_dmg']), int(row['max_dmg'])),
                        int(row['xp']),
                        int(row['gold']),
                        loot,
                        id=row['id'],
                        respawn_time=int(row.get('respawn_time', 30)),
                        enemy_type=row.get('type', 'beast')
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
                    
                    room = Room(row['name'], row['description'], symbol)
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
                        dist = abs(room.y)
                        # Chance: 1% per step. Max 80%?
                        chance = min(0.8, dist * 0.01)
                        dist_x = abs(room.x)
                        chance += min(0.2, dist_x * 0.01) # also X
                        
                        # Apply to all enemies in room (even if multiple)
                        for e in room.enemies:
                            # If not already aggressive (default False)
                            # Add base chance if we had "base_aggro" in Enemy class, but for now just depth
                            e.aggro_chance = chance 
                            
                            # Optional: Bosses always aggressive?
                            if e.proto_id and e.proto_id.startswith('boss_'):
                                e.aggro_chance = 1.0
                        else:
                            # Bosses don't mutate (already strong)
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
                            room.shop = Shop(f"{row['name']} Shop", "A local shop.", shop_items)

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
