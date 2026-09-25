"""
Vercel serverless entrypoint for FastAPI backend.
This file imports the FastAPI app instance and exposes it to Vercel's Python runtime.
"""
from app.main import app

# Vercel expects the ASGI app to be named 'app' at module level
# The import above already provides this, so no additional code is needed.
