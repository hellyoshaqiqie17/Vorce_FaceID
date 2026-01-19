import os
import json
import numpy as np
from typing import Dict, List, Optional
from threading import Lock
from datetime import datetime


USE_FIREBASE = os.getenv("USE_FIREBASE", "false").lower() == "true"
COLLECTION_NAME = "face_embeddings"

if USE_FIREBASE:
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        
        if not firebase_admin._apps:
            cred_json = os.getenv("FIREBASE_CREDENTIALS")
            if cred_json:
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                print("✅ Using Firebase with JSON credentials")
            else:
                firebase_admin.initialize_app()
                print("✅ Using Firebase with Application Default Credentials (Service Account)")
        
        db = firestore.client()
        FIREBASE_AVAILABLE = True
        print(f"✅ Firebase initialized - Collection: {COLLECTION_NAME}")
    except Exception as e:
        print(f"❌ Firebase init failed: {e}")
        FIREBASE_AVAILABLE = False
        USE_FIREBASE = False
else:
    FIREBASE_AVAILABLE = False


class FaceDatabase:
    def __init__(self, db_path: str = "face_data.json"):
        self.db_path = db_path
        self._lock = Lock()
        self._data: Dict[str, dict] = {}
        self.use_firebase = USE_FIREBASE and FIREBASE_AVAILABLE
        
        if self.use_firebase:
            print(f"✅ Using Firebase Firestore (Collection: {COLLECTION_NAME})")
            self.collection = db.collection(COLLECTION_NAME)
        else:
            print("⚠️ Using local JSON storage (data will be lost on redeploy)")
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
        if self.use_firebase:
            try:
                now = datetime.now().isoformat()
                doc_data = {
                    'user_id': user_id,
                    'embedding': embedding.tolist(),
                    'created_at': now,
                    'updated_at': now,
                    'samples_count': samples_count
                }
                self.collection.document(user_id).set(doc_data)
                print(f"✅ Saved to Firestore: {user_id}")
                return True
            except Exception as e:
                print(f"❌ Firebase save error: {e}")
                return False
        else:
            with self._lock:
                self._data[user_id] = {
                    'embedding': embedding,
                    'created_at': datetime.now().isoformat(),
                    'samples_count': samples_count
                }
                self._save()
                return True

    def get_embedding(self, user_id: str) -> Optional[np.ndarray]:
        if self.use_firebase:
            try:
                doc = self.collection.document(user_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    return np.array(data['embedding'])
                return None
            except Exception as e:
                print(f"❌ Firebase get error: {e}")
                return None
        else:
            with self._lock:
                return self._data[user_id]['embedding'] if user_id in self._data else None

    def user_exists(self, user_id: str) -> bool:
        if self.use_firebase:
            try:
                doc = self.collection.document(user_id).get()
                return doc.exists
            except:
                return False
        else:
            return user_id in self._data

    def delete_user(self, user_id: str) -> bool:
        if self.use_firebase:
            try:
                self.collection.document(user_id).delete()
                print(f"✅ Deleted from Firestore: {user_id}")
                return True
            except Exception as e:
                print(f"❌ Firebase delete error: {e}")
                return False
        else:
            with self._lock:
                if user_id in self._data:
                    del self._data[user_id]
                    self._save()
                    return True
                return False

    def get_all_users(self) -> List[str]:
        if self.use_firebase:
            try:
                docs = self.collection.stream()
                return [doc.id for doc in docs]
            except Exception as e:
                print(f"❌ Firebase list error: {e}")
                return []
        else:
            return list(self._data.keys())

    def get_user_count(self) -> int:
        return len(self.get_all_users())


face_db = FaceDatabase()
