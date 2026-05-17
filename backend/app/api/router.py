"""API router registration module.

This module imports health, ticket, and dashboard routes and exposes a
shared APIRouter instance that the main application can include.
"""

from fastapi import APIRouter

from app.api.routes import dashboard, health, tickets


api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(tickets.router)
api_router.include_router(dashboard.router)