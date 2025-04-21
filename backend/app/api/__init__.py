"""
Paper Trail Automator API

This package contains all the API routes for the application.
"""

from .v1 import auth, pdf, forms, websocket, users

__all__ = ["auth", "pdf", "forms", "websocket", "users"] 