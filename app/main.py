from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, settings
from app.routes import router


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "AI Comic Story Creator "
        "using Gemini and Stable Diffusion"
    ),
)


# Static files
app.mount(
    "/static",
    StaticFiles(
        directory=str(
            BASE_DIR / "static"
        )
    ),
    name="static",
)


# Routes
app.include_router(router)


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )