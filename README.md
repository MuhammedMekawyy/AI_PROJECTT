# Quoridor — Strategy Board Game

A complete Python/Pygame implementation of **Quoridor**, developed for CSE472s: Artificial Intelligence, Spring 2026.

---

## Game Description

Quoridor is a 2–4 player abstract strategy game invented by Mirko Marchesi (1997), winner of the Mensa Mind Game award. Players race their pawn to the opposite side of a 9×9 board while placing walls to obstruct opponents. The tension between advancing your pawn and blocking your opponent creates rich tactical depth.

**Objective:** Be the first player to move your pawn to any cell on the opposite side of the board.

---

## Features

### Core
- Full 2-player Quoridor rule implementation
- Beautiful dark-themed Pygame GUI (900×700)
- Valid move highlighting (click pawn to see legal moves)
- Wall placement with real-time preview (green = valid, red = invalid)
- BFS pathfinding enforcement — walls that fully block a player are rejected
- Turn indicator, wall count display, winner announcement

### Game Modes
- **Human vs Human** — local two-player on the same machine
- **Human vs AI** — three difficulty levels

### AI Opponents
| Level  | Algorithm | Description |
|--------|-----------|-------------|
| Easy   | Random + bias | Mostly moves forward randomly; rarely places walls |
| Medium | Greedy 1-ply | Picks the action that maximises the BFS-distance heuristic |
| Hard   | Minimax depth-3 + Alpha-Beta pruning | Full game-tree search with move ordering |

### Bonus Features (all implemented)
- **Save / Load** — 3 save slots, JSON-based persistence (S key / L key)
- **Undo / Redo** — unlimited history stack (Z / Y keys)
- **4-Player Mode** — selectable from the main menu
- AI runs on a background thread (no UI freeze)

---

## Installation

### Requirements
- Python 3.10+
- Pygame 2.5+

### Setup

```bash
# 1. Clone or unzip the project
cd quoridor

# 2. Install pygame
pip install pygame

# 3. Run the game
python main.py
```

---

## Controls

| Key / Action | Function |
|---|---|
| Click pawn | Select pawn (shows valid moves) |
| Click highlighted cell | Move pawn to that cell |
| **W** | Toggle Wall placement mode |
| **R** | Rotate wall orientation (H ↔ V) |
| Hover in wall mode | Preview wall (green=OK, red=blocked) |
| Click in wall mode | Place wall |
| **Z** | Undo last move |
| **Y** | Redo |
| **S** | Save game (choose slot) |
| **L** | Load game (choose slot) |
| **F2** | New game / return to menu |
| **ESC** | Return to menu |

---

## Project Structure

```
quoridor/
├── main.py                  ← Entry point
├── requirements.txt
├── README.md
├── saves/                   ← Auto-created save files
├── tests/
│   └── test_game.py         ← 29 unit tests (run: python tests/test_game.py)
└── quoridor/
    ├── __init__.py
    ├── game.py              ← Core game logic, rules, BFS pathfinding
    ├── ai.py                ← AI engine (Easy/Medium/Hard)
    ├── renderer.py          ← Pygame drawing (board, walls, pawns, panels)
    ├── controller.py        ← Event handling, undo/redo, AI scheduling
    ├── menu.py              ← Main menu screen
    ├── dialogs.py           ← Save/load/confirm modal dialogs
    └── save_manager.py      ← JSON save/load with 3 slots
```

---

## Running Tests

```bash
python tests/test_game.py
# 29 tests covering: initial state, movement, wall placement,
# pathfinding, jump mechanics, serialization, AI correctness
```

---

## Demo Video

> *[https://drive.google.com/drive/folders/1EzMgCIHwXWhwmSWn55jlO1p-qErmc1KM?usp=drive_link]*

---

## References

- Official Quoridor Rules: https://en.gigamic.com/files/media/fiche_produit/educate-quoridor_pedagogical-sheet_en.pdf
- Quoridor on BoardGameGeek: https://boardgamegeek.com/boardgame/624/quoridor
- Minimax / Alpha-Beta: Russell & Norvig, *Artificial Intelligence: A Modern Approach*, Ch. 5
- BFS Pathfinding: Skiena, *The Algorithm Design Manual*
- Pygame documentation: https://www.pygame.org/docs/
