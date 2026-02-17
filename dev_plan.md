# Implementation Plan: Phase III - Mechanics & Economy

## Goal
Implement the core gameplay loop: Move -> Fight -> Loot -> Trade -> Upgrade.

## User Review Required
- **Controls**: Switching to `msvcrt.getch()` (Windows) for instant arrow key response without pressing Enter.
- **Equipment Slots**: Head, Body, L-Hand, R-Hand, L-Foot, R-Foot.

## Proposed Changes

### [MODIFY] `mud_prototype.py`

#### **1. Input Handling (Arrow Keys)**
- Import `msvcrt`.
- Replace `input()` loop with a `getch()` loop.
- Map Arrow Keys (Up/Down/Left/Right) to `n`, `s`, `w`, `e`.
- Maintain `input()` for typing commands like `kill rabbit` or `buy sword`.

#### **2. Combat System**
- **`Enemy` Class**:
    - `name_zh`, `name_en` -> displayed as `小兔兔(rabbit)`.
    - `hp`, `damage`, `gold_drop`.
    - `loot_table`: List of potential items (low chance).
- **`kill` Command**:
    - Simple turn-based: Player hits -> Enemy hits.
    - Damage formula: Random range based on player strength/weapon.
    - Skill cost: Attacks consume MV (Stamina) or MP (Magic).

#### **3. Economy & Shops**
- **`Shop` Class**:
    - NPC that offers a menu: `list`, `buy <item>`.
    - **Weapon Shop**: Sells basic swords/daggers.
    - **Skill Shop**: Sells skill books (future use).
    - **Potion Shop**: Sells HP/MP recovery items.
- **Player Updates**:
    - `self.gold`: Track money.
    - `self.inventory`: List of `Item` objects.
    - `self.equipment`: Dictionary of slots.

## Verification Plan
### Manual Verification
1.  **Movement**: Run the game and use Arrow Keys. Player should move instantly on the map.
2.  **Combat**:
    - Type `k rabbit`.
    - Verify combat log shows damage numbers.
    - Kill rabbit -> Verify "You got X gold" message.
3.  **Shopping**:
    - Go to a shop room.
    - Type `list`. Valid menu appears.
    - Type `buy sword`. Gold decreases, sword appears in inventory.
