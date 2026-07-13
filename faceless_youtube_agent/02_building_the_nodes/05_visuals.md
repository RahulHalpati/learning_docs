# 02-5 · Visuals

> **Level:** Beginner · **Time:** 25 min

The visuals node renders **one slide per segment** with Pillow — no LLM, no
network, no external font files. This is `visuals` in
[`nodes.py`](../99_project_faceless_studio/faceless_studio/nodes.py) and
`render_slide` in [`media.py`](../99_project_faceless_studio/faceless_studio/media.py).

---

## The node

```python
def visuals(state, *, workdir: Path) -> dict:
    img_dir = Path(workdir) / "slides"
    segments = [dict(s) for s in state["segments"]]
    total = len(segments)
    paths = []
    for i, seg in enumerate(segments):
        path = img_dir / f"slide_{i:02d}.png"
        media.render_slide(seg["heading"], seg.get("visual_hint", ""),
                           path, index=i, total=total)
        seg["image_path"] = str(path)
        paths.append(str(path))
    return {"segments": segments, "image_paths": paths, "log": ["visuals"]}
```

---

## Rendering a slide with Pillow

```python
from PIL import Image, ImageDraw, ImageFont
import textwrap

WIDTH, HEIGHT = 1280, 720

def _font(size):
    # Pillow 10+ gives a scalable default font with no external .ttf needed
    return ImageFont.load_default(size=size)

def render_slide(heading, subtitle, out_path, *, index=None, total=None):
    img = Image.new("RGB", (WIDTH, HEIGHT), (14, 17, 23))   # near-black bg
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, WIDTH, 10], fill=(88, 166, 255))  # accent bar

    h_font = _font(64)
    y = 190
    for line in textwrap.wrap(heading, width=24) or [""]:
        w = draw.textlength(line, font=h_font)
        draw.text(((WIDTH - w) / 2, y), line, font=h_font, fill=(240, 246, 252))
        y += 78

    s_font = _font(34)
    for line in textwrap.wrap(subtitle, width=52)[:4]:
        w = draw.textlength(line, font=s_font)
        draw.text(((WIDTH - w) / 2, y + 20), line, font=s_font, fill=(139, 148, 158))
        y += 46

    if index is not None and total is not None:
        draw.text((WIDTH - 110, HEIGHT - 50), f"{index+1} / {total}",
                  font=_font(24), fill=(88, 166, 255))
    img.save(out_path)
    return str(out_path)
```

Key details that make it "just work":

- **`ImageFont.load_default(size=64)`** — Pillow 10+ ships a scalable default font,
  so you get large, crisp text **without hunting for a `.ttf`** on the user's
  machine. (On ancient Pillow it falls back to the fixed bitmap.)
- **`textwrap.wrap`** — long headings wrap instead of running off the 1280px edge.
- **16:9 at 1280×720** — YouTube's standard aspect; bump `WIDTH, HEIGHT` to
  `1920, 1080` for full HD uploads (nothing else changes).

Every slide is centered, high-contrast, and carries a `n / total` progress tag —
minimal but genuinely watchable.

---

## The real upgrade: images and B-roll

A slide is the *offline* visual. For a real channel you'd swap `render_slide` for
one of:

- **AI images** — generate per-segment art from `visual_hint` with a local Stable
  Diffusion (SDXL) or a hosted image API; save one PNG per segment. Node signature
  is unchanged.
- **Stock B-roll** — pull clips from Pexels/Pixabay by keyword (`visual_hint`), and
  have the assembler use video clips instead of stills.
- **Screen recordings / charts** — for tech content, render code or diagrams.

Because the node's contract is "produce a file path per segment," any of these
drops in without touching the assembler.

---

## Recap

- One node renders **one slide per segment** with pure Pillow — no fonts to install.
- `load_default(size=…)` (Pillow 10+) gives scalable text with zero asset hunting.
- Swap `render_slide` for AI images or stock B-roll later; the **contract
  (one file per segment) stays the same.**

## Exercise

Give the slide a subtle vertical gradient background instead of a flat color, and
render the segment's **narration** (wrapped, smaller) beneath the heading so the
slide doubles as a caption. Keep it readable at 720p.

<details>
<summary>Hint</summary>

For the gradient, draw horizontal lines from top to bottom interpolating two RGB
colors. For captions, `textwrap.wrap(narration, width=60)` and draw the first few
lines below the heading in the subtitle font. Watch total height so text doesn't
overflow 720px.

</details>

---

**Next → [02-6 · Assembler](06_assembler.md)**
