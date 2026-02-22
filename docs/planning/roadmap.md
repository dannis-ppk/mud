# Product Roadmap

This document outlines the high-level goals and future direction for "The Ages" MUD project.

## Phase 1: Core Mechanics Refinement (Current)
Focus on stabilizing the base game loop, data integrity, and strategic combat depth.
- [x] Excel-compatible data editing (CSV with BOM)
- [x] Basic Combat & Stat systems
- [ ] **Equipment Core**: Implementation of slots (Weapon, Armor, Accessory) and Durability (耐久度) system.
- [ ] **Strategic Combat**: 
    - Disarm (打落), Sunder (破甲), and Snatch (搶奪) mechanics.
    - Status effects: Blind (致盲) and Knockdown (擊倒/站立機制).
- [ ] **Save/Load & Persistence**: Character data and Boss-class inventory persistence (stolen gear tracking).

## Phase 2: Content Expansion
Expanding the world and variety of gameplay with high-risk, high-reward systems.
- **Elite & Boss Variety**: Introduction of Variant, Elite, and Boss-class enemies with "Easter Egg" bags.
- **The Loot Ecosystem**: Unique/World-drop items (Unique Purple Gear) with global uniqueness tracking.
- **Town Services**: Gacha (抽獎) and Reforge (重洗詞綴) mechanics in the Village Center.
- **Tactical Stealth**: Sneak-based scanning (sc) for priority targets and enemy bag inspection.

## Phase 3: Technical Enhancements
- **Multiplayer/Network Support**: Crucial for real-time "Snatch" windows and command competition.
- **Scripting Engine**: Advanced AI for NPCs to prioritize picking up dropped gear or using recovery skills.
- **GUI Companion App**: Visual indicators for equipment durability and rarity glows.

## Phase 4: Polish & Release
- **Tutorial**: Interactive guide covering Disarm, Stand, and Repair mechanics.
- **Balancing**: Fine-tuning drop rates, affix weights, and luck-based protection.
- **Packaging**: Create executable builds.
