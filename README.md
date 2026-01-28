# Liveness Detection API

API untuk validasi wajah asli vs foto/video palsu menggunakan head movement dan blink detection.

**Tujuan:** Mencegah spoofing attack dengan foto, video, atau deepfake.

## Base URL

```
https://vorce-faceid-544676101248.europe-west1.run.app
```

---

## Endpoint

### Health Check

```
GET /health
```

Response:
```json
{
  "status": "ok",
  "model_loaded": true,
  "service": "liveness-detection"
}
```

---

### Validate Liveness

```
POST /api/liveness/validate
Content-Type: application/json
```

**Request:**
```json
{
  "frames": {
    "right": "base64_image_hadap_kanan",
    "left": "base64_image_hadap_kiri",
    "up": "base64_image_lihat_atas",
    "down": "base64_image_lihat_bawah",
    "center": "base64_image_lihat_kamera",
    "blink": [
      "base64_frame_1",
      "base64_frame_2",
      "base64_frame_3"
    ]
  }
}
```

**Response (Wajah Asli):**
```json
{
  "success": true,
  "is_real": true,
  "confidence": 0.92,
  "message": "Wajah asli terdeteksi",
  "checks": {
    "pose_right": {
      "valid": true,
      "expected": "right",
      "actual": "right",
      "confidence": 0.95,
      "yaw": 25.3,
      "pitch": 5.2
    },
    "pose_left": {
      "valid": true,
      "expected": "left",
      "actual": "left",
      "confidence": 0.88,
      "yaw": -22.1,
      "pitch": 3.5
    },
    "pose_up": {
      "valid": true,
      "expected": "up",
      "actual": "up",
      "confidence": 0.91,
      "yaw": 2.1,
      "pitch": -15.3
    },
    "pose_down": {
      "valid": true,
      "expected": "down",
      "actual": "down",
      "confidence": 0.89,
      "yaw": -1.2,
      "pitch": 28.5
    },
    "pose_center": {
      "valid": true,
      "expected": "center",
      "actual": "center",
      "confidence": 0.96,
      "yaw": 0.5,
      "pitch": 2.1
    },
    "blink": {
      "valid": true,
      "blink_count": 2,
      "frames_processed": 3,
      "confidence": 1.0
    },
    "face_consistency": {
      "valid": true,
      "confidence": 0.94,
      "variation": 0.12,
      "avg_face_size": 45230.5
    }
  },
  "details": {
    "total_checks": 7,
    "passed_checks": 7,
    "anti_spoofing": {
      "head_movement": true,
      "blink_detected": true,
      "face_consistency": true
    }
  }
}
```

**Response (Wajah Palsu):**
```json
{
  "success": true,
  "is_real": false,
  "confidence": 0.15,
  "message": "Wajah palsu terdeteksi (foto/video)",
  "checks": {
    "pose_right": {
      "valid": false,
      "expected": "right",
      "actual": "center",
      "confidence": 0.0,
      "yaw": 2.1,
      "pitch": 1.5
    },
    "blink": {
      "valid": false,
      "blink_count": 0,
      "frames_processed": 3,
      "confidence": 0.0
    }
  }
}
```

---

## Flow Integrasi Flutter

### 1. Capture Frames

```dart
Map<String, dynamic> frames = {};

// Hadap kanan
frames['right'] = await captureAndConvert();

// Hadap kiri
frames['left'] = await captureAndConvert();

// Lihat atas
frames['up'] = await captureAndConvert();

// Lihat bawah
frames['down'] = await captureAndConvert();

// Lihat kamera
frames['center'] = await captureAndConvert();

// Kedipkan mata (capture 3-5 frames)
List<String> blinkFrames = [];
for (int i = 0; i < 3; i++) {
  await Future.delayed(Duration(milliseconds: 200));
  blinkFrames.add(await captureAndConvert());
}
frames['blink'] = blinkFrames;
```

### 2. Send to API

```dart
final response = await http.post(
  Uri.parse('$baseUrl/api/liveness/validate'),
  headers: {'Content-Type': 'application/json'},
  body: jsonEncode({'frames': frames}),
);

final data = jsonDecode(response.body);

if (data['is_real'] == true) {
  // Wajah asli - lanjutkan ke login
  print('Liveness check passed: ${data['confidence']}');
} else {
  // Wajah palsu - tolak
  print('Liveness check failed: ${data['message']}');
}
```

### 3. Convert Image to Base64

```dart
import 'dart:convert';
import 'package:camera/camera.dart';

Future<String> captureAndConvert() async {
  XFile photo = await cameraController.takePicture();
  Uint8List bytes = await photo.readAsBytes();
  return base64Encode(bytes);
}
```

---

## Anti-Spoofing Strategy

| Attack Type | Detection Method | How It Works |
|-------------|------------------|--------------|
| **Foto** | Head movement + Blink | Foto tidak bisa gerak kepala atau kedip |
| **Video** | Face consistency | Video biasanya punya ukuran wajah tidak konsisten |
| **Deepfake** | Multi-pose validation | Sulit generate real-time response untuk semua pose |
| **Screen replay** | Blink + movement timing | Timing tidak natural |

---

## Validation Checks

### 1. Head Pose Detection

| Pose | Yaw Range | Pitch Range |
|------|-----------|-------------|
| Right | 15° to 100° | any |
| Left | -100° to -15° | any |
| Up | any | -100° to -10° |
| Down | any | 20° to 100° |
| Center | -15° to 15° | -10° to 20° |

### 2. Blink Detection

- Minimum: 1 blink detected
- Uses Eye Aspect Ratio (EAR)
- Threshold: EAR < 0.2 = eyes closed

### 3. Face Consistency

- Checks face size variation across frames
- Variation < 30% = consistent (real face)
- Variation > 30% = inconsistent (possible fake)

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `no_face` | Wajah tidak terdeteksi | Pastikan wajah terlihat jelas |
| `decode_error` | Base64 invalid | Cek format base64 |
| `no_pose` | Head pose tidak terdeteksi | Pastikan pencahayaan cukup |
| `Frame not provided` | Frame tidak dikirim | Cek semua frame sudah di-capture |

---

## Performance

- **Response time**: ~2-3 seconds
- **Accuracy**: ~95% (tergantung kualitas camera)
- **False positive**: <5%
- **False negative**: <3%

---

## Security Notes

✅ **Dapat mencegah:**
- Foto statis
- Video replay
- Screen recording
- Low-quality deepfake

⚠️ **Belum dapat mencegah:**
- High-quality deepfake dengan real-time rendering
- 3D mask (sangat jarang)

---

## Testing

### Postman Example

```json
{
  "frames": {
    "right": "iVBORw0KGgo...",
    "left": "iVBORw0KGgo...",
    "up": "iVBORw0KGgo...",
    "down": "iVBORw0KGgo...",
    "center": "iVBORw0KGgo...",
    "blink": [
      "iVBORw0KGgo...",
      "iVBORw0KGgo...",
      "iVBORw0KGgo..."
    ]
  }
}
```

---

## Deployment

- **Platform**: Google Cloud Run
- **Region**: europe-west1
- **Memory**: 2GB
- **CPU**: 2 cores
- **Scaling**: Auto (0-10 instances)

---

## Tech Stack

- **Framework**: FastAPI
- **Face Detection**: MediaPipe
- **Blink Detection**: Eye Aspect Ratio (EAR)
- **Head Pose**: Landmark-based estimation
- **Language**: Python 3.11
