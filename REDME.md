# ComicCraft

ComicCraft is a Generative AI based comic story creator.

The application accepts a story idea and generates a five-panel comic using:

- FastAPI
- Jinja2
- Gemini
- Hugging Face image generation
- Pillow
- FPDF2

---

## Project Flow

User Story
    ↓
Gemini Storyboard
    ↓
Five Comic Panels
    ↓
Gemini Story + Dialogue
    ↓
AI Image Generation
    ↓
Comic Preview
    ↓
PDF Export

---

# Requirements

Install:

- Python 3.11+
- VS Code
- Internet connection
- Gemini API key

Optional:

- Hugging Face API token

---

# Installation

Create virtual environment.

Windows:

```powershell
py -3.11 -m venv .venv