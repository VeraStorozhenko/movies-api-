import uvicorn

from app.config import get_settings
from app.main import app  # noqa: F401

if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)
