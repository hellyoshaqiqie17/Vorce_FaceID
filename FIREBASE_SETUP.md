        # Firebase Setup untuk Face ID API

## 1. Setup Firebase Project

### A. Buat Project di Firebase Console
1. Buka https://console.firebase.google.com/
2. Klik **"Add project"** atau **"Create a project"**
3. Nama project: `vorce-faceid` (atau nama lain)
4. Disable Google Analytics (optional)
5. Klik **Create Project**

### B. Enable Firestore Database
1. Di sidebar, klik **"Firestore Database"**
2. Klik **"Create database"**
3. Pilih **"Start in production mode"**
4. Location: pilih yang dekat (contoh: `asia-southeast1`)
5. Klik **Enable**

### C. Setup Firestore Rules (Security)
Di tab **Rules**, ganti dengan:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /face_embeddings/{userId} {
      allow read, write: if true;
    }
  }
}
```

> ⚠️ Ini untuk development. Production harus pakai authentication!

---

## 2. Generate Service Account Key

1. Di Firebase Console, klik **⚙️ Settings** → **Project settings**
2. Tab **"Service accounts"**
3. Klik **"Generate new private key"**
4. Download file JSON (contoh: `vorce-faceid-firebase-adminsdk-xxxxx.json`)
5. **JANGAN COMMIT FILE INI KE GIT!**

---

## 3. Setup di Cloud Run

### A. Simpan Credentials sebagai Environment Variable

1. Buka file JSON yang di-download
2. Copy seluruh isinya (1 line JSON)
3. Di Google Cloud Console → Cloud Run → Service **vorce-faceid**
4. Klik **"Edit & Deploy New Revision"**
5. Tab **"Variables & Secrets"** → **"Environment variables"**
6. Tambahkan:
   - Name: `USE_FIREBASE`
   - Value: `true`
7. Tambahkan lagi:
   - Name: `FIREBASE_CREDENTIALS`
   - Value: (paste seluruh isi JSON file)
8. Klik **Deploy**

### B. Alternative: Upload sebagai Secret (Lebih Aman)

1. Google Cloud Console → **Secret Manager**
2. Klik **"Create Secret"**
3. Name: `firebase-credentials`
4. Secret value: (paste isi JSON file)
5. Klik **Create**

6. Di Cloud Run service:
   - Tab **"Variables & Secrets"** → **"Secrets"**
   - **"Reference a secret"**
   - Secret: `firebase-credentials`
   - Expose as: **Environment variable**
   - Name: `FIREBASE_CREDENTIALS`

---

## 4. Testing Local (Development)

### A. Setup Environment Variable

**Windows (PowerShell):**
```powershell
$env:USE_FIREBASE="true"
$env:FIREBASE_CREDENTIALS=(Get-Content firebase-key.json -Raw)
python run_api.py
```

**Linux/Mac:**
```bash
export USE_FIREBASE=true
export FIREBASE_CREDENTIALS=$(cat firebase-key.json)
python run_api.py
```

### B. Alternative: Gunakan File Path

Taruh file `firebase-key.json` di root project, lalu:

```python
# Ubah di api/database.py
cred = credentials.Certificate("firebase-key.json")
```

> ⚠️ Jangan lupa tambahkan `firebase-key.json` ke `.gitignore`!

---

## 5. Struktur Data di Firestore

### ⚠️ PENTING: Tidak Mengganggu Collection Lain

API ini **HANYA** mengakses collection `face_embeddings`. Collection lain seperti `absensi`, `companies`, `employee_location`, `users`, dll **TIDAK AKAN TERSENTUH**.

### Collection Baru: `face_embeddings`

```
Firestore Database
├─ absensi/              ← Collection existing (tidak tersentuh)
├─ companies/            ← Collection existing (tidak tersentuh)
├─ employee_location/    ← Collection existing (tidak tersentuh)
├─ users/                ← Collection existing (tidak tersentuh)
└─ face_embeddings/      ← Collection BARU untuk Face ID
   ├─ EMP001/
   │  ├─ user_id: "EMP001"
   │  ├─ embedding: [0.123, -0.456, ..., 0.789]  (array 512 float)
   │  ├─ created_at: "2025-01-19T10:30:00"
   │  ├─ updated_at: "2025-01-19T10:30:00"
   │  └─ samples_count: 10
   │
   └─ EMP002/
      ├─ user_id: "EMP002"
      ├─ embedding: [...]
      └─ ...
```

### ❓ Kenapa Tidak Simpan Foto?

| Aspek | Foto Asli | Embedding Vector |
|-------|-----------|------------------|
| **Size** | 500 KB - 2 MB | ~2 KB (512 float) |
| **Privacy** | ❌ Bisa dilihat wajah | ✅ Hanya angka, tidak bisa reverse |
| **Storage Cost** | ❌ Mahal | ✅ Murah |
| **Speed** | ❌ Lambat | ✅ Cepat |
| **Verifikasi** | ❌ Perlu process ulang | ✅ Langsung compare |

**Embedding vector** adalah representasi matematis wajah (512 angka). Cukup untuk verifikasi, tapi tidak bisa di-reverse jadi foto.

### Data yang Disimpan per User:

```json
{
  "user_id": "EMP001",
  "embedding": [0.123, -0.456, 0.789, ..., 0.321],
  "created_at": "2025-01-19T10:30:00",
  "updated_at": "2025-01-19T10:30:00",
  "samples_count": 10
}
```

- `user_id`: ID karyawan (sama dengan ID di collection `users`)
- `embedding`: Vector 512 float (hasil ArcFace model)
- `created_at`: Waktu pertama kali registrasi
- `updated_at`: Waktu terakhir update
- `samples_count`: Jumlah foto yang di-capture saat registrasi

---

## 6. Verify Setup

### Test API:

```bash
# Health check
curl https://vorce-faceid-544676101248.europe-west1.run.app/health

# Response harus:
{
  "status": "ok",
  "model_loaded": true,
  "registered_users": 0
}
```

### Check Logs:

Di Cloud Run → Logs, cari:
- ✅ `Using Firebase Firestore` → Firebase aktif
- ⚠️ `Using local JSON storage` → Firebase tidak aktif

---

## 7. Fallback Mode

Jika Firebase gagal, sistem otomatis fallback ke JSON lokal:
- File: `face_data.json` di Cloud Run
- ⚠️ Data hilang setiap redeploy!

---

## 8. Cost Estimate

### Firestore Pricing (Free Tier):
- **Reads**: 50,000/day free
- **Writes**: 20,000/day free
- **Deletes**: 20,000/day free
- **Storage**: 1 GB free

### Estimasi Usage:
- 1 Register = 1 write (~512 floats = ~2 KB)
- 1 Verify = 1 read
- 100 users = ~200 KB storage
- 1000 login/day = 1000 reads → **FREE**

---

## 9. Security Best Practices

### Production Setup:

1. **Enable Firebase Authentication**
2. **Update Firestore Rules:**

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /face_embeddings/{userId} {
      // Only authenticated API can access
      allow read, write: if request.auth != null;
    }
  }
}
```

3. **Restrict API Key** di Google Cloud Console
4. **Enable Cloud Run Authentication**

---

## 10. Troubleshooting

### Error: "Firebase init failed"
- Cek environment variable `FIREBASE_CREDENTIALS` ada
- Cek format JSON valid (gunakan JSON validator)
- Cek service account punya permission Firestore

### Error: "Permission denied"
- Cek Firestore Rules
- Cek service account role: **"Cloud Datastore User"**

### Data tidak tersimpan
- Cek logs di Cloud Run
- Cek Firestore console apakah collection `face_embeddings` ada
- Test dengan Postman: POST /api/register

---

## 11. Migration dari JSON ke Firebase

Jika sudah ada data di `face_data.json`:

```python
import json
import firebase_admin
from firebase_admin import credentials, firestore

cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

with open('face_data.json', 'r') as f:
    data = json.load(f)

for user_id, user_data in data.items():
    db.collection('face_embeddings').document(user_id).set(user_data)
    print(f"Migrated: {user_id}")
```

---

## Summary

✅ **Keuntungan Firebase:**
- Data persistent (tidak hilang saat redeploy)
- Scalable (auto-scale)
- Real-time sync
- Free tier cukup untuk production

✅ **Setup Steps:**
1. Buat Firebase project
2. Enable Firestore
3. Download service account key
4. Set environment variable di Cloud Run
5. Deploy

✅ **Fallback:**
- Jika Firebase gagal → otomatis pakai JSON lokal
- Tidak ada downtime
