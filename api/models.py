from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class RegisterStep(str, Enum):
    FRONT = "front"
    LEFT = "left"
    RIGHT = "right"
    COMPLETE = "complete"


class LivenessStatus(str, Enum):
    NO_FACE = "no_face"
    WAITING_BLINK = "waiting_blink"
    BLINK_DETECTED = "blink_detected"
    EYES_CLOSED = "eyes_closed"


class RegisterStartRequest(BaseModel):
    user_id: str = Field(..., min_length=1)


class RegisterFrameRequest(BaseModel):
    session_id: str
    frame_base64: str


class RegisterCompleteRequest(BaseModel):
    session_id: str


class VerifyRequest(BaseModel):
    user_id: str
    frames_base64: List[str] = Field(..., min_length=1, max_length=10)


class VerifySingleFrameRequest(BaseModel):
    user_id: str
    frame_base64: str


class RegisterStartResponse(BaseModel):
    success: bool
    session_id: Optional[str] = None
    current_step: RegisterStep = RegisterStep.FRONT
    instruction: str = ""
    message: str = ""


class RegisterFrameResponse(BaseModel):
    success: bool
    face_detected: bool = False
    samples_collected: int = 0
    samples_required: int = 5
    current_step: RegisterStep = RegisterStep.FRONT
    next_step: Optional[RegisterStep] = None
    instruction: str = ""
    message: str = ""
    progress: float = 0.0


class RegisterCompleteResponse(BaseModel):
    success: bool
    user_id: Optional[str] = None
    total_samples: int = 0
    message: str = ""


class VerifyResponse(BaseModel):
    success: bool
    verified: bool = False
    user_id: Optional[str] = None
    similarity: float = 0.0
    threshold: float = 0.35
    liveness_passed: bool = False
    blink_detected: bool = False
    face_detected: bool = False
    message: str = ""


class LivenessCheckResponse(BaseModel):
    success: bool
    face_detected: bool = False
    blink_count: int = 0
    ear_value: float = 0.0
    liveness_status: LivenessStatus = LivenessStatus.NO_FACE
    message: str = ""


class UserListResponse(BaseModel):
    success: bool
    users: List[str] = []
    total: int = 0


class DeleteUserResponse(BaseModel):
    success: bool
    user_id: str
    message: str = ""


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool = False
    version: str = "1.0.0"
