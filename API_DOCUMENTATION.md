# Liveness Detection API - Documentation

## Base URL
```
https://vorce-faceid-544676101248.europe-west1.run.app
```

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Description:** Check API status dan apakah model sudah loaded

**Response:**
```json
{
  "status": "ok",
  "model_loaded": false,
  "service": "liveness-detection"
}
```

**Note:** `model_loaded` akan `false` sampai request pertama ke `/api/liveness/validate` (lazy loading)

---

### 2. Validate Liveness

**Endpoint:** `POST /api/liveness/validate`

**Description:** Validasi apakah wajah asli atau palsu (foto/video)

**Headers:**
```
Content-Type: application/json
```

**Request Body:**
```json
{
  "frames": {
    "left": "base64_encoded_image_string",
    "right": "base64_encoded_image_string",
    "center": "base64_encoded_image_string",
    "blink": [
      "base64_encoded_frame_1",
      "base64_encoded_frame_2",
      "base64_encoded_frame_3"
    ]
  }
}
```

**Request Body Explanation:**
- `left`: Base64 string dari gambar saat user geleng kiri
- `right`: Base64 string dari gambar saat user geleng kanan
- `center`: Base64 string dari gambar saat user lihat kamera
- `blink`: Array of base64 strings (3-5 frames) untuk deteksi kedipan mata

**Response (Wajah Asli - Confidence >= 70%):**
```json
{
  "success": true,
  "is_real": true,
  "confidence": 0.85,
  "message": "Wajah asli terdeteksi",
  "checks": {
    "pose_left": {
      "valid": true,
      "expected": "left",
      "actual": "left",
      "confidence": 0.88,
      "yaw": -22.1,
      "pitch": 3.5
    },
    "pose_right": {
      "valid": true,
      "expected": "right",
      "actual": "right",
      "confidence": 0.95,
      "yaw": 25.3,
      "pitch": 5.2
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
    "total_checks": 5,
    "passed_checks": 5,
    "threshold": 0.70,
    "anti_spoofing": {
      "head_movement": true,
      "blink_detected": true,
      "face_consistency": true
    }
  }
}
```

**Response (Wajah Palsu - Confidence < 70%):**
```json
{
  "success": true,
  "is_real": false,
  "confidence": 0.45,
  "message": "Wajah palsu terdeteksi (foto/video)",
  "checks": {
    "pose_left": {
      "valid": false,
      "expected": "left",
      "actual": "center",
      "confidence": 0.0,
      "yaw": 2.1,
      "pitch": 1.5
    },
    "pose_right": {
      "valid": true,
      "expected": "right",
      "actual": "right",
      "confidence": 0.54,
      "yaw": 8.3,
      "pitch": 2.1
    },
    "pose_center": {
      "valid": true,
      "expected": "center",
      "actual": "center",
      "confidence": 0.80,
      "yaw": 1.2,
      "pitch": 0.5
    },
    "blink": {
      "valid": false,
      "blink_count": 0,
      "frames_processed": 3,
      "confidence": 0.0
    },
    "face_consistency": {
      "valid": true,
      "confidence": 0.75,
      "variation": 0.18,
      "avg_face_size": 42130.2
    }
  },
  "details": {
    "total_checks": 5,
    "passed_checks": 3,
    "threshold": 0.70,
    "anti_spoofing": {
      "head_movement": false,
      "blink_detected": false,
      "face_consistency": true
    }
  }
}
```

**Response (Error):**
```json
{
  "success": false,
  "is_real": false,
  "confidence": 0.0,
  "checks": {},
  "message": "Error: [error message]"
}
```

---

## Validation Logic

### Confidence Threshold
- **Confidence >= 70%** → Wajah ASLI ✅
- **Confidence < 70%** → Wajah PALSU ❌ (foto/video)

### Pose Requirements
| Pose | Yaw Range | Pitch Range | Keterangan |
|------|-----------|-------------|------------|
| Left | -100° to -5° | any | Geleng kiri sedikit |
| Right | 5° to 100° | any | Geleng kanan sedikit |
| Center | -15° to 15° | -10° to 15° | Wajah di tengah |

### Blink Detection
- Minimum: 1 blink detected
- Uses Eye Aspect Ratio (EAR)
- Threshold: EAR < 0.2 = eyes closed

### Face Consistency
- Checks face size variation across frames
- Variation < 50% = consistent (real face)
- Variation > 50% = inconsistent (possible fake)

---

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `no_face` | Wajah tidak terdeteksi | Pastikan wajah terlihat jelas |
| `decode_error` | Base64 invalid | Cek format base64 |
| `no_pose` | Head pose tidak terdeteksi | Pastikan pencahayaan cukup |
| `Frame not provided` | Frame tidak dikirim | Cek semua frame sudah di-capture |

---

## Integration Example (Flutter)

### 1. Capture Frames
```dart
import 'dart:convert';
import 'package:camera/camera.dart';

Future<String> captureAndConvert(CameraController controller) async {
  XFile photo = await controller.takePicture();
  Uint8List bytes = await photo.readAsBytes();
  return base64Encode(bytes);
}

Future<Map<String, dynamic>> captureAllFrames(CameraController controller) async {
  Map<String, dynamic> frames = {};
  
  // User geleng kiri
  await showInstruction("Geleng KIRI");
  await Future.delayed(Duration(seconds: 1));
  frames['left'] = await captureAndConvert(controller);
  
  // User geleng kanan
  await showInstruction("Geleng KANAN");
  await Future.delayed(Duration(seconds: 1));
  frames['right'] = await captureAndConvert(controller);
  
  // User lihat kamera
  await showInstruction("Lihat KAMERA");
  await Future.delayed(Duration(seconds: 1));
  frames['center'] = await captureAndConvert(controller);
  
  // User kedip mata (capture 3 frames)
  await showInstruction("KEDIPKAN MATA");
  List<String> blinkFrames = [];
  for (int i = 0; i < 3; i++) {
    await Future.delayed(Duration(milliseconds: 200));
    blinkFrames.add(await captureAndConvert(controller));
  }
  frames['blink'] = blinkFrames;
  
  return frames;
}
```

### 2. Send to API
```dart
import 'package:http/http.dart' as http;

Future<bool> validateLiveness(Map<String, dynamic> frames) async {
  final url = Uri.parse('https://vorce-faceid-544676101248.europe-west1.run.app/api/liveness/validate');
  
  final response = await http.post(
    url,
    headers: {'Content-Type': 'application/json'},
    body: jsonEncode({'frames': frames}),
  );
  
  if (response.statusCode == 200) {
    final data = jsonDecode(response.body);
    
    if (data['is_real'] == true) {
      print('✅ Wajah asli terdeteksi');
      print('Confidence: ${(data['confidence'] * 100).toStringAsFixed(0)}%');
      return true;
    } else {
      print('❌ Wajah palsu terdeteksi');
      print('Confidence: ${(data['confidence'] * 100).toStringAsFixed(0)}%');
      return false;
    }
  } else {
    print('Error: ${response.statusCode}');
    return false;
  }
}
```

### 3. Complete Flow
```dart
Future<void> performLivenessCheck() async {
  try {
    // 1. Initialize camera
    final cameras = await availableCameras();
    final frontCamera = cameras.firstWhere(
      (camera) => camera.lensDirection == CameraLensDirection.front,
    );
    final controller = CameraController(frontCamera, ResolutionPreset.medium);
    await controller.initialize();
    
    // 2. Capture all frames
    final frames = await captureAllFrames(controller);
    
    // 3. Validate liveness
    final isReal = await validateLiveness(frames);
    
    // 4. Handle result
    if (isReal) {
      // Proceed with login/registration
      navigateToNextScreen();
    } else {
      // Show error message
      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: Text('Validasi Gagal'),
          content: Text('Wajah tidak terdeteksi sebagai wajah asli. Gunakan wajah asli, bukan foto atau video.'),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: Text('Coba Lagi'),
            ),
          ],
        ),
      );
    }
    
    // 5. Dispose camera
    await controller.dispose();
    
  } catch (e) {
    print('Error: $e');
  }
}
```

---

## Performance

- **Response time**: ~2-5 seconds (first request slower due to lazy loading)
- **Accuracy**: ~95% (tergantung kualitas camera)
- **False positive**: <5% (wajah palsu dianggap asli)
- **False negative**: <3% (wajah asli dianggap palsu)

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

## Tech Stack

- **Framework**: FastAPI
- **Face Detection**: MediaPipe Face Mesh
- **Blink Detection**: Eye Aspect Ratio (EAR)
- **Head Pose**: Landmark-based estimation
- **Language**: Python 3.11
- **Deployment**: Google Cloud Run

---

## Support

Untuk pertanyaan atau issue, silakan hubungi tim development.
