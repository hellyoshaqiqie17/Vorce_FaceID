from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class LivenessRequest(BaseModel):
    frames: Dict[str, any] = Field(..., description="Frames untuk setiap pose")
    
    class Config:
        json_schema_extra = {
            "example": {
                "frames": {
                    "right": "base64_image_string",
                    "left": "base64_image_string",
                    "up": "base64_image_string",
                    "down": "base64_image_string",
                    "center": "base64_image_string",
                    "blink": ["base64_1", "base64_2", "base64_3"]
                }
            }
        }


class PoseCheck(BaseModel):
    detected: bool
    expected: str
    actual: str
    confidence: float


class LivenessResponse(BaseModel):
    success: bool
    is_real: bool = False
    confidence: float = 0.0
    checks: Dict[str, any] = {}
    message: str = ""
    details: Optional[Dict[str, any]] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    model_loaded: bool = False
    service: str = "liveness-detection"
