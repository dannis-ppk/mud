# MUD: The Age

A text-based MUD (Multi-User Dungeon) game built with Python and Rich.

## Features
- **Exploration**: Navigate through a world of connected rooms, forests, caves, and safe zones.
- **Combat**: Turn-based combat system with various enemies, skills, and magic.
- **Equipment**: detailed equipment system with Rarity tiers (Fine, Rare, Epic) and random stats.
- **Skills**: Physical and Magical skills learnable by leveling up (e.g., Fireball, Double Strike, Heal).
- **Persistence**: Save and Load game progress.
- **Map**: Dynamic ASCII mini-map with fog of war.

## Requirements
- Python 3.8+
- `rich` library

## Installation
1.  Clone this repository.
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

## How to Play
Run the game using Python:
```bash
python mud_main.py
```
Or double-click `start_mud_game.bat` on Windows.

### Controls
- **Arrow Keys**: Move (North, South, East, West)
- **PageUp/PageDown (or I/Q)**: Scroll Log History
- **Commands**: Type commands like `look`, `i` (inventory), `eq` (equipment), `stat`, `skill`, `help`.

## Project Structure
- `mud_main.py`: Main game entry point and core logic.
- `data/`: CSV files defining Items, Enemies, Rooms, Shops, and Skills.
- `saves/`: Save files (local only, ignored by git).
- `get_latest.bat`: Helper script to pull updates from GitHub.
- `save_updates.bat`: Helper script to commit and push changes to GitHub.
