# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.auth.auth_routes import router as auth_router
from backend.chat.chat_routes import router as chat_router

app = FastAPI(title="AIDA Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)

@app.get("/health")
def health():
    return {"status": "ok"}
    