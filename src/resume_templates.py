"""
Resume Template Engine -- 10 visual templates.

Each template defines layout, fonts, colors, and section ordering.
Export functions live in src/resume_export.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TemplateStyle:
    """Visual configuration for a resume template."""

    id: str
    name: str
    description: str
    primary_color: tuple[int, int, int]  # RGB
    accent_color: tuple[int, int, int]
    heading_font: str
    body_font: str
    font_size_name: int
    font_size_heading: int
    font_size_subheading: int
    font_size_body: int
    line_spacing: float
    margin_left: float
    margin_right: float
    margin_top: float
    margin_bottom: float
    show_sidebar: bool = False
    sidebar_width: float = 55.0
    header_style: str = "centered"  # centered, left-aligned, banner
    section_divider: str = "line"  # line, space, dots, none
    columns: int = 1
    tags: list[str] = field(default_factory=list)


TEMPLATES: dict[str, TemplateStyle] = {
    "classic": TemplateStyle(
        id="classic",
        name="Classic Professional",
        description="Clean, traditional layout. Safe choice for corporate roles.",
        primary_color=(0, 0, 0),
        accent_color=(0, 51, 102),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=20,
        font_size_heading=13,
        font_size_subheading=11,
        font_size_body=10,
        line_spacing=5.5,
        margin_left=20,
        margin_right=20,
        margin_top=20,
        margin_bottom=15,
        header_style="centered",
        section_divider="line",
        tags=["corporate", "finance", "legal", "traditional"],
    ),
    "modern": TemplateStyle(
        id="modern",
        name="Modern Minimal",
        description="Sleek design with accent colors. Great for tech and startups.",
        primary_color=(51, 51, 51),
        accent_color=(0, 122, 204),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=22,
        font_size_heading=12,
        font_size_subheading=10,
        font_size_body=9,
        line_spacing=5.0,
        margin_left=18,
        margin_right=18,
        margin_top=15,
        margin_bottom=15,
        header_style="left-aligned",
        section_divider="space",
        tags=["tech", "startup", "modern", "clean"],
    ),
    "executive": TemplateStyle(
        id="executive",
        name="Executive Suite",
        description="Bold, authoritative layout for C-suite and VP-level roles.",
        primary_color=(25, 25, 25),
        accent_color=(128, 0, 0),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=24,
        font_size_heading=14,
        font_size_subheading=11,
        font_size_body=10,
        line_spacing=6.0,
        margin_left=22,
        margin_right=22,
        margin_top=22,
        margin_bottom=18,
        header_style="centered",
        section_divider="line",
        tags=["executive", "c-suite", "leadership", "director"],
    ),
    "creative": TemplateStyle(
        id="creative",
        name="Creative Portfolio",
        description="Eye-catching design with color accents. For design and creative roles.",
        primary_color=(60, 60, 60),
        accent_color=(230, 126, 34),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=22,
        font_size_heading=13,
        font_size_subheading=10,
        font_size_body=9,
        line_spacing=5.0,
        margin_left=15,
        margin_right=15,
        margin_top=15,
        margin_bottom=15,
        show_sidebar=True,
        sidebar_width=55,
        header_style="banner",
        section_divider="none",
        tags=["design", "creative", "marketing", "portfolio"],
    ),
    "technical": TemplateStyle(
        id="technical",
        name="Technical Engineer",
        description="Structured layout optimized for listing technical skills and projects.",
        primary_color=(40, 40, 40),
        accent_color=(39, 174, 96),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=18,
        font_size_heading=12,
        font_size_subheading=10,
        font_size_body=9,
        line_spacing=5.0,
        margin_left=16,
        margin_right=16,
        margin_top=14,
        margin_bottom=14,
        header_style="left-aligned",
        section_divider="line",
        tags=["engineering", "developer", "data-science", "devops"],
    ),
    "academic": TemplateStyle(
        id="academic",
        name="Academic CV",
        description="Formal CV format for research, teaching, and academic positions.",
        primary_color=(0, 0, 0),
        accent_color=(0, 0, 128),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=16,
        font_size_heading=13,
        font_size_subheading=11,
        font_size_body=10,
        line_spacing=5.5,
        margin_left=25,
        margin_right=25,
        margin_top=25,
        margin_bottom=20,
        header_style="left-aligned",
        section_divider="line",
        tags=["academic", "research", "professor", "phd"],
    ),
    "compact": TemplateStyle(
        id="compact",
        name="Compact One-Page",
        description="Dense single-page layout. Perfect for early career or career changers.",
        primary_color=(50, 50, 50),
        accent_color=(52, 73, 94),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=16,
        font_size_heading=11,
        font_size_subheading=9,
        font_size_body=8,
        line_spacing=4.0,
        margin_left=12,
        margin_right=12,
        margin_top=10,
        margin_bottom=10,
        header_style="left-aligned",
        section_divider="space",
        tags=["compact", "entry-level", "career-change", "one-page"],
    ),
    "elegant": TemplateStyle(
        id="elegant",
        name="Elegant Serif",
        description="Sophisticated serif-style layout. Great for consulting and finance.",
        primary_color=(30, 30, 30),
        accent_color=(102, 51, 153),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=20,
        font_size_heading=13,
        font_size_subheading=11,
        font_size_body=10,
        line_spacing=5.5,
        margin_left=22,
        margin_right=22,
        margin_top=20,
        margin_bottom=18,
        header_style="centered",
        section_divider="dots",
        tags=["consulting", "finance", "elegant", "sophisticated"],
    ),
    "bold": TemplateStyle(
        id="bold",
        name="Bold Impact",
        description="Strong typography with high contrast. For sales, marketing, business dev.",
        primary_color=(20, 20, 20),
        accent_color=(192, 57, 43),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=24,
        font_size_heading=14,
        font_size_subheading=11,
        font_size_body=10,
        line_spacing=5.5,
        margin_left=18,
        margin_right=18,
        margin_top=16,
        margin_bottom=16,
        header_style="banner",
        section_divider="line",
        tags=["sales", "marketing", "business", "bold"],
    ),
    "ats_optimized": TemplateStyle(
        id="ats_optimized",
        name="ATS-Optimized",
        description="Maximum ATS compatibility. No graphics, clean structure, standard fonts.",
        primary_color=(0, 0, 0),
        accent_color=(0, 0, 0),
        heading_font="Helvetica",
        body_font="Helvetica",
        font_size_name=16,
        font_size_heading=13,
        font_size_subheading=11,
        font_size_body=10,
        line_spacing=5.5,
        margin_left=20,
        margin_right=20,
        margin_top=20,
        margin_bottom=15,
        header_style="left-aligned",
        section_divider="line",
        tags=["ats", "applicant-tracking", "safe", "compatible"],
    ),
}


def list_templates() -> list[dict[str, Any]]:
    """Return metadata for all available templates."""
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "tags": t.tags,
            "header_style": t.header_style,
            "columns": t.columns,
        }
        for t in TEMPLATES.values()
    ]


def get_template(template_id: str) -> TemplateStyle:
    """Retrieve a template by ID, defaulting to 'classic'."""
    return TEMPLATES.get(template_id, TEMPLATES["classic"])
