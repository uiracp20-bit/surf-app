#!/usr/bin/env python3
"""
Generate mobile.html deterministically from index.html.

The desktop dashboard (index.html) is the single source of truth. Running this
script regenerates the mobile view (hero card + best→worst accordion) so the
two can never drift out of sync.

Updated to handle the redesigned desktop layout (wind-bar, shark-bar,
section-title, cond-card, fc-row, etc.).
"""
import re
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "index.html"
OUT = HERE / "mobile.html"

NAMES = {"deewhy": "Dee Why", "longreef": "Long Reef", "curlcurl": "Curl Curl"}
ORDER = ["deewhy", "longreef", "curlcurl"]


def grab(pattern, text, flags=re.S, group=1, default=""):
    m = re.search(pattern, text, flags)
    return m.group(group).strip() if m else default


def main():
    html = SRC.read_text(encoding="utf-8")

    # --- shared chrome pulled verbatim from desktop ---
    desktop_css = grab(r"<style>(.*?)</style>", html)

    # Wind/alert bar — new design uses .wind-bar
    wind_bar = grab(r'(<div class="wind-bar"[^>]*>.*?</div>)', html)
    # Fallback to old .alert-bar if redesign not present
    if not wind_bar:
        wind_bar = grab(r'(<div class="alert-bar.*?</div>)', html)

    # Shark bar
    shark_bar = grab(r'(<div class="shark-bar[^"]*"[^>]*>.*?</div>)', html)

    # Footer date line
    footer_line = grab(r'<div class="footer">\s*(.*?)<br>', html, default="")

    # --- split the three per-spot blocks on the section comment markers ---
    # Support both old (<!-- FOOTER -->) and new (<!-- Footer -->) markers
    markers = [
        r"<!-- ===== DEE WHY ===== -->",
        r"<!-- ===== LONG REEF ===== -->",
        r"<!-- ===== CURL CURL ===== -->",
        r"<!-- [Ff]ooter -->",
    ]
    try:
        bounds = [re.search(m, html).start() for m in markers]
    except AttributeError:
        print("ERROR: Could not find section markers in index.html", file=sys.stderr)
        return 1

    blocks = {
        "deewhy":   html[bounds[0]:bounds[1]],
        "longreef": html[bounds[1]:bounds[2]],
        "curlcurl": html[bounds[2]:bounds[3]],
    }

    spots = {}
    for sid in ORDER:
        b = blocks[sid]

        # --- Rating: try new layout first, fall back to old ---
        # New: <div class="rating-label">⭐⭐ FAIR</div>
        rating_label = grab(r'<div class="rating-label">(.*?)</div>', b)
        if rating_label:
            star_count = rating_label.count("⭐")
            stars = "⭐" * star_count + "☆" * (5 - star_count)
            badge_text = re.sub(r"^[⭐☆\s]+", "", rating_label).strip().title()
        else:
            # Old: <div class="stars">⭐⭐⭐☆☆</div>
            stars_raw = grab(r'<div class="stars">(.*?)</div>', b)
            star_count = stars_raw.count("⭐")
            stars = stars_raw or ("⭐" * star_count + "☆" * (5 - star_count))
            badge_raw = re.search(r'<span class="condition-badge[^"]*">(.*?)</span>', b, re.S)
            badge_text = badge_raw.group(1).strip() if badge_raw else "Fair"

        badge_class = (
            "badge-epic" if star_count >= 5 else
            "badge-good" if star_count >= 4 else
            "badge-fair" if star_count >= 2 else
            "badge-poor"
        )

        # --- Surf size ---
        # New: <div class="ft" ...>2–3ft</div>
        size = grab(r'<div class="ft"[^>]*>(.*?)</div>', b)
        if not size:
            # Old: <div class="surf-size">
            size = grab(r'<div class="surf-size">(.*?)</div>', b)

        # --- Description (waist to chest, etc.) ---
        # New: inline div after rating-label with style attribute
        desc = grab(r'class="rating-label">.*?</div>\s*<div style="[^"]*">(.*?)</div>', b)
        if not desc:
            desc = grab(r'<div class="surf-desc">(.*?)</div>', b)

        # --- Energy ---
        # New: Energy label followed by cond-value containing digits + kJ
        energy_str = grab(r'Energy</div>\s*<div class="cond-value">([\d]+)\s*kJ', b, default="0")
        if energy_str == "0":
            # Old: Wave Energy label
            energy_str = grab(r'Wave Energy</div>\s*<div class="cond-val">(\d+)', b, default="0")
        energy = int(energy_str) if energy_str.isdigit() else 0

        # --- Wind ---
        # New
        wind = grab(r'Wind</div>\s*<div class="cond-value">(.*?)</div>', b)
        if not wind:
            # Old
            wind = grab(r'Wind</div>\s*<div class="cond-val">(.*?)</div>', b)

        # --- Consistency ---
        # New: "65/100 consistency" in cond-sub
        consistency = grab(r'(\d+/100)\s*consistency', b)
        if not consistency:
            consistency = grab(r'Consistency</div>\s*<div class="cond-val">(.*?)</div>', b)

        # --- Session summary ---
        # New: session-best
        summary = grab(r'<div class="session-best">(.*?)</div>', b)
        if not summary:
            # Old: session-good or session-warn
            summary = re.sub(r"^[^A-Za-z🟢🟡⚠️]+", "",
                             grab(r'<div class="session-(?:good|warn)">(.*?)</div>', b))

        # --- Full detail cards block to embed in accordion ---
        # New: from first section-title (Conditions) to the Surfline </a>
        cards = grab(r'(<div class="section-title">Conditions</div>.*</a>)', b)
        if not cards:
            # Old: from <!-- Conditions Grid --> to </a>
            cards = grab(r"(<!-- Conditions Grid -->.*</a>)", b)

        spots[sid] = {
            "id": sid,
            "name": NAMES[sid],
            "stars": stars,
            "star_count": star_count,
            "badge_class": badge_class,
            "badge_text": badge_text,
            "size": size,
            "desc": desc,
            "energy": energy,
            "wind": wind,
            "consistency": consistency,
            "summary": summary,
            "cards": cards,
        }

    # rank best -> worst: more stars wins, then more wave energy
    ranked = sorted(spots.values(), key=lambda s: (-s["star_count"], -s["energy"]))
    hero = ranked[0]

    # --- assemble accordion ---
    accordion = []
    for i, s in enumerate(ranked):
        open_cls = " open" if i == 0 else ""
        accordion.append(f'''  <div class="spot{open_cls}" onclick="toggleSpot(this)">
    <div class="spot-head">
      <div class="spot-rank">{i + 1}</div>
      <div class="spot-name">{s["name"]}</div>
      <div class="spot-quick">
        <div class="spot-stars">{s["stars"]}</div>
        <div class="spot-size">{s["size"]}</div>
      </div>
      <div class="spot-chev">›</div>
    </div>
    <div class="spot-body" onclick="event.stopPropagation()">
      {s["cards"]}
    </div>
  </div>''')
    accordion_html = "\n".join(accordion)

    page = f'''<!DOCTYPE html><script type="application/json" id="cowork-artifact-meta">
{{
  "name": "Uira Surf Dashboard — Mobile",
  "schemaVersion": 1,
  "description": "Glanceable mobile surf check for Dee Why, Long Reef & Curl Curl — auto-generated mirror of the desktop dashboard"
}}
</script>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#0077b6">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Surf">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon.svg">
<title>Surf Check</title>
<!-- AUTO-GENERATED FROM index.html BY build_mobile.py — DO NOT EDIT BY HAND -->
<style>
{desktop_css}

  /* ===== MOBILE SHELL (overrides desktop base) ===== */
  body {{ max-width: 100%; padding-bottom: env(safe-area-inset-bottom); }}

  .hero {{ background: linear-gradient(135deg, #0077b6 0%, #023e8a 100%); color: white; border-radius: 14px; padding: 16px 16px 14px; box-shadow: 0 6px 18px rgba(0,119,182,0.3); margin: 12px 12px 10px; }}
  .hero-tag {{ font-size: 10px; font-weight: 800; letter-spacing: 1.2px; color: rgba(255,255,255,0.75); text-transform: uppercase; margin-bottom: 4px; }}
  .hero-spot {{ font-size: 28px; font-weight: 900; line-height: 1.05; }}
  .hero-row {{ display: flex; align-items: baseline; gap: 10px; margin-top: 4px; flex-wrap: wrap; }}
  .hero-stars {{ font-size: 15px; }}
  .hero-size {{ font-size: 15px; font-weight: 800; color: rgba(255,255,255,0.9); }}
  .hero-meta {{ font-size: 12px; color: rgba(255,255,255,0.8); margin-top: 8px; line-height: 1.4; }}
  .hero-stat {{ display: inline-block; margin-top: 10px; background: rgba(255,255,255,0.18); border: 1px solid rgba(255,255,255,0.3); border-radius: 20px; padding: 4px 12px; font-size: 12px; font-weight: 700; }}

  .sec-label {{ font-size: 11px; font-weight: 700; color: #718096; text-transform: uppercase; letter-spacing: 0.8px; margin: 4px 12px 8px; }}

  .spot {{ background: white; border-radius: 12px; margin: 0 12px 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); overflow: hidden; }}
  .spot-head {{ display: flex; align-items: center; gap: 10px; padding: 14px; cursor: pointer; user-select: none; }}
  .spot-rank {{ width: 26px; height: 26px; border-radius: 50%; background: #ebf4ff; color: #0077b6; font-size: 13px; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .spot-name {{ font-size: 16px; font-weight: 800; flex: 1; }}
  .spot-quick {{ text-align: right; }}
  .spot-stars {{ font-size: 12px; line-height: 1; }}
  .spot-size {{ font-size: 14px; font-weight: 800; color: #0077b6; margin-top: 2px; }}
  .spot-chev {{ color: #cbd5e0; font-size: 18px; margin-left: 6px; transition: transform 0.25s; flex-shrink: 0; }}
  .spot.open .spot-chev {{ transform: rotate(90deg); color: #0077b6; }}
  .spot-body {{ display: none; padding: 0 4px 12px; border-top: 1px solid #edf2f7; }}
  .spot.open .spot-body {{ display: block; }}
  .spot-body .rating-banner {{ display: none; }}
  .spot-body .tab-content {{ display: block !important; padding: 0; }}
  .footer-wrap {{ margin: 0 12px 20px; border-radius: 8px; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <div>
      <div class="header h1" style="font-size:17px;font-weight:700;">🏄 This Morning</div>
      <div class="sub">Dee Why · Long Reef · Curl Curl</div>
    </div>
    <div class="clock" id="clock">--:--</div>
  </div>
</div>

{wind_bar}

{shark_bar}

<div class="hero">
  <div class="hero-tag">🌟 Best pick right now</div>
  <div class="hero-spot">{hero["name"]}</div>
  <div class="hero-row">
    <span class="hero-stars">{hero["stars"]}</span>
    <span class="hero-size">{hero["size"]} · {hero["desc"]}</span>
  </div>
  <div class="hero-meta">{hero["summary"]}</div>
  <span class="hero-stat">{hero["wind"]} · {hero["energy"]}kJ · {hero["consistency"]}</span>
</div>

<div class="sec-label">All spots · tap to expand</div>

{accordion_html}

<div class="footer footer-wrap">
  {footer_line}<br>
  <a href="index.html">⤢ Open full desktop dashboard</a>
</div>

<script>
  function toggleSpot(el) {{ el.classList.toggle('open'); }}

  function updateClock() {{
    var t = new Intl.DateTimeFormat('en-AU', {{
      timeZone: 'Australia/Sydney', hour: '2-digit', minute: '2-digit', hour12: false
    }}).format(new Date());
    document.getElementById('clock').textContent = t + ' AEST';
  }}
  updateClock();
  setInterval(updateClock, 30000);

  if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
</script>
</body>
</html>
'''

    OUT.write_text(page, encoding="utf-8")
    order_str = " > ".join(f"{s['name']}({s['star_count']}★/{s['energy']}kJ)" for s in ranked)
    print(f"mobile.html regenerated. Best pick: {hero['name']}. Rank: {order_str}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
