import numpy as np
import cv2
import onnxruntime as ort
from dataclasses import dataclass
from typing import Optional, List, Dict
import os


@dataclass
class EmbeddingResult:
    success: bool
    embedding: Optional[np.ndarray] = None
    error_message: Optional[str] = None


@dataclass
class VerificationResult:
    verified: bool
    similarity: float
    threshold: float
    liveness_passed: bool
    error_message: Optional[str] = None


ARCFACE_DST = np.array([
    [38.2946, 51.6963], [73.5318, 51.5014], [56.0252, 71.7366],
    [41.5493, 92.3655], [70.7299, 92.2041]
], dtype=np.float32)


def estimate_affine(src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    num = src.shape[0]
    src_pad = np.hstack([src, np.ones((num, 1))])
    M, _, _, _ = np.linalg.lstsq(src_pad, dst, rcond=None)
    return M.T


def align_face(frame: np.ndarray, landmarks: np.ndarray) -> Optional[np.ndarray]:
    try:
        left_eye = landmarks[[33, 133]].mean(axis=0)
        right_eye = landmarks[[362, 263]].mean(axis=0)
        src_pts = np.array([
            left_eye, right_eye, landmarks[1], landmarks[61], landmarks[291]
        ], dtype=np.float32)
        M = estimate_affine(src_pts, ARCFACE_DST)
        return cv2.warpAffine(frame, M, (112, 112), borderValue=0)
    except:
        return None


class FaceEmbedding:
    def __init__(self, model_path: str = "buffalo_sc/w600k_mbf.onnx"):
        self.model_path = model_path
        self._session = None
        self._initialized = False
        self._input_name = None

    def _init_model(self) -> bool:
        if self._initialized:
            return True

        paths = [self.model_path, "buffalo_sc/w600k_mbf.onnx", "w600k_mbf.onnx", "arcface_model.onnx"]
        model_path = next((p for p in paths if os.path.exists(p)), None)

        if not model_path:
            return False

        try:
            self._session = ort.InferenceSession(model_path, providers=['CPUExecutionProvider'])
            self._input_name = self._session.get_inputs()[0].name
            self._initialized = True
            return True
        except:
            return False

    def preprocess(self, face: np.ndarray) -> np.ndarray:
        img = cv2.cvtColor(face, cv2.COLOR_BGR2RGB)
        img = (img.astype(np.float32) - 127.5) / 127.5
        return np.expand_dims(np.transpose(img, (2, 0, 1)), axis=0)

    def generate_embedding(self, frame: np.ndarray, landmarks: np.ndarray) -> EmbeddingResult:
        if not self._init_model():
            return EmbeddingResult(success=False, error_message="Model not loaded")

        if landmarks is None or len(landmarks) < 468:
            return EmbeddingResult(success=False, error_message="Invalid landmarks")

        try:
            aligned = align_face(frame, landmarks)
            if aligned is None:
                return EmbeddingResult(success=False, error_message="Alignment failed")

            output = self._session.run(None, {self._input_name: self.preprocess(aligned)})
            emb = output[0][0]
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            return EmbeddingResult(success=True, embedding=emb)
        except Exception as e:
            return EmbeddingResult(success=False, error_message=str(e))

    @staticmethod
    def calculate_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        if emb1 is None or emb2 is None or len(emb1) != len(emb2):
            return 0.0
        dot = np.dot(emb1, emb2)
        return float(np.clip(dot / (np.linalg.norm(emb1) * np.linalg.norm(emb2) + 1e-10), 0.0, 1.0))

    @staticmethod
    def average_embeddings(embeddings: List[np.ndarray]) -> Optional[np.ndarray]:
        if not embeddings:
            return None
        avg = np.mean(embeddings, axis=0)
        return avg / (np.linalg.norm(avg) + 1e-10)


class IdentityStore:
    def __init__(self, similarity_threshold: float = 0.35):
        self.similarity_threshold = similarity_threshold
        self._identities: Dict[str, np.ndarray] = {}

    def enroll(self, identity_id: str, embeddings: List[np.ndarray]) -> bool:
        if not embeddings:
            return False
        self._identities[identity_id] = FaceEmbedding.average_embeddings(embeddings)
        return True

    def verify(self, identity_id: str, embedding: np.ndarray, liveness_passed: bool) -> VerificationResult:
        if identity_id not in self._identities:
            return VerificationResult(False, 0.0, self.similarity_threshold, liveness_passed,
                                      f"Identity '{identity_id}' not found")
        similarity = FaceEmbedding.calculate_similarity(embedding, self._identities[identity_id])
        verified = (similarity >= self.similarity_threshold) and liveness_passed
        return VerificationResult(verified, similarity, self.similarity_threshold, liveness_passed)

    def get_identity_ids(self) -> List[str]:
        return list(self._identities.keys())

    def remove_identity(self, identity_id: str) -> bool:
        if identity_id in self._identities:
            del self._identities[identity_id]
            return True
        return False
