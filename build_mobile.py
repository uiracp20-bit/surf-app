#!/usr/bin/env python3
"""
Generate mobile.html deterministically from index.html.

The desktop dashboard (index.html) is the single source of truth. The daily 6am
task only has to update index.html; running this script regenerates the mobile
view so the two can never drift out of sync again.

The mobile view = a "best pick" hero card + an accordion of all 3 spots ranked
best->worst, each expanding to the EXACT desktop card markup for that spot. It
reuses the desktop <style> verbatim so any embedded card renders identically,
then layers on the mobile shell (header / hero / accordion).
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
    alert_bar = grab(r'(<div class="alert-bar.*?\n</div>)', html)
    shark_bar = grab(r'(<div class="shark-bar.*?\n</div>)', html)
    footer_date = grab(r"</strong><br>\s*(.*?)<br>", html, default="")

    # --- split the three per-spot blocks on the section comment markers ---
    markers = [
        r"<!-- ===== DEE WHY ===== -->",
        r"<!-- ===== LONG REEF ===== -->",
        r"<!-- ===== CURL CURL ===== -->",
        r"<!-- FOOTER -->",
    ]
    bounds = [re.search(m, html).start() for m in markers]
    blocks = {
        "deewhy": html[bounds[0]:bounds[1]],
        "longreef": html[bounds[1]:bounds[2]],
        "curlcurl": html[bounds[2]:bounds[3]],
    }

    spots = {}
    for sid in ORDER:
        b = blocks[sid]
        stars = grab(r'<div class="stars">(.*?)</div>', b)
        badge = re.search(r'<span class="condition-badge (badge-[\w-]+)">(.*?)</span>', b, re.S)
        energy = grab(r'Wave Energy</div>\s*<div class="cond-val">(\d+)', b, default="0")
        cards = grab(r"(<!-- Conditions Grid -->.*</a>)", b)
        spots[sid] = {
            "id": sid,
            "name": NAMES[sid],
            "stars": stars,
            "star_count": stars.count("⭐"),
            "badge_class": badge.group(1) if badge else "badge-poor-fair",
            "badge_text": badge.group(2).strip() if badge else "",
            "size": grab(r'<div class="surf-size">(.*?)</div>', b),
            "desc": grab(r'<div class="surf-desc">(.*?)</div>', b),
            "energy": int(energy),
            "wind": grab(r'Wind</div>\s*<div class="cond-val">(.*?)</div>', b),
            "consistency": grab(r'Consistency</div>\s*<div class="cond-val">(.*?)</div>', b),
            "summary": re.sub(r"^[^A-Za-z]+", "", grab(r'<div class="session-(?:good|warn)">(.*?)</div>', b)),
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
      <div style="margin-top:12px"><span class="condition-badge {s["badge_class"]}">{s["badge_text"]}</span></div>
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
<html lang="en" style="color-scheme: light;">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<meta name="theme-color" content="#0a2744">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Surf">
<link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon.svg">
<title>Surf — This Morning</title>
<!-- AUTO-GENERATED FROM index.html BY build_mobile.py — DO NOT EDIT BY HAND -->
<style>
{desktop_css}

  /* ===== MOBILE SHELL (overrides the desktop base above) ===== */
  body {{ font-size: 14px; padding-bottom: env(safe-area-inset-bottom); }}
  .header {{ padding: calc(14px + env(safe-area-inset-top)) 16px 12px; }}
  .header-title {{ font-size: 18px; }}
  .clock {{ font-size: 20px; }}
  .wrap {{ padding: 12px 12px 24px; }}

  .hero {{ background: linear-gradient(135deg, #1a4a7a 0%, #2b6cb0 100%); color: white; border-radius: 16px; padding: 16px 16px 14px; box-shadow: 0 6px 18px rgba(26,74,122,0.3); margin-bottom: 14px; }}
  .hero-tag {{ font-size: 11px; font-weight: 800; letter-spacing: 1.2px; color: #bee3f8; text-transform: uppercase; }}
  .hero-spot {{ font-size: 30px; font-weight: 900; line-height: 1.05; margin-top: 4px; }}
  .hero-row {{ display: flex; align-items: baseline; gap: 10px; margin-top: 4px; flex-wrap: wrap; }}
  .hero-stars {{ font-size: 17px; }}
  .hero-size {{ font-size: 16px; font-weight: 800; color: #ebf8ff; }}
  .hero-meta {{ font-size: 13px; color: #cfe8ff; margin-top: 8px; line-height: 1.4; }}
  .hero-stat {{ display: inline-block; margin-top: 10px; background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.3); border-radius: 20px; padding: 5px 12px; font-size: 12px; font-weight: 700; }}

  .sec-label {{ font-size: 11px; font-weight: 700; color: #718096; text-transform: uppercase; letter-spacing: 0.8px; margin: 4px 4px 8px; }}

  .spot {{ background: white; border-radius: 14px; margin-bottom: 10px; box-shadow: 0 2px 6px rgba(0,0,0,0.06); overflow: hidden; }}
  .spot-head {{ display: flex; align-items: center; gap: 10px; padding: 14px 14px; cursor: pointer; user-select: none; }}
  .spot-rank {{ width: 26px; height: 26px; border-radius: 50%; background: #ebf8ff; color: #2b6cb0; font-size: 13px; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }}
  .spot-name {{ font-size: 16px; font-weight: 800; flex: 1; }}
  .spot-quick {{ text-align: right; }}
  .spot-stars {{ font-size: 13px; line-height: 1; }}
  .spot-size {{ font-size: 14px; font-weight: 800; color: #2b6cb0; margin-top: 2px; }}
  .spot-chev {{ color: #cbd5e0; font-size: 18px; margin-left: 6px; transition: transform 0.25s; flex-shrink: 0; }}
  .spot.open .spot-chev {{ transform: rotate(90deg); color: #2b6cb0; }}
  .spot-body {{ display: none; padding: 0 12px 12px; border-top: 1px solid #edf2f7; }}
  .spot.open .spot-body {{ display: block; }}
  /* embedded desktop cards: drop their outer shadow/margin inside the accordion */
  .spot-body .card {{ box-shadow: none; padding-left: 0; padding-right: 0; }}
  .spot-body .rating-banner {{ display: none; }}

  .desktop-link {{ color: #63b3ed; font-weight: 700; text-decoration: none; }}
</style>
</head>
<body>

<div class="header">
  <div class="header-top">
    <div>
      <div class="header-title">🏄 This Morning</div>
      <div class="header-subtitle">Dee Why · Long Reef · Curl Curl</div>
    </div>
    <div style="text-align:right">
      <div class="clock" id="clock">--:--:--</div>
      <div class="date-line" id="dateline">AEST</div>
    </div>
  </div>
</div>

{alert_bar}

{shark_bar}

<div class="wrap">

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

  <div class="footer">
    <strong>Live data scraped from Surfline</strong><br>
    {footer_date}<br>
    <a class="desktop-link" href="index.html">⤢ Open full desktop dashboard</a>
  </div>

</div>

<script>
  function toggleSpot(el) {{ el.classList.toggle('open'); }}

  function updateClock() {{
    const now = new Date();
    const timeStr = new Intl.DateTimeFormat('en-AU', {{
      timeZone: 'Australia/Sydney', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false
    }}).format(now);
    const dateStr = new Intl.DateTimeFormat('en-AU', {{
      timeZone: 'Australia/Sydney', weekday: 'short', day: 'numeric', month: 'short', year: 'numeric'
    }}).format(now);
    document.getElementById('clock').textContent = timeStr;
    document.getElementById('dateline').textContent = dateStr + ' AEST';
  }}
  updateClock();
  setInterval(updateClock, 1000);

  if('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js');
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
