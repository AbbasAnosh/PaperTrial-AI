"""
Main FastAPI application module.

This module initializes and configures the FastAPI application with all routes,
middleware, and OpenAPI documentation.
"""

import os
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.staticfiles import StaticFiles
from app.core.config import settings
from app.core.errors import setup_exception_handlers
from app.core.logging import setup_logging, get_logger
from app.core.monitoring import MetricsMiddleware, SystemMetrics, analytics
from app.routes import auth, users, forms
from app.docs.api_examples import API_EXAMPLES, WEBHOOK_DOCS
import prometheus_client
from prometheus_client import make_asgi_app

# Configure logging
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_file=settings.LOG_FILE,
    log_format=settings.LOG_FORMAT
)
logger = get_logger(__name__)

app = FastAPI(
    title="Paper Trail Automator API",
    description="""
    # Paper Trail Automator API Documentation

    This API provides endpoints for managing form templates, processing documents,
    and automating form submissions.

    ## Features

    - Form template management
    - PDF document processing
    - Form submission handling
    - User authentication and authorization
    - Real-time status updates
    - Webhook notifications

    ## Getting Started

    1. Register a new user account
    2. Create form templates
    3. Process documents
    4. Submit forms
    5. Monitor status

    ## Authentication

    All API endpoints except registration and login require authentication.
    Include the JWT token in the Authorization header:

    ```
    Authorization: Bearer <token>
    ```

    ## Rate Limiting

    - Authenticated users: 100 requests per minute
    - Anonymous users: 20 requests per minute
    - IP-based rate limiting: 1000 requests per hour

    ## Pagination

    List endpoints support pagination using query parameters:

    - `page`: Page number (1-based)
    - `per_page`: Items per page (default: 20, max: 100)

    Response includes:
    - `items`: List of items
    - `total`: Total number of items
    - `page`: Current page
    - `per_page`: Items per page
    - `pages`: Total number of pages

    ## Filtering and Sorting

    List endpoints support filtering and sorting:

    ```
    GET /api/v1/forms/templates?status=active&sort=-created_at
    ```

    Filter parameters:
    - `status`: Filter by status
    - `search`: Search in name and description
    - `created_after`: Filter by creation date
    - `created_before`: Filter by creation date

    Sort parameters:
    - Prefix with `-` for descending order
    - Available fields: created_at, updated_at, name, status

    ## WebSocket Support

    Real-time updates are available via WebSocket connections:

    ```javascript
    const ws = new WebSocket('wss://api.example.com/ws');
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log('Update:', data);
    };
    ```

    ## Error Handling

    All errors follow a standard format:

    ```json
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "Human readable message",
            "details": {}
        }
    }
    ```

    Common error codes:
    - `UNAUTHORIZED`: Authentication required
    - `FORBIDDEN`: Insufficient permissions
    - `NOT_FOUND`: Resource not found
    - `VALIDATION_ERROR`: Invalid input data
    - `RATE_LIMITED`: Too many requests
    - `INTERNAL_ERROR`: Server error

    ## Examples

    See the interactive examples in the OpenAPI documentation for each endpoint.
    """,
    version="1.0.0",
    docs_url=None,
    redoc_url=None
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add metrics middleware
app.add_middleware(MetricsMiddleware)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(forms.router, prefix="/api/v1/forms", tags=["Forms"])

# Set up exception handlers
setup_exception_handlers(app)

# Custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Add examples to endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            endpoint = openapi_schema["paths"][path][method]
            tag = endpoint.get("tags", [""])[0].lower()
            operation_id = endpoint.get("operationId", "").lower()

            if tag in API_EXAMPLES and operation_id in API_EXAMPLES[tag]:
                example = API_EXAMPLES[tag][operation_id]
                if "requestBody" in endpoint:
                    endpoint["requestBody"]["content"] = {
                        "application/json": {
                            "example": example.get("example", {})
                        }
                    }
                if "responses" in endpoint:
                    for status in endpoint["responses"]:
                        if "content" in endpoint["responses"][status]:
                            endpoint["responses"][status]["content"] = {
                                "application/json": {
                                    "example": example.get("response", {})
                                }
                            }

    # Add webhook documentation
    openapi_schema["components"]["schemas"]["WebhookEvent"] = {
        "type": "object",
        "properties": {
            "event": {"type": "string", "enum": list(WEBHOOK_DOCS["events"].keys())},
            "timestamp": {"type": "string", "format": "date-time"},
            "data": {"type": "object"}
        },
        "example": WEBHOOK_DOCS["events"]["form.submitted"]["payload"]
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Custom documentation UI
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
        oauth2_redirect_url="/docs/oauth2-redirect",
        swagger_js_url="/static/swagger-ui-bundle.js",
        swagger_css_url="/static/swagger-ui.css",
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint that returns system status."""
    return SystemMetrics.get_health_status()

# Analytics endpoint
@app.get("/analytics")
async def get_analytics():
    """Get usage analytics."""
    return analytics.get_analytics()

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info(f"Starting {app.title} v{app.version}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info(f"Shutting down {app.title}") 