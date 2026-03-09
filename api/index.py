"""Vercel serverless entry point — exposes the FastAPI app."""

from webapp.app import app

# Vercel's Python runtime looks for an `app` variable (ASGI/WSGI)
# or a `handler` function. FastAPI is ASGI-compatible.
