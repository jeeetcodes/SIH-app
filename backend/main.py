from __future__ import annotations

import os
import uvicorn

from app.main import (  # noqa: F401
    app,
    lifespan,
    root,
    unhandled_exception_handler,
    validation_exception_handler,
)

__all__ = ["app"]

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
