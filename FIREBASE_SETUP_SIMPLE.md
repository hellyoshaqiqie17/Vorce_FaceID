# Firebase Setup - Cara Mudah (Pakai Service Account di Cloud Run)

## ✅ Cara Termudah: Pakai Service Account yang Sudah Ada

Kamu sudah punya service account Firebase di project `hora-7394b`:
```
firebase-adminsdk-fbavc@hora-7394b.iam.gserviceaccount.com
```

Tinggal pilih service account ini di Cloud Run!

---

## 📝 Step-by-Step

### 1. Enable Firestore (Jika Belum)

1. Buka https://console.firebase.google.com/project/hora-7394b/firestore
2. Jika belum ada, klik **"Create database"**
3. Pilih **"Start in production mode"**
4. Location: `asia-southeast1` (atau yang dekat)
5. Klik **Enable**

### 2. Setup Cloud Run

1. Buka **Google Cloud Console** → **Cloud Run**
2. Pilih service: **vorce-faceid**
3. Klik **"Edit & Deploy New Revision"**

#### A. Tab "Security"
- **Service account**: Pilih `firebase-adminsdk-fbavc@hora-7394b`

#### B. Tab "Variables & Secrets"
- Add environment variable:
  - Name: `USE_FIREBASE`
  - Value: `true`

4. Klik **Deploy**

### 3. Verify

Setelah deploy selesai, test API:

```bash
curl https://vorce-faceid-544676101248.europe-west1.run.app/health
```

Response:
```json
{
  "status": "ok",
  "model_loaded": true,
  "registered_users": 0
}
```

Cek **Logs** di Cloud Run, harus muncul:
```
✅ Using Firebase with Application Default Credentials (Service Account)
✅ Firebase initialized - Collection: face_embeddings
✅ Using Firebase Firestore (Collection: face_embeddings)
```

---

## 🧪 Test Register

```bash
curl -X POST https://vorce-faceid-544676101248.europe-west1.run.app/api/register \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "TEST001",
    "frames_base64": ["base64_image_1", "base64_image_2", "base64_image_3"]
  }'
```

Lalu cek di **Firestore Console**:
- Collection `face_embeddings` harus muncul
- Document `TEST001` harus ada

---

## 🔐 Firestore Rules (Security)

Di Firestore Console → **Rules**, pastikan:

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Collection lain (existing)
    match /{document=**} {
      allow read, write: if request.auth != null;
    }
    
    // Collection baru untuk Face ID
    match /face_embeddings/{userId} {
      allow read, write: if true;
    }
  }
}
```

> ⚠️ `allow read, write: if true` artinya public access. Untuk production, ganti dengan authentication yang proper!

---

## 📊 Struktur Data

Setelah register, di Firestore akan muncul:

```
Firestore Database
└─ face_embeddings/
   └─ TEST001/
      ├─ user_id: "TEST001"
      ├─ embedding: [512 float numbers]
      ├─ created_at: "2025-01-19T12:00:00"
      ├─ updated_at: "2025-01-19T12:00:00"
      └─ samples_count: 10
```

---

## ❓ Troubleshooting

### Error: "Permission denied"

**Solusi:**
1. Pastikan service account `firebase-adminsdk-fbavc` punya role **"Cloud Datastore User"**
2. Di Google Cloud Console → **IAM & Admin** → **IAM**
3. Cari `firebase-adminsdk-fbavc@hora-7394b.iam.gserviceaccount.com`
4. Pastikan ada role: **Cloud Datastore User** atau **Firebase Admin**

### Error: "Firebase init failed"

**Solusi:**
1. Cek environment variable `USE_FIREBASE=true` sudah di-set
2. Cek service account sudah dipilih di Cloud Run Security tab
3. Cek logs untuk error detail

### Collection tidak muncul

**Solusi:**
1. Test register dulu (POST /api/register)
2. Collection otomatis dibuat saat pertama kali ada data
3. Refresh Firestore Console

---

## 💰 Cost

**Firestore Free Tier:**
- 50,000 reads/day
- 20,000 writes/day
- 1 GB storage

**Estimasi:**
- 1 register = 1 write (~2 KB)
- 1 verify = 1 read
- 100 users = ~200 KB
- 1000 login/day = 1000 reads → **FREE**

---

## ✅ Summary

**Yang perlu dilakukan:**
1. ✅ Enable Firestore di Firebase Console
2. ✅ Pilih service account `firebase-adminsdk-fbavc` di Cloud Run
3. ✅ Set environment variable `USE_FIREBASE=true`
4. ✅ Deploy
5. ✅ Test dengan Postman

**Tidak perlu:**
- ❌ Download JSON key
- ❌ Copy-paste credentials
- ❌ Setup Secret Manager

Lebih simple!
