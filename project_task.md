# Restoration of 'The Ages' (時空之門) MUD

## Research
- [x] Search for "時空之門" MUD 4444 and "The Ages" MUD on the web
- [x] Check PTT (Taiwan BBS) and other MUD communities for archives or discussions
- [x] Identify the MUD driver/library type (LPMud, DikuMUD, etc.) -> **MERC 2.0 (DikuMUD variant)**

## Findings
- **Status**: The original source code for "The Ages" is not publicly available.
- **Alternatives**: The "Eastern Stories 2" (ES2) codebase is a similar Chinese MERC-based MUD that is open source.
- **History**: The game was hosted at `.nthu.edu.tw` and later `mud.slzzp.net`.

## Prototype Phase (Python/Custom) - [Completed]
- [x] **Core Engine**: Simple command parser (look, move, help).
- [x] **Map System**: 
    - [x] Grid-based world (2D array or coordinate system).
    - [x] "Fog of War": Track visited coordinates.
    - [x] ASCII Map Renderer: Display a mini-map next to or above text.
- [x] **Content**: Create a small starting area ("The Nexus").

## Phase II: UI & Immersion - [Completed]
- [x] **Color Support**: Implement ANSI color codes.
- [x] **Status Line**: Constant display of HP, MP, MV, Time, Location, XP.
- [x] **Controls**: Bind Arrow Keys to movement (N/S/E/W).


## Phase III: Combat & Economy
- [ ] **Combat System**:
    - [ ] `Enemy` class with name formatting `中文(English)`.
    - [ ] `kill` command with RNG damage.
    - [ ] Loot system: Gold and rare item drops.
- [ ] **Economy**:
    - [ ] Shops: Weapon, Skill, and Potion stores.
    - [ ] Currency: Gold system.
- [ ] **Equipment (Simplified)**: Head, Body, L-Hand, R-Hand, L-Foot, R-Foot.






## Architecture & Technology
- [x] Decide on project location (Keep in playground vs. dedicated folder) -> **Start in Playground**
- [x] Choose technology stack:
    - **Selected**: Python (with focus on TUI/Console UI)

## Next Steps
- [ ] Create `mud_prototype.py`
- [ ] Implement `Map` class with exploration tracking



