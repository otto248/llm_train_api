"""Root entrypoint that exposes the FastAPI app and CLI launcher."""

from __future__ import annotations

from app.main import app, create_app, main

__all__ = ["app", "create_app", "main"]

if __name__ == "__main__":
    main()
