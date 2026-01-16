import numpy as np
from dataclasses import dataclass
from typing import Optional
from scipy.spatial import distance as dist
from enum import Enum


class LivenessStatus(Enum):
    NO_FACE = "no_face"
    WAITING_BLINK = "waiting_blink"
    BLINK_DETECTED = "blink_detected"
    EYES_CLOSED = "eyes_closed"


@dataclass
class BlinkDetectionResult:
    ear_left: float
    ear_right: float
    ear_avg: float
    is_blinking: bool
    blink_count: int
    liveness_status: LivenessStatus
    eyes_open: bool


class BlinkDetector:
    def __init__(self, ear_threshold: float = 0.21, consecutive_frames: int = 2, open_threshold: float = 0.25):
        self.ear_threshold = ear_threshold
        self.consecutive_frames = consecutive_frames
        self.open_threshold = open_threshold
        self._blink_count = 0
        self._frame_counter = 0
        self._was_closed = False
        self._liveness_status = LivenessStatus.WAITING_BLINK

    def reset(self):
        self._blink_count = 0
        self._frame_counter = 0
        self._was_closed = False
        self._liveness_status = LivenessStatus.WAITING_BLINK

    @staticmethod
    def calculate_ear(eye_landmarks: np.ndarray) -> float:
        v1 = dist.euclidean(eye_landmarks[1], eye_landmarks[5])
        v2 = dist.euclidean(eye_landmarks[2], eye_landmarks[4])
        h = dist.euclidean(eye_landmarks[0], eye_landmarks[3])
        return (v1 + v2) / (2.0 * h) if h != 0 else 0.0

    def detect(self, left_eye: Optional[np.ndarray], right_eye: Optional[np.ndarray]) -> BlinkDetectionResult:
        if left_eye is None or right_eye is None:
            self._liveness_status = LivenessStatus.NO_FACE
            return BlinkDetectionResult(0.0, 0.0, 0.0, False, self._blink_count, self._liveness_status, False)

        ear_left = self.calculate_ear(left_eye)
        ear_right = self.calculate_ear(right_eye)
        ear_avg = (ear_left + ear_right) / 2.0
        eyes_open = ear_avg >= self.open_threshold
        is_blinking = False

        if ear_avg < self.ear_threshold:
            self._frame_counter += 1
            self._liveness_status = LivenessStatus.EYES_CLOSED
            if self._frame_counter >= self.consecutive_frames:
                self._was_closed = True
        else:
            if self._was_closed:
                self._blink_count += 1
                is_blinking = True
                self._liveness_status = LivenessStatus.BLINK_DETECTED
            else:
                self._liveness_status = LivenessStatus.WAITING_BLINK
            self._frame_counter = 0
            self._was_closed = False

        return BlinkDetectionResult(ear_left, ear_right, ear_avg, is_blinking, self._blink_count, self._liveness_status, eyes_open)

    @property
    def blink_count(self) -> int:
        return self._blink_count
