from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from api.models import (
    RegisterRequest, RegisterResponse,
    VerifyRequest, VerifyResponse,
    QuickVerifyRequest,
    UserListResponse, DeleteUserResponse, HealthResponse
)
from api.database import face_db
from api.face_service import face_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ = face_service
    yield


app = FastAPI(title="Face ID API", version="2.0.0", lifespan=lifespan)

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
        model_loaded=face_service.is_model_loaded(),
        registered_users=face_db.get_user_count()
    )


@app.post("/api/register", response_model=RegisterResponse)
async def register(req: RegisterRequest):
    """
    Register wajah baru - SINGLE REQUEST.
    Kirim 3-15 frames dari berbagai sudut wajah dalam 1 request.
    """
    if face_db.user_exists(req.user_id):
        return RegisterResponse(success=False, message=f"User '{req.user_id}' sudah terdaftar")

    embeddings = []
    faces_detected = 0

    for frame_b64 in req.frames_base64:
        result = face_service.process_base64(frame_b64, generate_embedding=True, check_blink=False)
        if result.face_detected:
            faces_detected += 1
            if result.embedding is not None:
                embeddings.append(result.embedding)

    if len(embeddings) < 3:
        return RegisterResponse(
            success=False,
            faces_detected=faces_detected,
            samples_saved=len(embeddings),
            message=f"Minimal 3 wajah terdeteksi. Hanya {len(embeddings)} berhasil."
        )

    avg = face_service.average_embeddings(embeddings)
    if avg is None:
        return RegisterResponse(success=False, message="Gagal generate embedding")

    face_db.save_embedding(req.user_id, avg, len(embeddings))

    return RegisterResponse(
        success=True,
        user_id=req.user_id,
        faces_detected=faces_detected,
        samples_saved=len(embeddings),
        message=f"Registrasi berhasil dengan {len(embeddings)} samples"
    )


@app.post("/api/verify", response_model=VerifyResponse)
async def verify(req: VerifyRequest):
    """
    Verifikasi wajah dengan liveness detection - SINGLE REQUEST.
    Kirim 3-10 frames, sistem akan cek kedipan mata + face match.
    """
    stored = face_db.get_embedding(req.user_id)
    if stored is None:
        return VerifyResponse(success=False, message=f"User '{req.user_id}' tidak ditemukan")

    face_service.reset_blink_detector()
    embeddings = []
    blink_detected = False
    faces_detected = 0

    for frame_b64 in req.frames_base64:
        result = face_service.process_base64(frame_b64, generate_embedding=True, check_blink=True)
        if result.face_detected:
            faces_detected += 1
            if result.embedding is not None:
                embeddings.append(result.embedding)
            if result.blink_result and result.blink_result.blink_count > 0:
                blink_detected = True

    if faces_detected == 0:
        return VerifyResponse(
            success=True, verified=False,
            faces_detected=0,
            message="Tidak ada wajah terdeteksi"
        )

    if not blink_detected:
        return VerifyResponse(
            success=True, verified=False,
            faces_detected=faces_detected,
            liveness_passed=False,
            message="Liveness gagal - tidak ada kedipan terdeteksi"
        )

    if not embeddings:
        return VerifyResponse(
            success=True, verified=False,
            faces_detected=faces_detected,
            liveness_passed=True,
            blink_detected=True,
            message="Gagal generate embedding"
        )

    avg = face_service.average_embeddings(embeddings)
    is_match, similarity = face_service.verify_face(avg, stored)

    return VerifyResponse(
        success=True,
        verified=is_match,
        user_id=req.user_id,
        similarity=round(similarity, 4),
        threshold=face_service.similarity_threshold,
        liveness_passed=True,
        blink_detected=True,
        faces_detected=faces_detected,
        message="Verifikasi berhasil" if is_match else "Wajah tidak cocok"
    )


@app.post("/api/verify/quick", response_model=VerifyResponse)
async def verify_quick(req: QuickVerifyRequest):
    """
    Quick verify - 1 frame, tanpa liveness.
    HANYA untuk testing, tidak aman untuk production.
    """
    stored = face_db.get_embedding(req.user_id)
    if stored is None:
        return VerifyResponse(success=False, message=f"User '{req.user_id}' tidak ditemukan")

    result = face_service.process_base64(req.frame_base64, generate_embedding=True, check_blink=False)

    if not result.face_detected:
        return VerifyResponse(success=True, verified=False, message="Wajah tidak terdeteksi")

    if result.embedding is None:
        return VerifyResponse(success=True, verified=False, faces_detected=1, message="Embedding gagal")

    is_match, similarity = face_service.verify_face(result.embedding, stored)

    return VerifyResponse(
        success=True,
        verified=is_match,
        user_id=req.user_id,
        similarity=round(similarity, 4),
        threshold=face_service.similarity_threshold,
        faces_detected=1,
        message="Match" if is_match else "Tidak cocok"
    )


@app.get("/api/users", response_model=UserListResponse)
async def list_users():
    users = face_db.get_all_users()
    return UserListResponse(success=True, users=users, total=len(users))


@app.delete("/api/users/{user_id}", response_model=DeleteUserResponse)
async def delete_user(user_id: str):
    if not face_db.user_exists(user_id):
        raise HTTPException(status_code=404, detail=f"User '{user_id}' tidak ditemukan")
    face_db.delete_user(user_id)
    return DeleteUserResponse(success=True, user_id=user_id, message="User dihapus")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
