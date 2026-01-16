import json
import os
import numpy as np
from typing import Dict, List, Optional
from threading import Lock
from datetime import datetime


class FaceDatabase:
    def __init__(self, db_path: str = "face_database.json"):
        self.db_path = db_path
        self._lock = Lock()
        self._data: Dict[str, dict] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r') as f:
                    raw = json.load(f)
                    self._data = {
                        uid: {
                            'embedding': np.array(d['embedding']),
                            'created_at': d.get('created_at', ''),
                            'samples_count': d.get('samples_count', 0)
                        }
                        for uid, d in raw.items()
                    }
            except:
                self._data = {}

    def _save(self):
        try:
            raw = {
                uid: {
                    'embedding': d['embedding'].tolist(),
                    'created_at': d.get('created_at', ''),
                    'samples_count': d.get('samples_count', 0)
                }
                for uid, d in self._data.items()
            }
            with open(self.db_path, 'w') as f:
                json.dump(raw, f)
        except:
            pass

    def save_embedding(self, user_id: str, embedding: np.ndarray, samples_count: int = 0) -> bool:
        with self._lock:
            self._data[user_id] = {
                'embedding': embedding,
                'created_at': datetime.now().isoformat(),
                'samples_count': samples_count
            }
            self._save()
            return True

    def get_embedding(self, user_id: str) -> Optional[np.ndarray]:
        with self._lock:
            return self._data[user_id]['embedding'] if user_id in self._data else None

    def user_exists(self, user_id: str) -> bool:
        return user_id in self._data

    def delete_user(self, user_id: str) -> bool:
        with self._lock:
            if user_id in self._data:
                del self._data[user_id]
                self._save()
                return True
            return False

    def get_all_users(self) -> List[str]:
        return list(self._data.keys())

    def get_user_count(self) -> int:
        return len(self._data)


face_db = FaceDatabase()
