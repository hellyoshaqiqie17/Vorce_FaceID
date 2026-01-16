from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.models import (
    RegisterStartRequest, RegisterStartResponse,
    RegisterFrameRequest, RegisterFrameResponse,
    RegisterCompleteRequest, RegisterCompleteResponse,
    VerifyRequest, VerifyResponse,
    VerifySingleFrameRequest, LivenessCheckResponse,
    UserListResponse, DeleteUserResponse, HealthResponse,
    RegisterStep, LivenessStatus
)
from api.session_manager import session_manager
from api.database import face_db
from api.face_service import face_service


STEP_INSTRUCTIONS = {
    RegisterStep.FRONT: "Posisikan wajah menghadap ke DEPAN",
    RegisterStep.LEFT: "Putar wajah sedikit ke KIRI",
    RegisterStep.RIGHT: "Putar wajah sedikit ke KANAN",
    RegisterStep.COMPLETE: "Registrasi selesai!"
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = face_service
    yield


app = FastAPI(title="Face ID API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", model_loaded=face_service.is_model_loaded())


@app.post("/api/face/register/start", response_model=RegisterStartResponse)
async def register_start(req: RegisterStartRequest):
    if face_db.user_exists(req.user_id):
        return RegisterStartResponse(success=False, message=f"User '{req.user_id}' already exists")

    session = session_manager.create_session(req.user_id)
    return RegisterStartResponse(
        success=True,
        session_id=session.session_id,
        current_step=RegisterStep.FRONT,
        instruction=STEP_INSTRUCTIONS[RegisterStep.FRONT],
        message="Session started"
    )


@app.post("/api/face/register/frame", response_model=RegisterFrameResponse)
async def register_frame(req: RegisterFrameRequest):
    session = session_manager.get_session(req.session_id)
    if not session:
        return RegisterFrameResponse(success=False, message="Session not found or expired")

    if session.is_complete:
        return RegisterFrameResponse(success=False, message="Session complete. Call /register/complete")

    result = face_service.process_base64(req.frame_base64, generate_embedding=True, check_blink=False)

    if not result.success or not result.face_detected:
        return RegisterFrameResponse(
            success=True,
            face_detected=False,
            samples_collected=session.get_current_step_progress(),
            samples_required=session.SAMPLES_PER_STEP,
            current_step=session.current_step,
            instruction=STEP_INSTRUCTIONS[session.current_step],
            progress=session.get_progress(),
            message=result.error_message or "No face detected"
        )

    if result.embedding is not None:
        session.add_embedding(result.embedding)

    next_step = None
    if session.is_step_complete():
        next_step = session.advance_step()

    return RegisterFrameResponse(
        success=True,
        face_detected=True,
        samples_collected=session.get_current_step_progress(),
        samples_required=session.SAMPLES_PER_STEP,
        current_step=session.current_step,
        next_step=next_step,
        instruction=STEP_INSTRUCTIONS.get(session.current_step, ""),
        progress=session.get_progress(),
        message="Complete" if session.is_complete else "Frame processed"
    )


@app.post("/api/face/register/complete", response_model=RegisterCompleteResponse)
async def register_complete(req: RegisterCompleteRequest):
    session = session_manager.get_session(req.session_id)
    if not session:
        return RegisterCompleteResponse(success=False, message="Session not found")

    if not session.is_complete:
        return RegisterCompleteResponse(success=False, message=f"Not complete. Step: {session.current_step.value}")

    if len(session.embeddings) < 5:
        session_manager.remove_session(req.session_id)
        return RegisterCompleteResponse(success=False, message=f"Not enough samples ({len(session.embeddings)})")

    avg = face_service.average_embeddings(session.embeddings)
    if avg is None:
        session_manager.remove_session(req.session_id)
        return RegisterCompleteResponse(success=False, message="Failed to generate embedding")

    face_db.save_embedding(session.user_id, avg, len(session.embeddings))
    session_manager.remove_session(req.session_id)

    return RegisterCompleteResponse(
        success=True,
        user_id=session.user_id,
        total_samples=len(session.embeddings),
        message=f"User '{session.user_id}' registered"
    )


@app.post("/api/face/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest):
    stored = face_db.get_embedding(req.user_id)
    if stored is None:
        return VerifyResponse(success=False, message=f"User '{req.user_id}' not found")

    face_service.reset_blink_detector()
    embeddings = []
    blink_detected = False
    face_count = 0

    for frame_b64 in req.frames_base64:
        result = face_service.process_base64(frame_b64, generate_embedding=True, check_blink=True)
        if result.face_detected:
            face_count += 1
            if result.embedding is not None:
                embeddings.append(result.embedding)
            if result.blink_result and result.blink_result.blink_count > 0:
                blink_detected = True

    if face_count == 0:
        return VerifyResponse(success=True, verified=False, face_detected=False, message="No face detected")

    if not blink_detected:
        return VerifyResponse(success=True, verified=False, face_detected=True, liveness_passed=False, message="No blink detected")

    if not embeddings:
        return VerifyResponse(success=True, verified=False, face_detected=True, liveness_passed=True, blink_detected=True, message="Embedding failed")

    avg = face_service.average_embeddings(embeddings)
    is_match, similarity = face_service.verify_face(avg, stored)

    return VerifyResponse(
        success=True,
        verified=is_match,
        user_id=req.user_id,
        similarity=similarity,
        threshold=face_service.similarity_threshold,
        liveness_passed=True,
        blink_detected=True,
        face_detected=True,
        message="Verified" if is_match else "Face mismatch"
    )


@app.post("/api/face/verify/single", response_model=VerifyResponse)
async def verify_single(req: VerifySingleFrameRequest):
    stored = face_db.get_embedding(req.user_id)
    if stored is None:
        return VerifyResponse(success=False, message=f"User '{req.user_id}' not found")

    result = face_service.process_base64(req.frame_base64, generate_embedding=True, check_blink=False)

    if not result.face_detected:
        return VerifyResponse(success=True, verified=False, face_detected=False, message="No face detected")

    if result.embedding is None:
        return VerifyResponse(success=True, verified=False, face_detected=True, message="Embedding failed")

    is_match, similarity = face_service.verify_face(result.embedding, stored)

    return VerifyResponse(
        success=True,
        verified=is_match,
        user_id=req.user_id,
        similarity=similarity,
        threshold=face_service.similarity_threshold,
        face_detected=True,
        message="Match" if is_match else "No match"
    )


@app.post("/api/face/liveness", response_model=LivenessCheckResponse)
async def liveness(req: VerifySingleFrameRequest):
    result = face_service.process_base64(req.frame_base64, generate_embedding=False, check_blink=True)

    if not result.face_detected:
        return LivenessCheckResponse(success=True, face_detected=False, liveness_status=LivenessStatus.NO_FACE)

    blink = result.blink_result
    status = LivenessStatus.WAITING_BLINK
    if blink:
        if blink.blink_count > 0:
            status = LivenessStatus.BLINK_DETECTED
        elif blink.is_blinking:
            status = LivenessStatus.EYES_CLOSED

    return LivenessCheckResponse(
        success=True,
        face_detected=True,
        blink_count=blink.blink_count if blink else 0,
        ear_value=blink.ear_avg if blink else 0,
        liveness_status=status,
        message="Blink detected" if status == LivenessStatus.BLINK_DETECTED else "Waiting"
    )


@app.get("/api/users", response_model=UserListResponse)
async def list_users():
    users = face_db.get_all_users()
    return UserListResponse(success=True, users=users, total=len(users))


@app.delete("/api/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(user_id: str):
    if not face_db.user_exists(user_id):
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found")
    face_db.delete_user(user_id)
    return DeleteUserResponse(success=True, user_id=user_id, message="Deleted")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
