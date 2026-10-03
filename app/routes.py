from pathlib import Path

from fastapi import (
    APIRouter,
    Form,
    HTTPException,
    Request,
)

from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
)

from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, settings
from app.schemas import PromptRequest

from app.services.gemini_service import (
    generate_outline,
    generate_story,
)

from app.services.image_generator import (
    generate_image,
)

from app.services.layout_builder import (
    build_comic_layout,
)

from app.services.exporters import (
    save_pdf,
)


router = APIRouter()

templates = Jinja2Templates(
    directory=str(
        BASE_DIR / "templates"
    )
)


def _run_pipeline(
    request_data: PromptRequest,
):
    """
    Complete AI comic pipeline.

    1. Gemini outline
    2. Gemini story
    3. AI images
    4. Layout
    5. PDF
    """

    # Step 1
    outline = generate_outline(
        request_data
    )

    # Step 2
    story = generate_story(
        request_data,
        outline,
    )

    # Step 3
    image_paths = []

    for panel in story:

        panel_number = int(
            panel["panel_number"]
        )

        path = generate_image(
            panel["image_prompt"],
            panel_number,
        )

        image_paths.append(
            "/static/panels/"
            + path.name
        )

    # Step 4
    layout = build_comic_layout(
        story,
        image_paths,
    )

    # Step 5
    pdf_path = save_pdf(
        f"{request_data.character_name} Comic",
        layout,
    )

    return layout, pdf_path


@router.get(
    "/",
    response_class=HTMLResponse,
)
async def home(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "settings": settings
        },
    )


@router.post(
    "/generate",
    response_class=HTMLResponse,
)
async def generate(
    request: Request,

    story_prompt: str = Form(...),

    character_name: str = Form(...),

    setting: str = Form(...),

    tone: str = Form(...),

    art_style: str = Form(...),
):
    try:

        data = PromptRequest(
            story_prompt=story_prompt,
            character_name=character_name,
            setting=setting,
            tone=tone,
            art_style=art_style,
        )

        layout, pdf_path = (
            _run_pipeline(data)
        )

        return templates.TemplateResponse(
            request=request,
            name="comic_preview.html",
            context={
                "layout": layout,
                "pdf_url": (
                    "/download/"
                    + pdf_path.name
                ),
                "title": (
                    f"{character_name}'s Comic"
                ),
            },
        )

    except Exception as exc:

        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "error": str(exc)
            },
            status_code=500,
        )


@router.post(
    "/generate-comic/json"
)
async def generate_json(
    payload: PromptRequest,
):
    """
    JSON API endpoint.
    """

    try:

        layout, pdf_path = (
            _run_pipeline(payload)
        )

        return JSONResponse(
            {
                "title": (
                    f"{payload.character_name}"
                    "'s Comic"
                ),

                "panels": [
                    panel.model_dump()
                    for panel in layout
                ],

                "pdf_path": (
                    "/download/"
                    + pdf_path.name
                ),
            }
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get(
    "/download/{filename}"
)
async def download(
    filename: str,
):
    """
    Download generated PDF.
    """

    path = (
        BASE_DIR
        / "static"
        / "exports"
        / filename
    )

    # Security check
    if (
        path.suffix.lower() != ".pdf"
        or not path.is_file()
        or path.parent
        != (
            BASE_DIR
            / "static"
            / "exports"
        )
    ):
        raise HTTPException(
            status_code=404,
            detail="PDF not found",
        )

    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
    )


@router.get(
    "/export-success",
    response_class=HTMLResponse,
)
async def export_success(
    request: Request,
):
    return templates.TemplateResponse(
        request=request,
        name="export_success.html",
        context={},
    )


@router.get(
    "/test-image"
)
async def test_image(
    prompt: str = (
        "A brave fox exploring "
        "an enchanted forest"
    ),
    panel: int = 1,
):
    """
    Test image generation separately.
    """

    try:

        path = generate_image(
            prompt,
            panel,
        )

        return {
            "success": True,
            "image_path": (
                "/static/panels/"
                + path.name
            ),
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc


@router.get("/health")
async def health():
    """
    Application health endpoint.
    """

    return {
        "status": "ok",
        "gemini_configured": bool(
            settings.gemini_api_key
        ),
        "image_api_configured": bool(
            settings.hf_api_key
        ),
    }