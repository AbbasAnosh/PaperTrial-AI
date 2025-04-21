"""
Routes package for the application.
"""

from app.routes.auth import router as auth_router
from app.routes.forms import router as forms_router
from app.routes.users import router as users_router
from app.routes.websocket import router as websocket_router

__all__ = [
    "auth_router",
    "forms_router",
    "users_router",
    "websocket_router",
] 