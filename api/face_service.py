import base64
import cv2
import numpy as np
from typing import Optional, Tuple, List
from dataclasses import dataclass
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.face_detector import FaceDetector
from src.blink_detector import BlinkDetector, BlinkDetectionResult
from src.embedding import FaceEmbedding


@dataclass
class ProcessFrameResult:
    success: bool
    face_detected: bool = False
    embedding: Optional[np.ndarray] = None
    blink_result: Optional[BlinkDetectionResult] = None
    error_message: str = ""


class FaceService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.face_detector = FaceDetector()
        self.blink_detector = BlinkDetector()
        self.embedding_model = FaceEmbedding()
        self.similarity_threshold = 0.35
        self._initialized = True

    def decode_image(self, base64_str: str) -> Optional[np.ndarray]:
        try:
            if ',' in base64_str:
                base64_str = base64_str.split(',')[1]
            img_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        except:
            return None

    def process_frame(self, frame: np.ndarray, generate_embedding: bool = True, check_blink: bool = False) -> ProcessFrameResult:
        face_result = self.face_detector.detect(frame)

        if not face_result.detected:
            return ProcessFrameResult(success=True, face_detected=False,
                                      error_message=face_result.error_message or "No face detected")

        result = ProcessFrameResult(success=True, face_detected=True)

        if generate_embedding and face_result.landmarks is not None:
            emb_result = self.embedding_model.generate_embedding(frame, face_result.landmarks)
            if emb_result.success:
                result.embedding = emb_result.embedding
            else:
                result.error_message = emb_result.error_message or "Embedding failed"

        if check_blink:
            result.blink_result = self.blink_detector.detect(
                face_result.left_eye_landmarks, face_result.right_eye_landmarks)

        return result

    def process_base64(self, base64_str: str, generate_embedding: bool = True, check_blink: bool = False) -> ProcessFrameResult:
        frame = self.decode_image(base64_str)
        if frame is None:
            return ProcessFrameResult(success=False, error_message="Failed to decode image")
        return self.process_frame(frame, generate_embedding, check_blink)

    def verify_face(self, embedding: np.ndarray, stored_embedding: np.ndarray) -> Tuple[bool, float]:
        similarity = FaceEmbedding.calculate_similarity(embedding, stored_embedding)
        return similarity >= self.similarity_threshold, similarity

    def average_embeddings(self, embeddings: List[np.ndarray]) -> Optional[np.ndarray]:
        return FaceEmbedding.average_embeddings(embeddings)

    def reset_blink_detector(self):
        self.blink_detector.reset()

    def is_model_loaded(self) -> bool:
        return self.embedding_model._initialized


face_service = FaceService()
