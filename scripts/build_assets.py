"""Generate the README's static SVG assets (link buttons + tech stack card) in dark and light themes.

Usage: python scripts/build_assets.py assets
"""
import re
import sys
from html import escape
from pathlib import Path

ICONS = Path(__file__).parent / "icons"
OUT = Path(sys.argv[1])

# GitHub's own font stack and Primer colours, so the assets read as native GitHub UI
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif"
ENVELOPE = "M2 4h20a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2zm0 2.2V18h20V6.2l-10 6.3L2 6.2zM3.6 6 12 11.3 20.4 6H3.6z"

# File suffix -> palette
THEMES = {
    "": {"card": "#0d1117", "chip": "#161b22", "border": "#30363d", "text": "#e6edf3", "muted": "#8b949e", "icon": "#8b949e"},
    "-light": {"card": "#ffffff", "chip": "#f6f8fa", "border": "#d0d7de", "text": "#1f2328", "muted": "#656d76", "icon": "#656d76"},
}

BUTTONS = [
    ("LinkedIn", "linkedin", "btn-linkedin"),
    ("Email", ENVELOPE, "btn-email"),
]

STACK = [
    ("Machine Learning", [("python", "Python"), ("pytorch", "PyTorch"), ("streamlit", "Streamlit"), ("latex", "LaTeX")]),
    ("Web", [("typescript", "TypeScript"), ("react", "React"), ("nextdotjs", "Next.js"), ("astro", "Astro"), ("tailwindcss", "Tailwind")]),
    ("Commerce & Cloud", [("shopify", "Shopify"), ("aws", "AWS"), ("vercel", "Vercel"), ("git", "Git")]),
    ("Systems & Apps", [("cplusplus", "C++"), ("dotnet", "C#"), ("openjdk", "Java"), ("swift", "Swift")]),
]


def icon_path(slug):
    svg = (ICONS / f"{slug}.svg").read_text(encoding="utf-8")
    return re.search(r'<path d="([^"]+)"', svg).group(1)


def text_width(s, size):
    # Rough Segoe UI advance width; good enough for chip sizing
    return sum(0.33 if c in "il.-'" else 0.62 if c.isupper() else 0.54 for c in s) * size


def icon(slug_or_path, x, y, size, fill):
    d = slug_or_path if slug_or_path.startswith("M") else icon_path(slug_or_path)
    s = size / 24
    return f'<path d="{d}" fill="{fill}" transform="translate({x:.1f} {y:.1f}) scale({s:.4f})"/>'


def button(t, label, glyph):
    w = 14 + 16 + 8 + text_width(label, 14) + 16
    h = 32
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h}" viewBox="0 0 {w:.0f} {h}">
  <rect x="0.5" y="0.5" width="{w - 1:.0f}" height="{h - 1}" rx="6" fill="{t['chip']}" stroke="{t['border']}"/>
  {icon(glyph, 14, 8, 16, t['icon'])}
  <text x="38" y="20.5" font-family="{FONT}" font-size="14" font-weight="500" fill="{t['text']}">{escape(label)}</text>
</svg>'''


def stack_card(t, groups):
    width, pad, label_w, row_h, chip_h, gap = 880, 20, 160, 40, 28, 8
    height = pad * 2 + 28 + row_h * len(groups) - (row_h - chip_h)
    parts = [
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="6" fill="{t["card"]}" stroke="{t["border"]}"/>',
        f'<text x="{pad}" y="{pad + 14}" font-family="{FONT}" font-size="14" font-weight="600" fill="{t["text"]}">Tech stack</text>',
    ]
    y = pad + 28
    for label, items in groups:
        parts.append(f'<text x="{pad}" y="{y + chip_h / 2 + 5}" font-family="{FONT}" font-size="13" font-weight="400" fill="{t["muted"]}">{escape(label)}</text>')
        x = pad + label_w
        for slug, name in items:
            w = 10 + 14 + 6 + text_width(name, 12) + 10
            parts.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="{chip_h}" rx="14" fill="{t["chip"]}" stroke="{t["border"]}"/>')
            parts.append(icon(slug, x + 10, y + 7, 14, t["icon"]))
            parts.append(f'<text x="{x + 30:.1f}" y="{y + 18.5}" font-family="{FONT}" font-size="12" font-weight="500" fill="{t["text"]}">{escape(name)}</text>')
            x += w + gap
        y += row_h
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  {chr(10).join("  " + p for p in parts)}
</svg>'''


for suffix, theme in THEMES.items():
    for label, glyph, name in BUTTONS:
        (OUT / f"{name}{suffix}.svg").write_text(button(theme, label, glyph), encoding="utf-8")
    (OUT / f"stack{suffix}.svg").write_text(stack_card(theme, STACK), encoding="utf-8")
print("ok")
