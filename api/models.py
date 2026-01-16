from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class LivenessStatus(str, Enum):
    NO_FACE = "no_face"
    WAITING_BLINK = "waiting_blink"
    BLINK_DETECTED = "blink_detected"
    EYES_CLOSED = "eyes_closed"


# REGISTER - Single request with multiple frames (HEMAT REQUEST)
class RegisterRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    frames_base64: List[str] = Field(..., min_length=3, max_length=15,
        description="3-15 frames dari berbagai sudut wajah")


class RegisterResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    faces_detected: int = 0
    samples_saved: int = 0
    message: str = ""


# VERIFY - Single request with multiple frames
class VerifyRequest(BaseModel):
    user_id: str
    frames_base64: List[str] = Field(..., min_length=3, max_length=10,
        description="3-10 frames untuk verifikasi + liveness")


class VerifyResponse(BaseModel):
    success: bool
    verified: bool = False
    user_id: Optional[str] = None
    similarity: float = 0.0
    threshold: float = 0.4
    liveness_passed: bool = False
    blink_detected: bool = False
    faces_detected: int = 0
    message: str = ""


# QUICK VERIFY - Single frame, no liveness (untuk testing)
class QuickVerifyRequest(BaseModel):
    user_id: str
    frame_base64: str


# USER MANAGEMENT
class UserListResponse(BaseModel):
    success: bool
    users: List[str] = []
    total: int = 0


class DeleteUserResponse(BaseModel):
    success: bool
    user_id: str = ""
    message: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool = False
    registered_users: int = 0
