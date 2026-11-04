"""Donk backend: real Git evidence, model investigation, email actions."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import ask as ask_routes
from .routes import email as email_routes
from .routes import investigations as investigations_routes
from .routes import repos as repos_routes

log = logging.getLogger("donk")
logging.basicConfig(level=logging.INFO)

app = FastAPI(title="Donk")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(ask_routes.router)
app.include_router(email_routes.router)
app.include_router(investigations_routes.router)
app.include_router(repos_routes.router)
