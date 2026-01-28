from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.models import LivenessRequest, LivenessResponse, HealthResponse
from api.liveness_service import liveness_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = liveness_service
    yield


app = FastAPI(
    title="Liveness Detection API",
    version="3.0.0",
    description="API untuk validasi wajah asli vs foto/video palsu",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        model_loaded=True,
        service="liveness-detection"
    )


@app.post("/api/liveness/validate", response_model=LivenessResponse)
async def validate_liveness(req: LivenessRequest):
    """
    Validasi apakah wajah asli atau palsu (foto/video).
    
    Flutter mengirim frames dari berbagai pose:
    - right: hadap kanan
    - left: hadap kiri
    - up: lihat atas
    - down: lihat bawah
    - center: lihat kamera
    - blink: array frames untuk deteksi kedipan
    
    Response:
    - is_real: true jika wajah asli, false jika palsu
    - confidence: 0.0 - 1.0
    - checks: detail validasi setiap step
    """
    try:
        result = liveness_service.validate_liveness(req.frames)
        
        message = "Wajah asli terdeteksi" if result.is_real else "Wajah palsu terdeteksi (foto/video)"
        
        return LivenessResponse(
            success=True,
            is_real=result.is_real,
            confidence=result.confidence,
            checks=result.checks,
            message=message,
            details=result.details
        )
    
    except Exception as e:
        return LivenessResponse(
            success=False,
            is_real=False,
            confidence=0.0,
            checks={},
            message=f"Error: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
