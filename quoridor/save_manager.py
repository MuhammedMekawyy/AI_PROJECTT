"""
quoridor/save_manager.py
Save / load game state to JSON files. Supports 3 save slots.
"""
from __future__ import annotations
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from quoridor.game import GameState

SAVE_DIR = os.path.join(os.path.dirname(__file__), '..', 'saves')
NUM_SLOTS = 3


def _slot_path(slot: int) -> str:
    os.makedirs(SAVE_DIR, exist_ok=True)
    return os.path.join(SAVE_DIR, f'save_slot_{slot}.json')


def save_game(state: GameState, slot: int, meta: Optional[Dict] = None) -> bool:
    """Serialize state + metadata to JSON. Returns True on success."""
    try:
        data = {
            'saved_at': datetime.now().isoformat(timespec='seconds'),
            'num_players': state.num_players,
            'move_count': state.move_count,
            'meta': meta or {},
            'state': state.serialize()
        }
        with open(_slot_path(slot), 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f'[SaveManager] Error saving slot {slot}: {e}')
        return False


def load_game(slot: int) -> Optional[GameState]:
    """Load and deserialize state from JSON. Returns None if slot empty/corrupt."""
    path = _slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return GameState.deserialize(data['state'])
    except Exception as e:
        print(f'[SaveManager] Error loading slot {slot}: {e}')
        return None


def slot_info(slot: int) -> Optional[Dict[str, Any]]:
    """Return metadata dict for a slot, or None if empty."""
    path = _slot_path(slot)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            data = json.load(f)
        return {
            'saved_at': data.get('saved_at', '?'),
            'num_players': data.get('num_players', 2),
            'move_count': data.get('move_count', 0),
            'meta': data.get('meta', {})
        }
    except Exception:
        return None


def delete_slot(slot: int) -> bool:
    path = _slot_path(slot)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False


def all_slots() -> Dict[int, Optional[Dict]]:
    return {i: slot_info(i) for i in range(NUM_SLOTS)}
