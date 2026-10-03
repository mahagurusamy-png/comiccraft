import json
import time

from google import genai
from google.genai import types

from app.config import settings
from app.schemas import PromptRequest


# Models are tried in this order.
# If one model is temporarily unavailable, the next model is used.
MODEL_FALLBACKS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
]


def _client() -> genai.Client:
    """Create Gemini client."""

    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. "
            "Please add your Gemini API key to .env."
        )

    return genai.Client(
        api_key=settings.gemini_api_key
    )


def _is_temporary_error(error: Exception) -> bool:
    """Check whether Gemini error is temporary."""

    error_text = str(error).upper()

    temporary_errors = [
        "503",
        "UNAVAILABLE",
        "429",
        "RESOURCE_EXHAUSTED",
        "500",
        "INTERNAL",
        "DEADLINE_EXCEEDED",
        "TIMEOUT",
    ]

    return any(
        error_code in error_text
        for error_code in temporary_errors
    )


def _generate_with_model(
    client: genai.Client,
    model_name: str,
    prompt: str,
    schema: dict,
):
    """Generate JSON using one Gemini model."""

    response = client.models.generate_content(
        model=model_name,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            max_output_tokens=6000,
        ),
    )

    if not response.text:
        raise RuntimeError(
            f"{model_name} returned an empty response."
        )

    try:
        return json.loads(response.text)

    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"{model_name} returned invalid JSON."
        ) from exc


def _generate_json(
    prompt: str,
    schema: dict,
):
    """
    Generate JSON with automatic model fallback.

    Order:
    1. gemini-3.8-flash
    2. gemini-3.7-flash
    3. gemini-3.5-flash
    4. gemini-3.5-flash-lite
    """

    client = _client()

    # Start with the model configured in .env.
    configured_model = settings.gemini_model.strip()

    models_to_try = []

    if configured_model:
        models_to_try.append(configured_model)

    # Add fallback models without duplicates.
    for model in MODEL_FALLBACKS:
        if model not in models_to_try:
            models_to_try.append(model)

    last_error = None

    for model_name in models_to_try:

        # Retry each model twice before moving to the next model.
        for attempt in range(2):

            try:
                print(
                    f"Trying Gemini model: {model_name} "
                    f"(attempt {attempt + 1}/2)"
                )

                result = _generate_with_model(
                    client=client,
                    model_name=model_name,
                    prompt=prompt,
                    schema=schema,
                )

                print(
                    f"Gemini success using model: {model_name}"
                )

                return result

            except Exception as exc:

                last_error = exc

                print(
                    f"Gemini model {model_name} failed: {exc}"
                )

                # Permanent error:
                # Don't waste time trying every model.
                if not _is_temporary_error(exc):
                    raise

                # Retry same model once.
                if attempt == 0:
                    print(
                        f"Temporary error from {model_name}. "
                        "Retrying in 3 seconds..."
                    )

                    time.sleep(3)

                else:
                    print(
                        f"{model_name} still unavailable. "
                        "Moving to next fallback model..."
                    )

    raise RuntimeError(
        "All Gemini models are temporarily unavailable. "
        "Please try again later. "
        f"Last error: {last_error}"
    )


def generate_outline(
    request: PromptRequest,
) -> list[dict]:
    """Generate exactly five connected comic panels."""

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "panel_number": {
                    "type": "integer"
                },
                "title": {
                    "type": "string"
                },
                "scene_description": {
                    "type": "string"
                },
                "image_prompt": {
                    "type": "string"
                },
            },
            "required": [
                "panel_number",
                "title",
                "scene_description",
                "image_prompt",
            ],
        },
    }

    prompt = f"""
You are a professional comic storyboard writer.

Create exactly {settings.panels_count} connected comic panels.

USER STORY:
{request.story_prompt}

MAIN CHARACTER:
{request.character_name}

SETTING:
{request.setting}

TONE:
{request.tone}

ART STYLE:
{request.art_style}

Requirements:

1. Create exactly five panels.
2. All panels must form one continuous story.
3. Keep the same main character throughout.
4. Maintain visual continuity.
5. Panel 1 should introduce the situation.
6. Panels 2-4 should develop the story.
7. Panel 5 should provide a satisfying ending.
8. Keep each scene easy to illustrate.
9. Do not put written text inside the image prompt.

Return ONLY valid JSON.
"""

    result = _generate_json(
        prompt=prompt,
        schema=schema,
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "Gemini outline response is not a list."
        )

    if len(result) != settings.panels_count:
        raise RuntimeError(
            f"Gemini returned {len(result)} panels "
            f"instead of {settings.panels_count}."
        )

    return result


def generate_story(
    request: PromptRequest,
    outline: list[dict],
) -> list[dict]:
    """Convert storyboard into complete comic content."""

    schema = {
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "panel_number": {
                    "type": "integer"
                },
                "title": {
                    "type": "string"
                },
                "scene_description": {
                    "type": "string"
                },
                "caption": {
                    "type": "string"
                },
                "narration": {
                    "type": "string"
                },
                "dialogue": {
                    "type": "string"
                },
                "image_prompt": {
                    "type": "string"
                },
            },
            "required": [
                "panel_number",
                "title",
                "scene_description",
                "caption",
                "narration",
                "dialogue",
                "image_prompt",
            ],
        },
    }

    outline_text = json.dumps(
        outline,
        ensure_ascii=False,
        indent=2,
    )

    prompt = f"""
You are an expert comic writer.

Create a polished five-panel educational/story comic.

CHARACTER:
{request.character_name}

SETTING:
{request.setting}

TONE:
{request.tone}

ART STYLE:
{request.art_style}

ORIGINAL STORY:
{request.story_prompt}

STORYBOARD:
{outline_text}

For every panel provide:

- panel_number
- title
- scene_description
- caption
- narration
- dialogue
- image_prompt

Writing requirements:

1. Keep the story concise.
2. Make the story understandable for students.
3. Keep the character consistent.
4. Dialogue should sound natural.
5. Captions should be short.
6. Narration should explain the scene clearly.
7. The image prompt should describe:
   - character
   - action
   - environment
   - composition
   - lighting
   - camera/view
   - art style
8. Never put readable text in the generated image.
9. Never include logos or watermarks.
10. Maintain continuity between panels.

Return ONLY valid JSON.
"""

    result = _generate_json(
        prompt=prompt,
        schema=schema,
    )

    if not isinstance(result, list):
        raise RuntimeError(
            "Gemini story response is not a list."
        )

    if len(result) != settings.panels_count:
        raise RuntimeError(
            "Gemini did not return the expected number of panels."
        )

    return result