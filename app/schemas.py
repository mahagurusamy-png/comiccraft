from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PromptRequest(BaseModel):
    story_prompt: str = Field(
        ...,
        min_length=5,
        max_length=1000,
    )

    character_name: str = Field(
        ...,
        min_length=1,
        max_length=80,
    )

    setting: str = Field(
        ...,
        min_length=1,
        max_length=120,
    )

    tone: str = Field(
        ...,
        min_length=1,
        max_length=40,
    )

    art_style: str = Field(
        ...,
        min_length=1,
        max_length=80,
    )

    @field_validator(
        "story_prompt",
        "character_name",
        "setting",
        "tone",
        "art_style",
    )
    @classmethod
    def strip_values(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty.")

        return value


class Panel(BaseModel):
    panel_number: int
    title: str
    scene_description: str
    caption: str
    narration: str
    dialogue: str = ""
    image_prompt: str
    image_path: Optional[str] = None


class ComicResponse(BaseModel):
    title: str
    panels: list[Panel]
    pdf_path: Optional[str] = None