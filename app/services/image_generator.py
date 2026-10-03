import re
import time
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageDraw
from huggingface_hub import InferenceClient

from app.config import BASE_DIR, settings


PANELS_DIR = BASE_DIR / "static" / "panels"

PANELS_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# Current text-to-image model recommended in Hugging Face
# Inference Providers documentation.
DEFAULT_IMAGE_MODEL = "Qwen/Qwen-Image"


def _safe_name(text: str) -> str:
    """Convert prompt text into a safe filename."""

    text = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        text,
    )

    text = text.strip("_")

    if not text:
        return "panel"

    return text[:60]


def _placeholder(
    prompt: str,
    panel_number: int,
) -> Path:
    """Create placeholder image."""

    image = Image.new(
        "RGB",
        (1024, 1024),
        "#f4efe6",
    )

    draw = ImageDraw.Draw(image)

    draw.rectangle(
        (25, 25, 999, 999),
        outline="#222222",
        width=8,
    )

    draw.text(
        (70, 70),
        f"ComicCraft - Panel {panel_number}",
        fill="#222222",
    )

    words = prompt.split()

    lines = []
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 > 55:
            if current_line:
                lines.append(current_line)

            current_line = word
        else:
            current_line = (
                current_line + " " + word
            ).strip()

    if current_line:
        lines.append(current_line)

    y = 160

    for line in lines[:20]:
        draw.text(
            (70, y),
            line,
            fill="#444444",
        )

        y += 38

    filename = (
        f"panel_{panel_number}_"
        f"{uuid4().hex[:8]}_placeholder.png"
    )

    path = PANELS_DIR / filename

    image.save(path)

    return path


def _is_temporary_error(error: Exception) -> bool:
    """Check whether HF error is temporary."""

    error_text = str(error).upper()

    temporary_errors = [
        "503",
        "429",
        "500",
        "502",
        "504",
        "TIMEOUT",
        "TEMPORARY",
        "UNAVAILABLE",
    ]

    return any(
        error_code in error_text
        for error_code in temporary_errors
    )


def _create_client() -> InferenceClient:
    """Create Hugging Face inference client."""

    if not settings.hf_api_key:
        raise RuntimeError(
            "HF_API_KEY is not configured. "
            "Please add your Hugging Face token to .env."
        )

    return InferenceClient(
        api_key=settings.hf_api_key,
        provider=(
            settings.hf_image_provider
            or settings.image_provider
            or "auto"
        ),
    )


def generate_image(
    prompt: str,
    panel_number: int,
) -> Path:
    """
    Generate an AI comic illustration.

    Uses Hugging Face Inference Providers.
    Falls back to a placeholder if generation fails.
    """

    # No HF token -> placeholder.
    if not settings.hf_api_key:
        print(
            "HF_API_KEY not configured. "
            f"Creating placeholder for panel {panel_number}."
        )

        return _placeholder(
            prompt,
            panel_number,
        )

    full_prompt = f"""
Comic book illustration for an educational student comic.

SCENE:
{prompt}

VISUAL REQUIREMENTS:

- consistent main character
- same character appearance across panels
- clear facial expression
- clear body pose
- coherent environment
- cinematic composition
- good lighting
- colorful 2D comic illustration
- detailed background
- clean line art
- visually readable scene
- high quality
- no written text
- no speech bubbles
- no watermark
- no logos
"""

    negative_prompt = (
        "blurry, low quality, distorted face, "
        "extra fingers, extra arms, extra legs, "
        "deformed hands, malformed body, "
        "text, letters, words, subtitles, "
        "speech bubble, watermark, logo"
    )

    client = _create_client()

    # Prefer the .env model, otherwise use current default.
    model_name = (
        settings.hf_image_model
        or settings.image_model
        or DEFAULT_IMAGE_MODEL
    )

    # If old model is still present in .env, automatically switch.
    if model_name == "stabilityai/stable-diffusion-2-1":
        print(
            "Old Stable Diffusion model detected. "
            "Switching to Qwen/Qwen-Image."
        )

        model_name = DEFAULT_IMAGE_MODEL

    max_attempts = 3
    delays = [3, 7, 12]

    last_error = None

    for attempt in range(max_attempts):

        try:
            print(
                f"Generating panel {panel_number} "
                f"using {model_name} "
                f"(attempt {attempt + 1}/{max_attempts})"
            )

            image = client.text_to_image(
                prompt=full_prompt,
                negative_prompt=negative_prompt,
                model=model_name,
                width=1024,
                height=1024,
            )

            filename = (
                f"panel_{panel_number}_"
                f"{_safe_name(prompt)}_"
                f"{uuid4().hex[:8]}.png"
            )

            path = PANELS_DIR / filename

            image.save(path)

            print(
                f"Panel {panel_number} generated successfully."
            )

            return path

        except Exception as exc:

            last_error = exc

            print(
                f"Hugging Face image generation failed: {exc}"
            )

            # Authentication errors should not be retried.
            error_text = str(exc).upper()

            if "401" in error_text or "INVALID USERNAME" in error_text:
                raise RuntimeError(
                    "Hugging Face authentication failed (401). "
                    "Please create a new HF token with "
                    "Inference access and update HF_API_KEY "
                    "in your .env file."
                ) from exc

            if "403" in error_text:
                raise RuntimeError(
                    "Hugging Face denied access to the model. "
                    "Check your token permissions and model access."
                ) from exc

            # Retry temporary failures.
            if _is_temporary_error(exc):
                if attempt < max_attempts - 1:
                    print(
                        f"Temporary HF error. "
                        f"Retrying in {delays[attempt]} seconds..."
                    )

                    time.sleep(
                        delays[attempt]
                    )

                    continue

            break

    # Don't crash the whole comic pipeline.
    # Create a placeholder so the PDF can still be generated.
    print(
        f"Image generation failed for panel "
        f"{panel_number}. Creating placeholder."
    )

    print(
        f"Last Hugging Face error: {last_error}"
    )

    return _placeholder(
        prompt,
        panel_number,
    )