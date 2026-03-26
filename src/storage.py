import json
import os
from pathlib import Path
from typing import List, Dict, Any
from .models import ActionDefinition, SequenceItem


class StorageManager:
    ACTIONS_FILE = "/home/maic/10-robotgui/data/actions_library.json"
    TASKS_DIR = "/home/maic/10-robotgui/data/tasks"

    @classmethod
    def ensure_directories(cls):
        Path(cls.ACTIONS_FILE).parent.mkdir(parents=True, exist_ok=True)
        Path(cls.TASKS_DIR).mkdir(parents=True, exist_ok=True)

    @classmethod
    def save_actions(cls, actions: List[ActionDefinition]):
        cls.ensure_directories()
        data = [action.to_dict() for action in actions]
        with open(cls.ACTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_actions(cls) -> List[ActionDefinition]:
        if not os.path.exists(cls.ACTIONS_FILE):
            return []
        with open(cls.ACTIONS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [ActionDefinition.from_dict(item) for item in data]

    @classmethod
    def save_sequence(cls, items: List[SequenceItem], filename: str):
        cls.ensure_directories()
        filepath = os.path.join(cls.TASKS_DIR, filename)
        if not filepath.endswith('.task'):
            filepath += '.task'
        data = [item.to_dict() for item in items]
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_sequence(cls, filename: str) -> List[SequenceItem]:
        filepath = os.path.join(cls.TASKS_DIR, filename)
        if not filepath.endswith('.task'):
            filepath += '.task'
        if not os.path.exists(filepath):
            return []
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return [SequenceItem.from_dict(item) for item in data]

    @classmethod
    def list_tasks(cls) -> List[str]:
        if not os.path.exists(cls.TASKS_DIR):
            return []
        return [f for f in os.listdir(cls.TASKS_DIR) if f.endswith('.task')]
