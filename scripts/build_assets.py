"""Builds the animated SVGs for the profile README (header + four doors).

Run: python3 scripts/build_assets.py
Fonts (Bricolage Grotesque, DM Sans) are downloaded from Google Fonts, subset to
the characters used and embedded, so GitHub renders the SVGs exactly as designed.
"""
import base64, io, re, sys, urllib.request
from xml.sax.saxutils import escape
from pathlib import Path
from fontTools import subset
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "scripts/.cache"
OUT = ROOT / "assets"
PORTRAIT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "scripts/portrait.png"

INK, PAPER = "#111114", "#E6EDF3"
BLUE, ORANGE, PURPLE, GREEN = "#2F54EB", "#FF5B23", "#7B3FF2", "#0F8A5F"
PHRASES = [("build software.", BLUE), ("write tutorials.", ORANGE), ("make videos.", "#9B6BFF"), ("do research.", "#17A673")]
ROLES = "Software engineer · Technical writer · YouTuber · Computer-vision researcher"
DOORS = [
    ("software", "01", "Software", "9 live products, end to end", BLUE, "#FFFFFF"),
    ("writing", "02", "Writing", "DEV, freeCodeCamp & my blog", ORANGE, INK),
    ("content", "03", "Content", "Beginner Friendly Dev", PURPLE, "#FFFFFF"),
    ("research", "04", "Research", "Teaching machines to see", GREEN, "#FFFFFF"),
]


def font_file(family: str, weight: int) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{family.replace(' ', '')}-{weight}.ttf"
    if not path.exists():
        css_url = f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}"
        css = urllib.request.urlopen(urllib.request.Request(css_url, headers={"User-Agent": "Mozilla/5.0"})).read().decode()
        url = re.search(r"src: url\((https:[^)]+)\) format\('truetype'\)", css).group(1)
        path.write_bytes(urllib.request.urlopen(url).read())
    return path


def embedded(path: Path, text: str) -> str:
    """Subset a font to `text` and return it as a base64 data URI."""
    font = TTFont(path)
    options = subset.Options()
    options.layout_features = ["*"]
    sub = subset.Subsetter(options)
    sub.populate(text=text + " →.·,&'’")
    sub.subset(font)
    buf = io.BytesIO()
    font.save(buf)
    return "data:font/ttf;base64," + base64.b64encode(buf.getvalue()).decode()


def widths(path: Path, size: int, text: str) -> list[float]:
    """Cumulative advance width after each character, for the typing effect."""
    f = ImageFont.truetype(str(path), size)
    return [f.getlength(text[: i + 1]) for i in range(len(text))]


def portrait_uri(size: int = 360) -> str:
    """David's cutout on the Software blue, as a JPEG data URI."""
    src = Image.open(PORTRAIT).convert("RGBA")
    pad = Image.new("RGBA", (src.width, src.height + 40), (0, 0, 0, 0))
    pad.paste(src, (0, 40))
    crop = pad.crop((57, 0, 57 + 370, 370)).resize((size, size), Image.LANCZOS)
    bg = Image.new("RGBA", (size, size), BLUE)
    bg.alpha_composite(crop)
    buf = io.BytesIO()
    bg.convert("RGB").save(buf, "JPEG", quality=86)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def header(theme: str, display: Path, body: Path, photo: str) -> str:
    fg = INK if theme == "light" else PAPER
    muted = "#57606A" if theme == "light" else "#8B949E"
    W, H = 960, 240
    cx, cy, r = 120, 120, 92
    x0 = 262
    cycle = 12  # seconds for all four phrases
    slot = cycle / len(PHRASES)
    lead_w = widths(body, 30, "I ")[-1]

    phrases = []
    for i, (text, colour) in enumerate(PHRASES):
        cum = widths(body, 30, text)
        n = len(cum)
        type_end, hold_end, erase_end = 0.32 * slot, 0.82 * slot, 0.95 * slot
        # Discrete steps: type char by char, hold, delete char by char, then hide.
        times, vals = [0.0], [0.0]
        for k in range(n):
            times.append((k + 1) / n * type_end); vals.append(cum[k])
        times.append(hold_end); vals.append(cum[-1])
        for k in range(n - 1, -1, -1):
            times.append(hold_end + (n - k) / n * (erase_end - hold_end)); vals.append(cum[k - 1] if k else 0.0)
        times.append(slot); vals.append(0.0)
        # Map this phrase's slot into the full cycle.
        start = i * slot
        kt = [0.0] + [(start + t) / cycle for t in times] + [1.0]
        kv = [0.0] + vals + [0.0]
        # keyTimes must be non-decreasing and unique enough; nudge duplicates.
        for j in range(1, len(kt)):
            if kt[j] <= kt[j - 1]:
                kt[j] = min(1.0, kt[j - 1] + 1e-4)
        key_times = ";".join(f"{t:.4f}" for t in kt)
        widths_v = ";".join(f"{v:.1f}" for v in kv)
        caret_x = ";".join(f"{x0 + lead_w + v + 3:.1f}" for v in kv)
        vis = ";".join("1" if start <= t * cycle < start + erase_end + 0.001 else "0" for t in kt)
        phrases.append(f"""
    <clipPath id="c{i}"><rect x="{x0 + lead_w}" y="118" height="44" width="0">
      <animate attributeName="width" values="{widths_v}" keyTimes="{key_times}" dur="{cycle}s" calcMode="discrete" repeatCount="indefinite"/></rect></clipPath>
    <text x="{x0 + lead_w}" y="150" class="b" fill="{colour}" clip-path="url(#c{i})">{escape(text)}</text>
    <rect y="124" width="3" height="32" fill="{colour}" opacity="0">
      <animate attributeName="x" values="{caret_x}" keyTimes="{key_times}" dur="{cycle}s" calcMode="discrete" repeatCount="indefinite"/>
      <animate attributeName="opacity" values="{vis}" keyTimes="{key_times}" dur="{cycle}s" calcMode="discrete" repeatCount="indefinite"/>
    </rect>""")

    arcs = "".join(
        f'<circle cx="{cx}" cy="{cy}" r="{r + 8}" fill="none" stroke="{c}" stroke-width="6" stroke-linecap="round" '
        f'stroke-dasharray="{(2 * 3.14159 * (r + 8)) / 4 - 14:.1f} 1000" transform="rotate({i * 90 - 90} {cx} {cy})"/>'
        for i, c in enumerate([BLUE, ORANGE, PURPLE, GREEN])
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="Hi, I'm David Asaolu. I build software, write tutorials, make videos and do research.">
  <style>
    @font-face {{ font-family: Display; src: url({embedded(display, "Hi, I’m David")}); }}
    @font-face {{ font-family: Body; src: url({embedded(body, "I " + "".join(p for p, _ in PHRASES) + ROLES)}); }}
    .d {{ font-family: Display, system-ui, sans-serif; font-size: 70px; letter-spacing: -3px; }}
    .b {{ font-family: Body, system-ui, sans-serif; font-size: 30px; }}
    .s {{ font-family: Body, system-ui, sans-serif; font-size: 17px; }}
    .rise {{ animation: rise 1s cubic-bezier(.2,.8,.2,1) both; }}
    .rise2 {{ animation: rise 1s .15s cubic-bezier(.2,.8,.2,1) both; }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
    @media (prefers-reduced-motion: reduce) {{ .rise, .rise2 {{ animation: none; }} }}
  </style>
  <defs><clipPath id="face"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath></defs>
  <g>
    {arcs}
    <animateTransform attributeName="transform" type="rotate" from="0 {cx} {cy}" to="360 {cx} {cy}" dur="14s" repeatCount="indefinite"/>
  </g>
  <image href="{photo}" x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}" clip-path="url(#face)"/>
  <g class="rise"><text x="{x0}" y="96" class="d" fill="{fg}">Hi, I’m David<tspan fill="{ORANGE}">.</tspan></text></g>
  <g class="rise2">
    <text x="{x0}" y="150" class="b" fill="{fg}">I </text>{''.join(phrases)}
    <text x="{x0 + 2}" y="196" class="s" fill="{muted}">{escape(ROLES)}</text>
  </g>
</svg>
"""


def door(slug, num, label, sub, bg, fg, index, display: Path, body: Path) -> str:
    W, H = 240, 150
    delay = index * 0.35
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(label)}: {escape(sub)}">
  <style>
    @font-face {{ font-family: Display; src: url({embedded(display, label)}); }}
    @font-face {{ font-family: Body; src: url({embedded(body, num + sub)}); }}
    .card {{ animation: bob 4.2s {delay}s cubic-bezier(.3,.7,.2,1) infinite; transform-origin: center; }}
    .arrow {{ animation: nudge 4.2s {delay}s ease-in-out infinite; }}
    @keyframes bob {{ 0%, 70%, 100% {{ transform: translateY(0); }} 12% {{ transform: translateY(-7px); }} 24% {{ transform: translateY(0); }} }}
    @keyframes nudge {{ 0%, 70%, 100% {{ transform: translateX(0); }} 12% {{ transform: translateX(6px); }} }}
    @media (prefers-reduced-motion: reduce) {{ .card, .arrow {{ animation: none; }} }}
  </style>
  <g class="card">
    <rect x="4" y="10" width="{W - 8}" height="{H - 18}" rx="22" fill="{bg}"/>
    <text x="24" y="40" font-family="Body, monospace" font-size="14" fill="{fg}" opacity=".75">{num}</text>
    <text x="24" y="98" font-family="Display, system-ui, sans-serif" font-size="34" letter-spacing="-1.2" fill="{fg}">{escape(label)}<tspan class="arrow"> →</tspan></text>
    <text x="24" y="124" font-family="Body, system-ui, sans-serif" font-size="13.5" fill="{fg}" opacity=".85">{escape(sub)}</text>
  </g>
</svg>
"""


def main():
    display = font_file("Bricolage Grotesque", 800)
    body = font_file("DM Sans", 500)
    OUT.mkdir(exist_ok=True)
    photo = portrait_uri()
    for theme in ("dark", "light"):
        (OUT / f"header-{theme}.svg").write_text(header(theme, display, body, photo))
    for i, d in enumerate(DOORS):
        (OUT / f"door-{d[0]}.svg").write_text(door(*d, i, display, body))
    for f in sorted(OUT.glob("*.svg")):
        print(f.name, f"{f.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
