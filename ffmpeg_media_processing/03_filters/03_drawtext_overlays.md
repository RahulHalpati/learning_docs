# 03-3 · Text & overlays

> **Level:** Intermediate · **Prerequisites:** [03-2 · Scale, crop & vertical video](02_scale_crop_vertical.md)
> **Time:** 45 min · **Verified:** 2026-08-07 · ffmpeg 4.4.2

## Why this matters

Titles, watermarks, progress bars, hook text on a Short, a logo in the corner — all of it is `drawtext` and `overlay`. These two filters cover most of what people think of as "video editing", and neither needs an editor.

---

## drawtext

```bash
ffmpeg -y -i sample.mp4 -vf \
  "drawtext=text='CLIP 01':x=20:y=20:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5" \
  -an -t 1 d1.mp4
```

**Output (real run):**
```
  d1 ok: 11968 bytes
```

`box=1:boxcolor=black@0.5` draws a half-transparent background behind the text. **Use it or an outline on anything overlaid on video** — white text on a shot that cuts to a bright sky becomes invisible, and you won't notice in testing because your test clip is one scene.

### The options worth knowing

| Option | Does |
|--------|------|
| `text` | the string (escape `:` `'` `%` `\`) |
| `textfile` | read from a file — avoids escaping entirely |
| `fontfile` | path to a `.ttf` |
| `font` | family name, needs fontconfig |
| `fontsize` | points; accepts expressions like `h/20` |
| `fontcolor` | name, `#RRGGBB`, or `white@0.8` for alpha |
| `x`, `y` | position; expressions allowed |
| `box`, `boxcolor`, `boxborderw` | background box |
| `borderw`, `bordercolor` | outline |
| `shadowx`, `shadowy`, `shadowcolor` | drop shadow |
| `line_spacing` | gap between lines |
| `enable` | **when** to draw it |

### Positioning expressions

These make a graphic work at any resolution:

| Expression | Position |
|------------|----------|
| `x=(w-tw)/2` | horizontally centred |
| `y=(h-th)/2` | vertically centred |
| `y=h-th-30` | 30px above the bottom |
| `x=w-tw-20` | 20px from the right |

`w`/`h` are the video's dimensions, `tw`/`th` the rendered text's. Hardcoding pixel positions works until someone uploads a different resolution.

```bash
ffmpeg -y -i sample.mp4 -vf \
  "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:\
text='Explicit font':x=(w-tw)/2:y=h-th-30:fontsize=32:fontcolor=yellow" -an -t 1 d2.mp4
```

**Output (real run):**
```
  using: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
  d2 ok: 16102 bytes
```

> ⚠️ **Always pass an explicit `fontfile` in production.** Without one, drawtext asks fontconfig for a default — which resolves differently on your laptop, your CI runner, and your Docker image, and in a slim container often resolves to nothing at all (*"Cannot find a valid font"*). Ship a font file with your application and reference it by path. This is one of the most common "works locally, fails in Docker" video bugs.

Find yours with:

```bash
fc-list | grep -i dejavu
```

**Output (real run):**
```
/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf: DejaVu Sans:style=Book
```

### Timed text with `enable`

```bash
ffmpeg -y -i sample.mp4 -vf \
  "drawtext=text='only 1-3s':x=20:y=60:fontsize=24:fontcolor=white:enable='between(t,1,3)'" \
  -an d3.mp4
```

`t` is the timestamp in seconds. This is what makes drawtext usable for real titling rather than just watermarks:

```bash
enable='between(t,1,3)'      # visible from 1s to 3s
enable='lt(t,5)'             # first 5 seconds only
enable='gt(t,10)'            # after 10 seconds
```

> **Tip:** You *can* build a whole captioning system out of chained `drawtext` filters with `enable` ranges — and people do, then discover the command line is 40 KB long and a single typo is unfindable. Subtitles are the right tool for timed text ([04](../04_subtitles/README.md)); `enable` is for the handful of fixed titles.

---

## overlay — compositing images and video

```bash
ffmpeg -y -i sample.mp4 -i logo.png -filter_complex "[0:v][1:v]overlay=W-w-20:20" -an out.mp4
```

**Output (real run):**
```
  d4 ok: 11411 bytes
```

`overlay=X:Y` where **uppercase `W`/`H` is the background and lowercase `w`/`h` the overlaid image**. So `W-w-20:20` is "20px from the right edge, 20px from the top". PNG alpha is respected automatically.

| Expression | Corner |
|------------|--------|
| `10:10` | top-left |
| `W-w-10:10` | top-right |
| `10:H-h-10` | bottom-left |
| `(W-w)/2:(H-h)/2` | centre |

Useful variants:

```bash
# fade a watermark in after 2s
-filter_complex "[0:v][1:v]overlay=W-w-20:20:enable='gt(t,2)'"

# scale the logo first
-filter_complex "[1:v]scale=120:-1[lg];[0:v][lg]overlay=W-w-20:20"

# picture-in-picture
-filter_complex "[1:v]scale=iw/4:-1[pip];[0:v][pip]overlay=W-w-20:H-h-20"
```

---

## A progress bar

Worth showing because it demonstrates that filter expressions can be *animated* — no keyframes, no timeline, just maths on `t`:

```bash
ffmpeg -y -i sample.mp4 -vf \
  "drawbox=x=0:y=ih-8:w=iw*t/10:h=8:color=red@0.9:t=fill" -an progress.mp4
```

`w=iw*t/10` makes the box width grow from 0 to the full width over 10 seconds (the clip's duration). The same trick drives countdown timers, animated reveals, and sliding lower-thirds.

---

## Text safety for social video

Platform UI covers parts of the frame. Keep text inside the safe area:

```bash
# 9:16 — clear of the top bar and the bottom caption/button area
-vf "drawtext=...:y=h*0.15"        # top text
-vf "drawtext=...:y=h*0.75"        # bottom text
```

Roughly the top 10% and bottom 20% of a vertical video are covered by the app's own interface on at least one platform. Anything important there gets hidden — which is why the capstone's caption default is `MarginV=40` rather than flush to the bottom ([04-2](../04_subtitles/02_burning_captions.md)).

---

## Recap & next

- ✅ `drawtext` handles titles and watermarks; **always add `box=1` or `borderw`** so text stays legible over changing footage.
- ✅ **Always pass an explicit `fontfile`** — fontconfig defaults differ across machines and are often absent in containers.
- ✅ Position with **expressions** (`(w-tw)/2`, `h-th-30`), never hardcoded pixels.
- ✅ `enable='between(t,a,b)'` gives timed text — but use **subtitles** for anything more than a few titles.
- ✅ `overlay=X:Y` uses **uppercase for the background, lowercase for the overlay**; alpha just works.
- ✅ Expressions can animate on `t` — a progress bar is one `drawbox`.
- ✅ Keep text out of the **top 10% / bottom 20%** of vertical video.
- ✅ Self-check: your title renders locally and vanishes in Docker. First thing to check?

→ Next: **[04 · Subtitles & captions](../04_subtitles/README.md)**

## Exercises

1. Add a centred title visible only for the first 2 seconds, with a readable background.

<details>
<summary>Solution</summary>

```bash
ffmpeg -y -i sample.mp4 -vf \
  "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:\
text='My Title':x=(w-tw)/2:y=(h-th)/2:fontsize=48:fontcolor=white:\
box=1:boxcolor=black@0.6:boxborderw=12:enable='lt(t,2)'" -c:a copy out.mp4
```
`boxborderw=12` pads the box beyond the glyph bounds — without it the background hugs the text so tightly it looks like a mistake.
</details>

2. Why does `text='Time: 10:30'` fail, and what are two fixes?

<details>
<summary>Solution</summary>

The `:` characters are parsed as filter-argument separators, so ffmpeg sees `text='Time'` followed by nonsense options. Fixes:

1. Escape them: `text='Time\: 10\:30'`
2. Use `textfile=title.txt` and put the raw string in the file — no escaping at all.

The second is better for anything user-supplied, because it removes the entire escaping problem rather than requiring you to get it right for every possible input.
</details>
