"""
Paper Trail Automator API v1

This package contains all the API routes for version 1 of the application.
"""

from . import auth, pdf, forms, websocket

__all__ = ["auth", "pdf", "forms", "websocket"] 