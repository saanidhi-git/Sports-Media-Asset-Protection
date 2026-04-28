# 🧠 RT-DETRv2 Detection Microservice

Standalone, separately-deployable object detection service for the **SPORTS GUARDIAN** anti-piracy system.

---

## 📏 Model Weight Sizes

| Model | File | Size | Use Case |
|-------|------|------|----------|
| RT-DETRv2-S | `rtdetrv2-s.pt` | **~20 MB** | Fast, low-resource servers |
| RT-DETRv2-L | `rtdetrv2-l.pt` | **~32 MB** | ✅ Recommended balance |
| RT-DETRv2-X | `rtdetrv2-x.pt` | **~67 MB** | Max accuracy, needs GPU |

> All of these are small enough for Render's free tier (512 MB RAM). No external storage needed.

---

## 📦 Where to Store Weights

### Option A: Auto-Download on Startup (Recommended for Render)
Upload your `.pt` file to one of these services and set the `MODEL_DOWNLOAD_URL` env var:

| Host | How |
|------|-----|
| **HuggingFace** | Upload to a model repo → use `https://huggingface.co/<user>/<repo>/resolve/main/rtdetrv2-l.pt` |
| **Google Drive** | Share file → use `https://drive.google.com/uc?export=download&id=<FILE_ID>` |
| **Cloudinary** | Upload as raw file → use the `secure_url` |

The service downloads weights **once** on first boot, then caches them in the container.

### Option B: Local Development
Just drop the `.pt` file into `model/weights/`:
```
model/
├── weights/
│   └── rtdetrv2-l.pt   ← Place here
├── main.py
└── ...
```

---

## 🚀 Deploy on Render

### Step 1: Create a new **Web Service** on Render
- **Root Directory**: `model`
- **Environment**: `Docker`
- **Instance Type**: Starter ($7/mo) or Free (may be slow)

### Step 2: Set Environment Variables
| Variable | Value | Required |
|----------|-------|----------|
| `MODEL_DOWNLOAD_URL` | URL to your `.pt` file | ✅ Yes (if weights not in image) |
| `MODEL_FILENAME` | `rtdetrv2-l.pt` | Optional (defaults to rtdetrv2-l.pt) |
| `DEFAULT_CONFIDENCE` | `0.25` | Optional |
| `PORT` | Auto-set by Render | No |

### Step 3: Deploy
Render will build the Docker image and start the service. On first boot:
1. Weights download from `MODEL_DOWNLOAD_URL` → saved to `weights/`
2. RT-DETRv2 model loads into memory
3. Service is ready at `https://your-model-service.onrender.com`

### Step 4: Connect to Backend
Set `MODEL_SERVICE_URL=https://your-model-service.onrender.com` in your **backend's** `.env`.

---

## 📡 API Reference

### `GET /health`
```json
{ "status": "online", "model_file": "weights/rtdetrv2-l.pt", "weights_exist": true }
```

### `POST /predict`
**Request:**
```json
{
  "image_url": "https://res.cloudinary.com/.../frame_001.jpg",
  "confidence_threshold": 0.25
}
```
**Response:**
```json
{
  "detections": [
    { "label": "sports ball", "confidence": 0.92, "box": [120.5, 45.0, 310.2, 280.8] }
  ],
  "frame_width": 1280,
  "frame_height": 720
}
```

---

## 🏗️ Local Development
```bash
cd model
pip install -r requirements.txt
python main.py
# → Running on http://localhost:8001
```
