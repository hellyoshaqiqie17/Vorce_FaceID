import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional, Tuple


@dataclass
class HeadPose:
    yaw: float = 0.0
    pitch: float = 0.0
    direction: str = "center"


@dataclass
class FaceDetectionResult:
    detected: bool
    bbox: Optional[Tuple[int, int, int, int]] = None
    landmarks: Optional[np.ndarray] = None
    left_eye_landmarks: Optional[np.ndarray] = None
    right_eye_landmarks: Optional[np.ndarray] = None
    head_pose: Optional[HeadPose] = None
    face_count: int = 0
    error_message: Optional[str] = None


class FaceDetector:
    LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
    RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
    
    NOSE_TIP = 1
    CHIN = 152
    LEFT_EYE_CORNER = 263
    RIGHT_EYE_CORNER = 33

    def __init__(self, min_detection_confidence: float = 0.5, min_tracking_confidence: float = 0.5):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=2,
            refine_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )

    def estimate_head_pose(self, landmarks: np.ndarray, frame_shape: Tuple[int, int]) -> HeadPose:
        h, w = frame_shape
        
        nose = landmarks[self.NOSE_TIP]
        left_eye = landmarks[self.LEFT_EYE_CORNER]
        right_eye = landmarks[self.RIGHT_EYE_CORNER]
        chin = landmarks[self.CHIN]
        
        eye_center_x = (left_eye[0] + right_eye[0]) / 2
        eye_width = abs(left_eye[0] - right_eye[0])
        
        if eye_width > 0:
            yaw = (nose[0] - eye_center_x) / eye_width * 100
        else:
            yaw = 0
            
        eye_center_y = (left_eye[1] + right_eye[1]) / 2
        face_height = abs(chin[1] - eye_center_y)
        
        if face_height > 0:
            pitch = (nose[1] - eye_center_y) / face_height * 100 - 50
        else:
            pitch = 0
        
        if yaw < -5:
            direction = "left"
        elif yaw > 5:
            direction = "right"
        else:
            direction = "center"
            
        return HeadPose(yaw=yaw, pitch=pitch, direction=direction)

    def detect(self, frame: np.ndarray) -> FaceDetectionResult:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w = frame.shape[:2]
        results = self.face_mesh.process(rgb)

        if not results.multi_face_landmarks:
            return FaceDetectionResult(detected=False, face_count=0, error_message="No face detected")

        face_count = len(results.multi_face_landmarks)
        if face_count > 1:
            return FaceDetectionResult(detected=False, face_count=face_count,
                                       error_message=f"Multiple faces detected ({face_count})")

        face_landmarks = results.multi_face_landmarks[0]
        landmarks = np.array([[lm.x * w, lm.y * h] for lm in face_landmarks.landmark])

        left_eye = landmarks[self.LEFT_EYE_IDX]
        right_eye = landmarks[self.RIGHT_EYE_IDX]

        x_min, x_max = int(landmarks[:, 0].min()), int(landmarks[:, 0].max())
        y_min, y_max = int(landmarks[:, 1].min()), int(landmarks[:, 1].max())
        pad = 20
        bbox = (max(0, x_min - pad), max(0, y_min - pad), x_max - x_min + 2 * pad, y_max - y_min + 2 * pad)
        
        head_pose = self.estimate_head_pose(landmarks, (h, w))

        return FaceDetectionResult(
            detected=True, bbox=bbox, landmarks=landmarks,
            left_eye_landmarks=left_eye, right_eye_landmarks=right_eye, 
            head_pose=head_pose, face_count=1
        )

    def draw_landmarks(self, frame: np.ndarray, result: FaceDetectionResult) -> np.ndarray:
        output = frame.copy()
        if not result.detected:
            return output

        if result.bbox:
            x, y, w, h = result.bbox
            cv2.rectangle(output, (x, y), (x + w, y + h), (0, 255, 0), 2)

        if result.left_eye_landmarks is not None:
            for pt in result.left_eye_landmarks:
                cv2.circle(output, (int(pt[0]), int(pt[1])), 2, (255, 0, 0), -1)

        if result.right_eye_landmarks is not None:
            for pt in result.right_eye_landmarks:
                cv2.circle(output, (int(pt[0]), int(pt[1])), 2, (0, 0, 255), -1)

        return output
