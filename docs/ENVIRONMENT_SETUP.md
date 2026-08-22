# Environment Setup & Dependency Management

## 1. Prerequisites
- **Python**: Python 3.10+ (tested on Python 3.11 / 3.14).
- **Node.js**: Node.js v18+ and npm v9+ (tested on Node v24).
- **Git**: Git version 2.30+.

---

## 2. Backend Setup
1. **Clone repository & enter workspace root**:
   ```bash
   cd "c:\projects\OIL SPILL"
   ```

2. **Install Python Core & Geospatial Dependencies**:
   ```bash
   python -m pip install numpy scipy shapely pyproj scikit-learn pydantic pydantic-settings fastapi uvicorn pytest httpx sqlalchemy
   ```

3. **Install PyTorch (CPU or CUDA)**:
   ```bash
   # CPU installation:
   python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

   # Or for CUDA GPU:
   # python -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   ```

4. **Environment Variables**:
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

---

## 3. Frontend Setup
1. **Navigate to `frontend` directory & install packages**:
   ```bash
   cd frontend
   npm install
   ```

2. **Verify Frontend Build**:
   ```bash
   npm run build
   ```

---

## 4. Running the Complete System
1. **Seed Database with Multi-Pass Case Studies**:
   ```bash
   python scripts/seed_database.py
   ```

2. **Launch Backend API Server**:
   ```bash
   python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   *Swagger Docs*: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

3. **Launch Frontend Dashboard** (in another terminal):
   ```bash
   cd frontend
   npm run dev
   ```
   *Dashboard URL*: [http://localhost:5173](http://localhost:5173)

---

## 5. Running Automated Verification Tests
```bash
python -m pytest -v
```
All 22 unit, geospatial, ML, temporal, forecasting, risk, and API tests will execute and report 100% pass status.
