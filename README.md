# Face ID API

Face Recognition dengan Liveness Detection (Blink) untuk aplikasi HR/Employee Management.

## Base URL

```
https://vorce-faceid-544676101248.europe-west1.run.app
```

## Endpoints

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok",
  "model_loaded": true,
  "registered_users": 5
}
```

---

### Register (Daftar Wajah)

```
POST /api/register
Content-Type: application/json
```

Request:
```json
{
  "user_id": "EMP001",
  "frames_base64": [
    "base64_image_1...",
    "base64_image_2...",
    "base64_image_3..."
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | ID unik user |
| frames_base64 | array | Yes | 3-15 gambar base64 dari berbagai sudut |

Response:
```json
{
  "success": true,
  "user_id": "EMP001",
  "faces_detected": 10,
  "samples_saved": 10,
  "message": "Registrasi berhasil dengan 10 samples"
}
```

---

### Verify (Login dengan Liveness)

```
POST /api/verify
Content-Type: application/json
```

Request:
```json
{
  "user_id": "EMP001",
  "frames_base64": [
    "base64_image_1...",
    "base64_image_2...",
    "base64_image_3..."
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| user_id | string | Yes | ID user yang akan diverifikasi |
| frames_base64 | array | Yes | 3-10 gambar base64 (harus ada kedipan mata) |

Response (Success):
```json
{
  "success": true,
  "verified": true,
  "user_id": "EMP001",
  "similarity": 0.85,
  "threshold": 0.4,
  "liveness_passed": true,
  "blink_detected": true,
  "faces_detected": 8,
  "message": "Verifikasi berhasil"
}
```

Response (Failed - Face Mismatch):
```json
{
  "success": true,
  "verified": false,
  "similarity": 0.25,
  "threshold": 0.4,
  "liveness_passed": true,
  "blink_detected": true,
  "message": "Wajah tidak cocok"
}
```

Response (Failed - No Blink):
```json
{
  "success": true,
  "verified": false,
  "liveness_passed": false,
  "blink_detected": false,
  "message": "Liveness gagal - tidak ada kedipan terdeteksi"
}
```

---

### Quick Verify (Tanpa Liveness)

```
POST /api/verify/quick
Content-Type: application/json
```

Request:
```json
{
  "user_id": "EMP001",
  "frame_base64": "base64_image..."
}
```

> ⚠️ Hanya untuk testing. Tidak aman untuk production karena tidak ada liveness check.

---

### List Users

```
GET /api/users
```

Response:
```json
{
  "success": true,
  "users": ["EMP001", "EMP002", "EMP003"],
  "total": 3
}
```

---

### Delete User

```
DELETE /api/users/{user_id}
```

Response:
```json
{
  "success": true,
  "user_id": "EMP001",
  "message": "User dihapus"
}
```

---

## Cara Convert Gambar ke Base64

### JavaScript
```javascript
const toBase64 = (file) => new Promise((resolve, reject) => {
  const reader = new FileReader();
  reader.readAsDataURL(file);
  reader.onload = () => resolve(reader.result.split(',')[1]);
  reader.onerror = reject;
});
```

### Python
```python
import base64

with open("image.jpg", "rb") as f:
    base64_str = base64.b64encode(f.read()).decode()
```

### Flutter/Dart
```dart
import 'dart:convert';
import 'dart:io';

String toBase64(File file) {
  return base64Encode(file.readAsBytesSync());
}
```

---

## Flow Integrasi

### Register Flow
1. Capture 5-15 frame wajah dari berbagai sudut (depan, kiri, kanan)
2. Convert semua frame ke base64
3. Kirim ke `POST /api/register`
4. Simpan user_id untuk login nanti

### Login Flow
1. Capture 5-10 frame wajah
2. Instruksikan user untuk kedip 1x
3. Convert semua frame ke base64
4. Kirim ke `POST /api/verify`
5. Cek response `verified: true`

---

## Error Codes

| Code | Message | Solution |
|------|---------|----------|
| 200 | success: false | Cek field `message` untuk detail |
| 404 | User not found | User belum terdaftar |
| 403 | Forbidden | API belum di-set allow unauthenticated |
| 500 | Internal error | Cek logs di Cloud Run |

---

## Security Notes

- Foto statis tidak bisa lolos (tidak ada kedipan)
- Video replay sulit lolos (timing kedipan berbeda)
- Wajah berbeda akan ditolak (similarity < threshold)
- Threshold default: 0.4 (40% similarity)
