import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.responses import JSONResponse
from app.api.routes import auth, user
from app.core.config import settings

app = FastAPI(title = "Smart Travel Planner API", version = "1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:4200", "http://localhost:8100"],
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

app.include_router(auth.router, prefix = "/api")
app.include_router(user.router, prefix = "/api")

@app.get("/")
def root():
    return {"message": "Smart Travel Planner API is running"}