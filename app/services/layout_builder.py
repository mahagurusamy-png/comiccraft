from app.schemas import Panel


def build_comic_layout(
    story: list[dict],
    image_paths: list[str],
) -> list[Panel]:
    """
    Combine story information and
    generated image paths.
    """

    if len(story) != len(image_paths):
        raise ValueError(
            "Story panel count and image count do not match."
        )

    panels = []

    for item, image_path in zip(
        story,
        image_paths,
    ):

        panel = Panel(
            **item,
            image_path=image_path,
        )

        panels.append(panel)

    return panels