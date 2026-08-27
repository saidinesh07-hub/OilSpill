from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Oil Spill Detection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Oil Spill Detection API is running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api/status")
def status():
    return {
        "backend": "online",
        "project": "oil-spill-detection"
    }