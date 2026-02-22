# Project Task List

## Current Objectives (Strategic Combat & Town Services)
- [ ] **Advanced Combat & Action Logic**
    - [ ] `blind` skill: 2-3 turns duration; disables "Snatch" and lowers accuracy.
    - [ ] `kick` skill: Damage + Knockdown chance; increases success rate of next "Disarm".
    - [ ] `stand` command: Required for players to recover from Knockdown; NPCs auto-stand after 2 turns.
    - [ ] "Snatch" Window: Logic for players/NPCs to grab items from the room floor using Agility checks.
- [ ] **Equipment & Durability System**
    - [ ] Update `items.csv`: Add `durability`, `max_durability`, `rarity`, `set_id`, and `is_unique`.
    - [ ] Implement Item Destruction: Gear is removed and stats drop when durability reaches 0.
    - [ ] Boss Inventory: Stolen player items are stored in the Boss's persistent data for future recovery.
- [ ] **Town Services (Village Center)**
    - [ ] Gacha System: Weighted loot table for Blue+ items and Unique gear.
    - [ ] Reforge System: Randomize item affixes with an optional "Lock" cost for specific stats.
- [ ] **Stealth & Intel**
    - [ ] `sneak` status: Move without triggering aggro.
    - [ ] `scan` (sc) update: List Boss/Elite gear and bag contents first while in stealth.

## Pending Tasks
- [ ] **Unique & Affix Logic**
    - [ ] Global UID tracker: Prevent duplicate "Server-Unique" items (e.g., Elven Longsword).
    - [ ] Affix Generator: Physical/magic dmg modifiers based on rarity.
    - [ ] Set Bonus Logic: Check for matching `set_id` and apply extra attributes.
- [ ] **Data & Balancing**
    - [ ] `skills.csv` expansion: Add Disarm/Sunder/Blind effect modifiers.
    - [ ] Protection logic: Use Luck and Dexterity to reduce the chance of being disarmed.
- [ ] **System**
    - [ ] GUI Development: Real-time notification when an item is dropped or broken.
