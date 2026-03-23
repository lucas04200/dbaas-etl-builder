#!/usr/bin/env python3
"""
DataForge — DBaaS Management Platform

This file is the entrypoint kept for backwards compatibility with start.sh.
All application code has been moved to the app/ package.
"""

import sys
from pathlib import Path

# Ensure web/ is on the Python path so `app.` imports resolve
sys.path.insert(0, str(Path(__file__).parent))

from app.main import app  # noqa: F401, E402

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=False)
