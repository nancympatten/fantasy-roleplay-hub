#!/usr/bin/env python3
"""
Fantasy Roleplay Hub — Production Static Website Generator
===========================================================

Builds a zero-dependency, SEO-optimized static website for
Cloudflare Pages and Cloudflare Workers.

Usage:
    python3 build.py

Input:
    data.csv

Output:
    dist/
        index.html
        scenario/
        category/
        topic/
        tag/
        sitemap.xml
        sitemap-1.xml
        sitemap.xsl
        robots.txt
        dmca.html
        2257.html
        _headers
        _redirects

Python dependencies: Standard library only.
"""

import os
from datetime import datetime

BASE_URL = os.environ.get(
    "BASE_URL",
    "https://fantasy-roleplay-hub.velvetgrid.workers.dev"
).rstrip("/")

SITE_NAME = "Fantasy Roleplay Hub"
NICHE_TOPIC = "Interactive Adult Fantasy Scenarios, Worldbuilding & AI Roleplay Scripts"
CONTACT_EMAIL = "nancympatten@gmail.com"
AFFILIATE_URL = "#affiliate-link"
AFFILIATE_CTA_TEXT = "Enter This Fantasy World with an AI Character Companion"
CURRENT_YEAR = datetime.utcnow().year

import csv
import re
import json
import html
import shutil
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import quote

# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "data.csv"
DIST = ROOT / "dist"

ITEMS_PER_PAGE = 24
RELATED_LIMIT = 8
NEWEST_LIMIT = 30

CSV_COLUMNS = [
    "slug",
    "title",
    "category",
    "subcategory",
    "target_keyword",
    "scenario_script",
    "twist_options",
    "description",
    "tags",
    "faq_q1",
    "faq_a1",
    "faq_q2",
    "faq_a2",
    "upload_date",
]

AD_SLOTS = """
<!-- AD_SLOT_POPUNDER -->
<!-- AD_SLOT_TOP_BANNER -->
<!-- AD_SLOT_MID_CONTENT -->
<!-- AD_SLOT_STICKY_FOOTER -->
"""

# ============================================================
# UTILITIES
# ============================================================


def esc(value):
    return html.escape(str(value or ""), quote=True)


def plain(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def slugify(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "uncategorized"


def safe_slug(value):
    value = slugify(value)
    return value[:120].strip("-") or "scenario"


def split_tags(value):
    if isinstance(value, list):
        values = value
    else:
        values = re.split(r"[,|;]", str(value or ""))

    result = []
    seen = set()

    for item in values:
        tag = plain(item)
        key = tag.lower()

        if tag and key not in seen:
            seen.add(key)
            result.append(tag)

    return result


def parse_date(value):
    value = plain(value)

    if not value:
        return datetime.min

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%d-%m-%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
            tzinfo=None
        )
    except ValueError:
        return datetime.min


def write_file(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def json_ld(data):
    return (
        '<script type="application/ld+json">'
        + json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
        + "</script>"
    )


def canonical_url(path):
    return BASE_URL + "/" + str(path).lstrip("/")


def meta_description(value):
    value = plain(value)
    if len(value) > 158:
        value = value[:155].rsplit(" ", 1)[0] + "..."
    return value or NICHE_TOPIC


def format_date(value):
    date = parse_date(value)

    if date == datetime.min:
        return "Evergreen"

    return date.strftime("%B %d, %Y")


def word_count(value):
    return len(re.findall(r"\b[\w'-]+\b", str(value or "")))


# ============================================================
# CSV LOADING
# ============================================================


def load_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Missing input file: {DATA_FILE}\n"
            "Place data.csv beside build.py."
        )

    rows = []
    used_slugs = set()

    with DATA_FILE.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:
        reader = csv.DictReader(file)

        if not reader.fieldnames:
            raise ValueError("data.csv is empty or has no CSV header.")

        missing = set(CSV_COLUMNS) - set(reader.fieldnames)

        if missing:
            raise ValueError(
                "Missing required CSV columns: "
                + ", ".join(sorted(missing))
            )

        for line_number, original in enumerate(reader, start=2):
            row = {
                key: plain(original.get(key, ""))
                for key in CSV_COLUMNS
            }

            if not row["title"] or not row["scenario_script"]:
                print(
                    f"Skipping line {line_number}: "
                    "missing title or scenario_script."
                )
                continue

            base = safe_slug(row["slug"] or row["title"])
            slug = base
            suffix = 2

            while slug in used_slugs:
                slug = f"{base}-{suffix}"
                suffix += 1

            used_slugs.add(slug)
            row["slug"] = slug

            row["category"] = row["category"] or "Fantasy Scenarios"
            row["subcategory"] = row["subcategory"] or "General Fantasy"
            row["target_keyword"] = (
                row["target_keyword"] or row["title"]
            )
            row["description"] = (
                row["description"] or row["title"]
            )

            row["tags_list"] = split_tags(row["tags"])
            row["twists_list"] = [
                plain(t)
                for t in row["twist_options"].split("|")
                if plain(t)
            ]

            row["date_object"] = parse_date(row["upload_date"])

            rows.append(row)

    if not rows:
        raise ValueError("No valid scenario rows found in data.csv.")

    return rows


# ============================================================
# GLOBAL CSS
# ============================================================


def global_css():
    return r"""
:root {
    color-scheme: dark;
    --bg: #080a10;
    --card: #121624;
    --card2: #171d2d;
    --purple: #a855f7;
    --gold: #f59e0b;
    --text: #f3f4f6;
    --muted: #a1a1aa;
    --border: #272b3b;
    --green: #34d399;
    --radius: 16px;
    --max: 1180px;
}

* { box-sizing: border-box; }

html {
    scroll-behavior: smooth;
    background: var(--bg);
}

body {
    margin: 0;
    background:
        radial-gradient(ellipse at 15% 0%, #23133d 0%, transparent 34%),
        radial-gradient(ellipse at 90% 10%, #251c12 0%, transparent 28%),
        var(--bg);
    color: var(--text);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system,
        BlinkMacSystemFont, "Segoe UI", sans-serif;
    line-height: 1.7;
    min-height: 100vh;
}

a {
    color: #c4a2ff;
    text-decoration: none;
}

a:hover { color: var(--gold); }

button, input, select, textarea {
    font: inherit;
}

button {
    cursor: pointer;
}

.container {
    width: min(var(--max), calc(100% - 36px));
    margin-inline: auto;
}

.site-header {
    position: sticky;
    top: 0;
    z-index: 30;
    background: rgba(8,10,16,.94);
    backdrop-filter: blur(16px);
    border-bottom: 1px solid var(--border);
}

.nav {
    min-height: 70px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 20px;
}

.brand {
    font-size: 1.2rem;
    font-weight: 900;
    color: white;
    letter-spacing: -.04em;
}

.brand span { color: var(--purple); }

.nav-links {
    display: flex;
    flex-wrap: wrap;
    gap: 18px;
    font-size: .88rem;
}

.hero {
    padding: 78px 0 55px;
    text-align: center;
}

.eyebrow {
    display: inline-flex;
    border: 1px solid #67439a;
    border-radius: 999px;
    padding: 5px 13px;
    color: #d8b4fe;
    font-size: .78rem;
    font-weight: 800;
    letter-spacing: .1em;
    text-transform: uppercase;
}

h1, h2, h3 {
    line-height: 1.2;
    letter-spacing: -.035em;
}

h1 {
    font-size: clamp(2.2rem, 6vw, 4.6rem);
    max-width: 950px;
    margin: 24px auto;
}

h2 { font-size: clamp(1.5rem, 3vw, 2.1rem); }

.hero p {
    max-width: 760px;
    margin: 0 auto;
    color: var(--muted);
}

.section {
    padding: 38px 0;
}

.section-heading {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 15px;
    margin-bottom: 22px;
}

.section-heading h2 { margin: 0; }

.search-wrap {
    max-width: 760px;
    margin: 30px auto 0;
}

.search-input, .field, .select, .textarea {
    width: 100%;
    padding: 14px 16px;
    border: 1px solid var(--border);
    background: #101422;
    border-radius: 12px;
    color: var(--text);
    outline: none;
}

.search-input:focus, .field:focus, .textarea:focus,
.select:focus {
    border-color: var(--purple);
    box-shadow: 0 0 0 3px #a855f72b;
}

.grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 18px;
}

.grid.two {
    grid-template-columns: repeat(2, minmax(0, 1fr));
}

.card {
    background: linear-gradient(145deg, var(--card2), var(--card));
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 21px;
    min-width: 0;
    transition: transform .2s, border-color .2s;
}

.card:hover {
    transform: translateY(-3px);
    border-color: #8050b9;
}

.card h3 {
    margin: 8px 0;
    font-size: 1.08rem;
}

.card p {
    color: var(--muted);
    font-size: .9rem;
}

.card-meta {
    color: var(--gold);
    font-size: .75rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .06em;
}

.count {
    color: var(--gold);
    font-size: .82rem;
}

.pills, .tags {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
}

.pill, .tag {
    display: inline-flex;
    align-items: center;
    padding: 6px 11px;
    border-radius: 999px;
    border: 1px solid var(--border);
    background: #171c2b;
    font-size: .8rem;
}

.tag { color: #c4b5fd; }

.button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: linear-gradient(120deg, #9333ea, #7c3aed);
    color: white;
    border: 0;
    border-radius: 11px;
    padding: 12px 19px;
    font-weight: 800;
    transition: opacity .2s, transform .2s;
}

.button:hover {
    opacity: .88;
    color: white;
    transform: translateY(-1px);
}

.button.gold {
    background: linear-gradient(120deg, #f59e0b, #d97706);
    color: #17110a;
}

.button.secondary {
    background: #252b3c;
    border: 1px solid #41475a;
    color: white;
}

.button.small {
    padding: 8px 12px;
    font-size: .83rem;
}

.muted { color: var(--muted); }

.breadcrumbs {
    padding: 20px 0;
    font-size: .82rem;
    color: var(--muted);
}

.breadcrumbs span { padding: 0 7px; }

.studio {
    border: 1px solid #53327d;
    background: linear-gradient(145deg, #171327, #111624);
    border-radius: 20px;
    padding: clamp(18px, 4vw, 32px);
}

.studio h2 { margin-top: 0; }

.customizer {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 14px;
    margin: 22px 0;
}

.field-group label {
    display: block;
    margin-bottom: 7px;
    font-size: .83rem;
    color: #d4d4d8;
    font-weight: 700;
}

.script-output {
    background: #090d17;
    border: 1px solid #32364b;
    border-radius: 14px;
    padding: 24px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    min-height: 170px;
    font-size: 16px;
    line-height: 1.85;
    transition: font-size .15s;
}

.studio-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 9px;
    margin: 16px 0;
}

.counter {
    color: var(--muted);
    font-size: .8rem;
    margin: 9px 0;
}

.twist-box {
    margin-top: 20px;
    padding: 19px;
    border: 1px solid #86551c;
    border-radius: 14px;
    background: #261d12;
}

.twist-box h3 {
    margin-top: 0;
    color: var(--gold);
}

.audio-box {
    margin-top: 22px;
    padding: 20px;
    border: 1px solid var(--border);
    border-radius: 14px;
    background: #101625;
}

.audio-controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 12px;
}

.audio-controls input[type=range] { accent-color: var(--purple); }

.verified {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    border: 1px solid #145b45;
    background: #09271f;
    color: #6ee7b7;
    border-radius: 999px;
    padding: 6px 12px;
    font-size: .77rem;
    font-weight: 800;
}

.affiliate {
    margin: 25px 0;
    padding: 30px;
    border-radius: 18px;
    background: linear-gradient(120deg, #281542, #3c2411);
    border: 1px solid #8050a5;
    text-align: center;
}

.affiliate h2 { margin-top: 0; }

.faq {
    border-bottom: 1px solid var(--border);
    padding: 16px 0;
}

.faq h3 { font-size: 1rem; }

.pagination {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 15px;
    margin: 32px 0;
}

.site-footer {
    border-top: 1px solid var(--border);
    margin-top: 60px;
    padding: 35px 0;
    color: var(--muted);
    font-size: .85rem;
}

.footer-links {
    display: flex;
    flex-wrap: wrap;
    gap: 17px;
    margin: 12px 0;
}

.empty {
    padding: 30px;
    text-align: center;
    color: var(--muted);
}

.age-overlay {
    position: fixed;
    inset: 0;
    z-index: 1000;
    display: none;
    align-items: center;
    justify-content: center;
    padding: 20px;
    background: rgba(0,0,0,.94);
    backdrop-filter: blur(14px);
}

.age-dialog {
    max-width: 440px;
    width: 100%;
    text-align: center;
    background: #141827;
    border: 1px solid #62418a;
    border-radius: 20px;
    padding: 32px;
}

.age-dialog h2 { color: var(--gold); }

.sticky-footer {
    display: none;
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 20;
    background: rgba(8,10,16,.96);
    border-top: 1px solid var(--border);
    padding: 10px 16px;
    text-align: center;
}

.sticky-footer .button { width: 100%; }

@media(max-width: 850px) {
    .grid { grid-template-columns: repeat(2, minmax(0,1fr)); }
    .customizer { grid-template-columns: 1fr; }
}

@media(max-width: 580px) {
    .container { width: min(100% - 26px, var(--max)); }
    .nav { min-height: 62px; }
    .nav-links { gap: 10px; font-size: .76rem; }
    .grid, .grid.two { grid-template-columns: 1fr; }
    .hero { padding: 52px 0 35px; }
    .section { padding: 27px 0; }
    .affiliate { padding: 23px 17px; }
    .sticky-footer { display: block; }
    body { padding-bottom: 65px; }
}

@media(prefers-reduced-motion: reduce) {
    *, *::before, *::after {
        scroll-behavior: auto !important;
        transition: none !important;
    }
}
"""


# ============================================================
# GLOBAL JAVASCRIPT
# ============================================================


def global_js():
    return r"""
(function(){
    "use strict";

    function updateLiveYear(){
        var year = new Date().getFullYear();
        document.querySelectorAll(".live-year").forEach(function(el){
            el.textContent = year;
        });

        var month = new Intl.DateTimeFormat(undefined,{
            month:"long"
        }).format(new Date());

        document.querySelectorAll(".verified-status").forEach(function(el){
            el.textContent = "Verified & Active for " + month + " " + year;
        });
    }

    updateLiveYear();

    var overlay = document.getElementById("age-overlay");

    if(overlay){
        var accepted = false;

        try{
            accepted = localStorage.getItem("frh_age_verified") === "yes";
        }catch(e){}

        if(!accepted){
            overlay.style.display = "flex";
        }

        var yes = document.getElementById("age-yes");
        var no = document.getElementById("age-no");

        if(yes){
            yes.addEventListener("click",function(){
                try{
                    localStorage.setItem("frh_age_verified","yes");
                }catch(e){}

                overlay.style.display = "none";
            });
        }

        if(no){
            no.addEventListener("click",function(){
                document.body.innerHTML =
                    '<main class="container section"><h1>Access Restricted</h1>' +
                    '<p>This website is intended for adults aged 18 or older.</p></main>';
            });
        }
    }

    document.querySelectorAll("[data-live-search]").forEach(function(input){
        input.addEventListener("input",function(){
            var query = input.value.toLowerCase().trim();

            document.querySelectorAll("[data-search-item]").forEach(function(card){
                var haystack = (card.getAttribute("data-search-item") || "")
                    .toLowerCase();

                card.style.display = haystack.includes(query) ? "" : "none";
            });
        });
    });

    var customizer = document.getElementById("scenario-script");

    if(customizer){
        var source = customizer.getAttribute("data-template") || "";

        function updateScenario(){
            var replacements = {
                "{{hero_name}}":
                    document.getElementById("hero-name").value || "The Hero",
                "{{companion_name}}":
                    document.getElementById("companion-name").value || "The Companion",
                "{{realm}}":
                    document.getElementById("realm-name").value || "The Enchanted Realm"
            };

            var output = source;

            Object.keys(replacements).forEach(function(key){
                output = output.split(key).join(replacements[key]);
            });

            customizer.textContent = output;
            updateCounter();
        }

        function updateCounter(){
            var value = customizer.textContent || "";
            var words = value.trim() ? value.trim().split(/\s+/).length : 0;
            var tokens = Math.ceil(value.length / 4);

            var counter = document.getElementById("word-counter");

            if(counter){
                counter.textContent = words + " words · Approximately " +
                    tokens + " tokens";
            }
        }

        ["hero-name","companion-name","realm-name"].forEach(function(id){
            var field = document.getElementById(id);
            if(field){
                field.addEventListener("input",updateScenario);
            }
        });

        updateScenario();

        var copyButton = document.getElementById("copy-script");

        if(copyButton){
            copyButton.addEventListener("click",async function(){
                try{
                    await navigator.clipboard.writeText(customizer.textContent);
                }catch(e){
                    var range = document.createRange();
                    range.selectNodeContents(customizer);
                    var selection = window.getSelection();
                    selection.removeAllRanges();
                    selection.addRange(range);
                    document.execCommand("copy");
                    selection.removeAllRanges();
                }

                copyButton.textContent = "Copied!";

                setTimeout(function(){
                    copyButton.textContent = "Copy Roleplay Prompt";
                },1800);
            });
        }

        var fontSize = 16;

        var smaller = document.getElementById("font-smaller");
        var larger = document.getElementById("font-larger");

        if(smaller){
            smaller.addEventListener("click",function(){
                fontSize = Math.max(12,fontSize-2);
                customizer.style.fontSize = fontSize + "px";
            });
        }

        if(larger){
            larger.addEventListener("click",function(){
                fontSize = Math.min(28,fontSize+2);
                customizer.style.fontSize = fontSize + "px";
            });
        }

        var twists = [];

        try{
            twists = JSON.parse(
                document.getElementById("twist-data").textContent
            );
        }catch(e){}

        var twistButton = document.getElementById("generate-twist");
        var twistOutput = document.getElementById("twist-output");

        if(twistButton && twistOutput){
            twistButton.addEventListener("click",function(){
                if(!twists.length){
                    twistOutput.textContent =
                        "No additional plot twists are available.";
                    return;
                }

                var selected = twists[
                    Math.floor(Math.random()*twists.length)
                ];

                twistOutput.textContent = selected;
                twistOutput.parentElement.style.display = "block";
            });
        }

        // Web Audio API synthesized ambience.
        var audioContext = null;
        var masterGain = null;
        var oscillators = [];
        var noiseSource = null;
        var playing = false;

        var audioButton = document.getElementById("audio-toggle");
        var mode = document.getElementById("sound-mode");
        var volume = document.getElementById("sound-volume");

        function stopAudio(){
            oscillators.forEach(function(osc){
                try{ osc.stop(); }catch(e){}
            });

            oscillators = [];

            if(noiseSource){
                try{ noiseSource.stop(); }catch(e){}
                noiseSource = null;
            }

            playing = false;

            if(audioButton){
                audioButton.textContent = "Play Ambience";
            }
        }

        function createNoise(){
            var bufferSize = 2 * audioContext.sampleRate;
            var buffer = audioContext.createBuffer(
                1,bufferSize,audioContext.sampleRate
            );

            var data = buffer.getChannelData(0);

            for(var i=0;i<bufferSize;i++){
                data[i] = Math.random()*2-1;
            }

            var source = audioContext.createBufferSource();
            source.buffer = buffer;
            source.loop = true;

            var filter = audioContext.createBiquadFilter();
            filter.type = "lowpass";
            filter.frequency.value = 900;

            var gain = audioContext.createGain();
            gain.gain.value = 0.035;

            source.connect(filter);
            filter.connect(gain);
            gain.connect(masterGain);

            source.start();
            noiseSource = source;
        }

        function addTone(frequency,type,gainValue){
            var osc = audioContext.createOscillator();
            var gain = audioContext.createGain();

            osc.type = type;
            osc.frequency.value = frequency;
            gain.gain.value = gainValue;

            osc.connect(gain);
            gain.connect(masterGain);

            osc.start();
            oscillators.push(osc);
        }

        function startAudio(){
            var AudioContextClass =
                window.AudioContext || window.webkitAudioContext;

            if(!AudioContextClass){
                alert("Web Audio API is not supported in this browser.");
                return;
            }

            audioContext = audioContext || new AudioContextClass();

            if(audioContext.state === "suspended"){
                audioContext.resume();
            }

            masterGain = audioContext.createGain();
            masterGain.gain.value = Number(volume.value)/100;
            masterGain.connect(audioContext.destination);

            var selected = mode.value;

            if(selected === "forest"){
                createNoise();
                addTone(174,"sine",0.025);
                addTone(261,"sine",0.012);
            }else if(selected === "tavern"){
                createNoise();
                addTone(65,"triangle",0.025);
                addTone(82,"sine",0.015);
            }else{
                addTone(55,"sine",0.025);
                addTone(82,"triangle",0.018);
                addTone(110,"sine",0.012);
                createNoise();
            }

            playing = true;
            audioButton.textContent = "Pause Ambience";
        }

        if(audioButton){
            audioButton.addEventListener("click",function(){
                if(playing){
                    stopAudio();
                }else{
                    startAudio();
                }
            });
        }

        if(mode){
            mode.addEventListener("change",function(){
                if(playing){
                    stopAudio();
                    startAudio();
                }
            });
        }

        if(volume){
            volume.addEventListener("input",function(){
                if(masterGain){
                    masterGain.gain.value = Number(volume.value)/100;
                }
            });
        }

        document.addEventListener("visibilitychange",function(){
            if(document.hidden && playing){
                stopAudio();
            }
        });

        window.addEventListener("pagehide",stopAudio);
    }

    // Set the current year dynamically without requiring a rebuild.
    document.querySelectorAll(".live-year").forEach(function(el){
        el.textContent = new Date().getFullYear();
    });
})();
"""


# ============================================================
# SHARED PAGE COMPONENTS
# ============================================================


def age_modal():
    return """
<div class="age-overlay" id="age-overlay" role="dialog"
     aria-modal="true" aria-labelledby="age-title">
    <div class="age-dialog">
        <div class="eyebrow">Fantasy Roleplay Hub</div>
        <h2 id="age-title">18+ Age Verification</h2>
        <p>This website is intended exclusively for adults aged 18 or older.
        Some scenarios may contain mature fictional themes.</p>
        <p>By continuing, you confirm that you are at least 18 years old
        and legally permitted to access this content in your jurisdiction.</p>
        <div class="studio-actions" style="justify-content:center">
            <button class="button gold" id="age-yes">I Am 18 or Older</button>
            <button class="button secondary" id="age-no">Exit</button>
        </div>
    </div>
</div>
"""


def header():
    return """
<header class="site-header">
    <div class="container nav">
        <a class="brand" href="/">Fantasy<span>Roleplay</span>Hub</a>
        <nav class="nav-links" aria-label="Main navigation">
            <a href="/">Home</a>
            <a href="/#categories">Realms</a>
            <a href="/#latest">Scenarios</a>
            <a href="/#tags">Tags</a>
        </nav>
    </div>
</header>
"""


def footer():
    return f"""
<footer class="site-footer">
    <div class="container">
        <strong>{esc(SITE_NAME)}</strong>
        <div class="footer-links">
            <a href="/dmca.html">DMCA Policy</a>
            <a href="/2257.html">Compliance Statement</a>
            <a href="mailto:{esc(CONTACT_EMAIL)}">Contact</a>
            <a href="/sitemap.xml">XML Sitemap</a>
        </div>
        <p>© <span class="live-year">{CURRENT_YEAR}</span>
        {esc(SITE_NAME)}. All rights reserved.</p>
        <p>Fictional interactive fantasy scenarios for adults.
        All scenarios are provided for entertainment and creative writing.</p>
    </div>
</footer>
"""


def sticky_footer():
    return f"""
<div class="sticky-footer">
    <a class="button gold" href="{esc(AFFILIATE_URL)}">
        Explore AI Character Companions
    </a>
</div>
"""


def page_template(title, description, path, content, extra_head="",
                  include_age=True):
    url = canonical_url(path)

    age = age_modal() if include_age else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#080a10">
<meta name="rating" content="RTA-5042-1996-1400-1577-RTA">
<title>{esc(title)}</title>
<meta name="description" content="{esc(meta_description(description))}">
<link rel="canonical" href="{esc(url)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="{esc(SITE_NAME)}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(meta_description(description))}">
<meta property="og:url" content="{esc(url)}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{esc(title)}">
<meta name="twitter:description" content="{esc(meta_description(description))}">
{extra_head}
<style>{global_css()}</style>
</head>
<body>
{AD_SLOTS}
{header()}
{content}
{footer()}
{sticky_footer()}
{age}
<script>{global_js()}</script>
</body>
</html>"""


# ============================================================
# CATEGORY / TOPIC / TAG AGGREGATION
# ============================================================


def build_indexes(rows):
    categories = defaultdict(list)
    subcategories = defaultdict(list)
    tags = defaultdict(list)

    category_names = {}
    subcategory_names = {}
    tag_names = {}

    for row in rows:
        category_slug = slugify(row["category"])
        subcategory_slug = slugify(row["subcategory"])

        categories[category_slug].append(row)
        subcategories[subcategory_slug].append(row)

        category_names[category_slug] = row["category"]
        subcategory_names[subcategory_slug] = row["subcategory"]

        row["category_slug"] = category_slug
        row["subcategory_slug"] = subcategory_slug

        for tag in row["tags_list"]:
            tag_slug = slugify(tag)
            tags[tag_slug].append(row)
            tag_names[tag_slug] = tag

    return {
        "categories": categories,
        "subcategories": subcategories,
        "tags": tags,
        "category_names": category_names,
        "subcategory_names": subcategory_names,
        "tag_names": tag_names,
    }


# ============================================================
# SCENARIO CARDS
# ============================================================


def scenario_card(row):
    searchable = " ".join([
        row["title"],
        row["target_keyword"],
        row["description"],
        " ".join(row["tags_list"]),
        row["category"],
        row["subcategory"],
    ])

    return f"""
<article class="card" data-search-item="{esc(searchable)}">
    <div class="card-meta">{esc(row["category"])}</div>
    <h3><a href="/scenario/{quote(row["slug"])}.html">
        {esc(row["title"])}
    </a></h3>
    <p>{esc(row["description"])}</p>
    <div class="tags">
        <span class="tag">{esc(row["subcategory"])}</span>
        {''.join(
            '<span class="tag">' + esc(tag) + '</span>'
            for tag in row["tags_list"][:3]
        )}
    </div>
    <p class="muted">Updated: {esc(format_date(row["upload_date"]))}</p>
    <a class="button small"
       href="/scenario/{quote(row["slug"])}.html">Explore Scenario</a>
</article>
"""


def render_cards(rows):
    if not rows:
        return '<div class="empty">No scenarios found.</div>'

    return '<div class="grid">' + "".join(
        scenario_card(row) for row in rows
    ) + "</div>"


# ============================================================
# HOMEPAGE
# ============================================================


def build_homepage(rows, indexes):
    categories = indexes["categories"]
    subcategories = indexes["subcategories"]
    tags = indexes["tags"]

    category_cards = []

    # Exactly one card for every unique category.
    for cat_slug, items in sorted(
        categories.items(),
        key=lambda item: item[0]
    ):
        name = indexes["category_names"][cat_slug]

        category_cards.append(f"""
        <a class="card" href="/category/{quote(cat_slug)}/page-1.html">
            <h3>{esc(name)}</h3>
            <span class="count">{len(items)} scenarios</span>
            <p>Explore interactive stories, fantasy characters,
            and immersive roleplay adventures.</p>
        </a>
        """)

    subcategory_pills = []

    for sub_slug, items in sorted(
        subcategories.items(),
        key=lambda item: item[0]
    ):
        name = indexes["subcategory_names"][sub_slug]

        subcategory_pills.append(f"""
        <a class="pill" href="/topic/{quote(sub_slug)}.html">
            {esc(name)} <span class="count">({len(items)})</span>
        </a>
        """)

    tag_cloud = []

    for tag_slug, items in sorted(
        tags.items(),
        key=lambda item: (-len(item[1]), item[0])
    ):
        tag_name = indexes["tag_names"][tag_slug]

        tag_cloud.append(f"""
        <a class="tag" href="/tag/{quote(tag_slug)}.html">
            {esc(tag_name)} ({len(items)})
        </a>
        """)

    newest = sorted(
        rows,
        key=lambda row: row["date_object"],
        reverse=True
    )[:NEWEST_LIMIT]

    content = f"""
<main>
<section class="hero container">
    <span class="eyebrow">Your Imagination Has No Borders</span>
    <h1>Enter Extraordinary Fantasy Worlds with
        <span style="color:var(--purple)">Interactive Roleplay</span>
    </h1>
    <p>{esc(NICHE_TOPIC)}. Discover detailed scenarios, customizable
    characters, unexpected plot twists, and immersive storytelling
    experiences.</p>

    <div class="search-wrap">
        <input class="search-input" type="search"
            placeholder="Search scenarios, keywords, or tags..."
            aria-label="Search fantasy scenarios"
            data-live-search>
        <p class="muted">Search instantly across
            {len(rows)} fantasy scenarios.</p>
    </div>
</section>

<section class="section container" id="categories">
    <div class="section-heading">
        <h2>Explore Fantasy Realms</h2>
        <span class="count">{len(categories)} unique categories</span>
    </div>
    <div class="grid">
        {''.join(category_cards)}
    </div>
</section>

<section class="section container">
    <div class="section-heading">
        <h2>Explore Story Topics</h2>
    </div>
    <div class="pills">
        {''.join(subcategory_pills)}
    </div>
</section>

<section class="section container" id="tags">
    <div class="section-heading">
        <h2>Popular Fantasy Tags</h2>
    </div>
    <div class="tags">
        {''.join(tag_cloud)}
    </div>
</section>

<section class="section container" id="latest">
    <div class="section-heading">
        <h2>Latest Fantasy Scenarios</h2>
        <span class="count">{len(newest)} newest entries</span>
    </div>
    {render_cards(newest)}
    <p class="muted">Explore our complete collection through the
    category and topic directories above.</p>
</section>

<section class="section container">
    <div class="affiliate">
        <div class="eyebrow">Unlock Your Imagination</div>
        <h2>Bring Your Fantasy Characters to Life</h2>
        <p>Discover AI-powered character companions and create
        personalized interactive storytelling experiences.</p>
        <a class="button gold" href="{esc(AFFILIATE_URL)}">
            {esc(AFFILIATE_CTA_TEXT)}
        </a>
    </div>
</section>

<section class="section container">
    <h2>About {esc(SITE_NAME)}</h2>
    <p class="muted">{esc(SITE_NAME)} is a creative library of fictional
    fantasy roleplay scenarios, worldbuilding prompts, character
    interactions, and imaginative storytelling resources. Explore
    unique settings, customize character names, generate plot twists,
    and develop your own adventures.</p>
    <p class="muted">Our scenario collection is designed for creative
    inspiration and entertainment. You can adapt prompts to your
    preferred writing style, characters, and fictional worlds.</p>
</section>
</main>
"""

    content += """
<script type="application/ld+json">
{
 "@context":"https://schema.org",
 "@type":"WebSite",
 "name":"Fantasy Roleplay Hub",
 "url":""" + json.dumps(BASE_URL) + """,
 "potentialAction":{
   "@type":"SearchAction",
   "target":{
     "@type":"EntryPoint",
     "urlTemplate":""" + json.dumps(BASE_URL + "/?q={search_term_string}") + """
   },
   "query-input":"required name=search_term_string"
 }
}
</script>
"""

    page = page_template(
        f"{SITE_NAME} | Interactive Fantasy Roleplay Scenarios",
        f"Explore {len(rows)} interactive fantasy roleplay scenarios, "
        "customizable characters, immersive worlds, and creative plot twists.",
        "index.html",
        content,
    )

    write_file(DIST / "index.html", page)


# ============================================================
# RELATED SCENARIOS
# ============================================================


def related_scenarios(row, rows):
    candidates = []

    for other in rows:
        if other["slug"] == row["slug"]:
            continue

        same_subcategory = (
            other["subcategory_slug"] == row["subcategory_slug"]
        )

        shared_tags = len(
            set(t.lower() for t in row["tags_list"])
            & set(t.lower() for t in other["tags_list"])
        )

        same_category = (
            other["category_slug"] == row["category_slug"]
        )

        score = (
            same_subcategory * 100
            + shared_tags * 15
            + same_category * 5
        )

        if score > 0:
            candidates.append((score, other))

    candidates.sort(
        key=lambda item: (
            -item[0],
            -item[1]["date_object"].timestamp()
            if item[1]["date_object"] != datetime.min
            else 0
        )
    )

    selected = [item[1] for item in candidates[:RELATED_LIMIT]]

    if len(selected) < RELATED_LIMIT:
        existing = {item["slug"] for item in selected}
        existing.add(row["slug"])

        fallback = sorted(
            [item for item in rows if item["slug"] not in existing],
            key=lambda item: item["date_object"],
            reverse=True
        )

        selected.extend(
            fallback[:RELATED_LIMIT - len(selected)]
        )

    return selected


# ============================================================
# DETAIL PAGE JSON-LD
# ============================================================


def detail_schema(row, url):
    faq_items = []

    for q_key, a_key in [
        ("faq_q1", "faq_a1"),
        ("faq_q2", "faq_a2"),
    ]:
        question = plain(row[q_key])
        answer = plain(row[a_key])

        if question and answer:
            faq_items.append({
                "@type": "Question",
                "name": question,
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": answer,
                }
            })

    article = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": row["title"],
        "description": meta_description(row["description"]),
        "mainEntityOfPage": {
            "@type": "WebPage",
            "@id": url,
        },
        "author": {
            "@type": "Organization",
            "name": SITE_NAME,
        },
        "publisher": {
            "@type": "Organization",
            "name": SITE_NAME,
        },
        "datePublished": (
            row["date_object"].strftime("%Y-%m-%d")
            if row["date_object"] != datetime.min
            else f"{CURRENT_YEAR}-01-01"
        ),
        "inLanguage": "en",
        "articleSection": row["category"],
        "keywords": ", ".join([
            row["target_keyword"]
        ] + row["tags_list"]),
    }

    breadcrumb = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": 1,
                "name": "Home",
                "item": BASE_URL + "/",
            },
            {
                "@type": "ListItem",
                "position": 2,
                "name": row["category"],
                "item": canonical_url(
                    "category/" + row["category_slug"] + "/page-1.html"
                ),
            },
            {
                "@type": "ListItem",
                "position": 3,
                "name": row["title"],
                "item": url,
            },
        ],
    }

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": faq_items,
    }

    schemas = [json_ld(article), json_ld(breadcrumb)]

    if faq_items:
        schemas.append(json_ld(faq))

    return "\n".join(schemas)


# ============================================================
# DETAIL PAGES
# ============================================================


def build_detail_page(row, rows):
    url_path = "scenario/" + row["slug"] + ".html"
    url = canonical_url(url_path)

    related = related_scenarios(row, rows)

    script = row["scenario_script"]

    script_json = json.dumps(
        script,
        ensure_ascii=False
    ).replace("</", "<\\/")

    twist_json = json.dumps(
        row["twists_list"],
        ensure_ascii=False
    ).replace("</", "<\\/")

    schema = detail_schema(row, url)

    content = f"""
<main class="container">
    <div class="breadcrumbs">
        <a href="/">Home</a><span>›</span>
        <a href="/category/{quote(row["category_slug"])}/page-1.html">
            {esc(row["category"])}
        </a>
        <span>›</span>{esc(row["title"])}
    </div>

    <section class="section">
        <span class="eyebrow">{esc(row["category"])}</span>
        <h1>{esc(row["title"])}</h1>
        <p class="muted">{esc(row["description"])}</p>

        <div class="tags">
            <span class="tag">{esc(row["subcategory"])}</span>
            {''.join(
                '<span class="tag">' + esc(tag) + '</span>'
                for tag in row["tags_list"]
            )}
        </div>

        <p class="muted">
            Published: {esc(format_date(row["upload_date"]))}
        </p>

        <div class="verified">
            <span>●</span>
            <span class="verified-status">
                Verified &amp; Active for {datetime.utcnow().strftime("%B %Y")}
            </span>
        </div>
    </section>

    <section class="section">
        <div class="studio">
            <div class="eyebrow">Interactive Roleplay Studio</div>
            <h2>Customize Your Fantasy Adventure</h2>
            <p class="muted">Personalize character names and your setting.
            Your changes update the scenario instantly in your browser.</p>

            <div class="customizer">
                <div class="field-group">
                    <label for="hero-name">Hero Name</label>
                    <input class="field" id="hero-name"
                        placeholder="Enter your hero's name"
                        maxlength="80">
                </div>

                <div class="field-group">
                    <label for="companion-name">Companion Name</label>
                    <input class="field" id="companion-name"
                        placeholder="Enter companion's name"
                        maxlength="80">
                </div>

                <div class="field-group">
                    <label for="realm-name">Realm / Setting</label>
                    <input class="field" id="realm-name"
                        placeholder="Enter your fantasy realm"
                        maxlength="120">
                </div>
            </div>

            <h3>Your Personalized Scenario</h3>

            <div class="script-output" id="scenario-script"
                data-template="{esc(script)}"></div>

            <div class="counter" id="word-counter">
                0 words · Approximately 0 tokens
            </div>

            <div class="studio-actions">
                <button class="button" id="copy-script">
                    Copy Roleplay Prompt
                </button>
                <button class="button secondary" id="font-smaller">
                    A−
                </button>
                <button class="button secondary" id="font-larger">
                    A+
                </button>
            </div>

            <div class="twist-box">
                <h3>Unexpected Plot Twists</h3>
                <p>Give your adventure a surprising new direction.</p>
                <button class="button gold" id="generate-twist">
                    Generate Random Plot Twist
                </button>
                <div id="twist-output" style="margin-top:15px"
                    aria-live="polite"></div>
            </div>

            <script type="application/json" id="twist-data">{twist_json}</script>

            <div class="audio-box">
                <h3>Fantasy Realm Ambience Player</h3>
                <p class="muted">Original synthesized atmospheric sound
                using your browser's Web Audio API. No external audio files.</p>

                <div class="audio-controls">
                    <button class="button" id="audio-toggle">
                        Play Ambience
                    </button>

                    <select class="select" id="sound-mode"
                        style="width:auto;max-width:100%">
                        <option value="forest">Enchanted Forest Wind</option>
                        <option value="tavern">Tavern Hearth Crackling</option>
                        <option value="cosmic">Deep Cosmic Drone</option>
                    </select>

                    <label for="sound-volume">Volume</label>
                    <input type="range" id="sound-volume"
                        min="0" max="100" value="35">
                </div>
            </div>
        </div>
    </section>

    <section class="section">
        <div class="affiliate">
            <div class="eyebrow">Fantasy Companion Experience</div>
            <h2>Continue Your Adventure Beyond the Page</h2>
            <p>Explore AI character companions and bring your favorite
            fictional worlds to life through interactive conversations.</p>
            <a class="button gold" href="{esc(AFFILIATE_URL)}"
               rel="nofollow sponsored">
                {esc(AFFILIATE_CTA_TEXT)}
            </a>
        </div>
    </section>

    <!-- AD_SLOT_MID_CONTENT -->

    <section class="section">
        <h2>About This Fantasy Scenario</h2>
        <p>{esc(row["description"])}</p>
        <p>This fictional roleplay prompt belongs to the
        {esc(row["category"])} collection and explores the
        {esc(row["subcategory"])} theme. Customize the characters,
        setting, and plot direction to create your own unique narrative.</p>

        <h3>Target Keyword</h3>
        <p class="muted">{esc(row["target_keyword"])}</p>

        <h3>Scenario Writing Prompt</h3>
        <p class="muted">Use the interactive studio above to customize
        and copy your personalized version of this scenario.</p>
    </section>

    <section class="section">
        <h2>Frequently Asked Questions</h2>
        {''.join(
            f'<div class="faq"><h3>{esc(row[q])}</h3>'
            f'<p class="muted">{esc(row[a])}</p></div>'
            for q, a in [
                ("faq_q1", "faq_a1"),
                ("faq_q2", "faq_a2")
            ]
            if row[q] and row[a]
        ) or '<p class="muted">More information coming soon.</p>'}
    </section>

    <section class="section">
        <div class="section-heading">
            <h2>Related Fantasy Scenarios</h2>
            <span class="count">Explore more adventures</span>
        </div>
        {render_cards(related)}
    </section>

    <section class="section">
        <h2>Explore More Topics</h2>
        <div class="pills">
            <a class="pill"
               href="/topic/{quote(row["subcategory_slug"])}.html">
               {esc(row["subcategory"])}
            </a>
            <a class="pill"
               href="/category/{quote(row["category_slug"])}/page-1.html">
               {esc(row["category"])}
            </a>
        </div>
    </section>
</main>
"""

    content += schema

    extra_head = (
        '<meta property="og:type" content="article">'
        + '<meta property="article:section" content="'
        + esc(row["category"]) + '">'
    )

    page = page_template(
        f'{row["title"]} | {SITE_NAME}',
        row["description"],
        url_path,
        content,
        extra_head,
    )

    write_file(DIST / url_path, page)


# ============================================================
# PAGINATED CATEGORY HUBS
# ============================================================


def build_category_pages(indexes):
    for cat_slug, items in indexes["categories"].items():
        ordered = sorted(
            items,
            key=lambda row: row["date_object"],
            reverse=True
        )

        total_pages = max(
            1,
            (len(ordered) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        )

        for page_number in range(1, total_pages + 1):
            start = (page_number - 1) * ITEMS_PER_PAGE
            subset = ordered[start:start + ITEMS_PER_PAGE]

            category_name = indexes["category_names"][cat_slug]

            prev_link = ""
            next_link = ""

            if page_number > 1:
                prev_link = (
                    f'<link rel="prev" href="{esc(canonical_url(
                        f"category/{cat_slug}/page-{page_number-1}.html"
                    ))}">'
                )

            if page_number < total_pages:
                next_link = (
                    f'<link rel="next" href="{esc(canonical_url(
                        f"category/{cat_slug}/page-{page_number+1}.html"
                    ))}">'
                )

            pagination = f"""
            <div class="pagination">
                {(
                    f'<a class="button secondary" href="page-{page_number-1}.html">Previous</a>'
                    if page_number > 1 else ''
                )}
                <span class="muted">Page {page_number} of {total_pages}</span>
                {(
                    f'<a class="button" href="page-{page_number+1}.html">Next</a>'
                    if page_number < total_pages else ''
                )}
            </div>
            """

            content = f"""
<main class="container">
    <div class="breadcrumbs"><a href="/">Home</a> ›
        {esc(category_name)}</div>

    <section class="hero">
        <span class="eyebrow">Fantasy Category Hub</span>
        <h1>{esc(category_name)}</h1>
        <p>Discover {len(ordered)} interactive fantasy scenarios
        in the {esc(category_name)} collection.</p>
    </section>

    <section class="section">
        <div class="section-heading">
            <h2>Explore {esc(category_name)}</h2>
            <span class="count">{len(ordered)} scenarios</span>
        </div>
        {render_cards(subset)}
        {pagination}
    </section>
</main>
"""

            relative_path = (
                f"category/{cat_slug}/page-{page_number}.html"
            )

            extra = prev_link + next_link

            page = page_template(
                f"{category_name} Fantasy Scenarios | Page {page_number}",
                f"Explore {len(ordered)} {category_name} fantasy roleplay "
                "scenarios, prompts, and interactive storytelling adventures.",
                relative_path,
                content,
                extra,
            )

            write_file(DIST / relative_path, page)


# ============================================================
# SUBCATEGORY AND TAG HUBS
# ============================================================


def build_collection_hub(
    collection,
    names,
    folder,
    title_prefix,
    description_prefix
):
    for item_slug, items in collection.items():
        name = names[item_slug]

        ordered = sorted(
            items,
            key=lambda row: row["date_object"],
            reverse=True
        )

        content = f"""
<main class="container">
    <div class="breadcrumbs"><a href="/">Home</a> ›
        {esc(name)}</div>

    <section class="hero">
        <span class="eyebrow">{esc(title_prefix)}</span>
        <h1>{esc(name)}</h1>
        <p>{esc(description_prefix)} {len(ordered)} scenarios.</p>
    </section>

    <section class="section">
        <div class="section-heading">
            <h2>Explore {esc(name)}</h2>
            <span class="count">{len(ordered)} scenarios</span>
        </div>
        {render_cards(ordered)}
    </section>
</main>
"""

        relative_path = f"{folder}/{item_slug}.html"

        page = page_template(
            f"{name} | {SITE_NAME}",
            f"{description_prefix} Discover {len(ordered)} "
            f"fantasy roleplay scenarios about {name}.",
            relative_path,
            content,
        )

        write_file(DIST / relative_path, page)


# ============================================================
# XML SITEMAP
# ============================================================


def build_sitemaps(rows, indexes):
    urls = [
        {
            "loc": canonical_url(""),
            "lastmod": datetime.utcnow().strftime("%Y-%m-%d"),
            "priority": "1.0",
        }
    ]

    for row in rows:
        date = row["date_object"]

        urls.append({
            "loc": canonical_url(
                f"scenario/{row['slug']}.html"
            ),
            "lastmod": (
                date.strftime("%Y-%m-%d")
                if date != datetime.min
                else datetime.utcnow().strftime("%Y-%m-%d")
            ),
            "priority": "0.8",
        })

    for cat_slug, items in indexes["categories"].items():
        total_pages = max(
            1,
            (len(items) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE
        )

        for page_number in range(1, total_pages + 1):
            urls.append({
                "loc": canonical_url(
                    f"category/{cat_slug}/page-{page_number}.html"
                ),
                "lastmod": datetime.utcnow().strftime("%Y-%m-%d"),
                "priority": "0.7",
            })

    for sub_slug in indexes["subcategories"]:
        urls.append({
            "loc": canonical_url(f"topic/{sub_slug}.html"),
            "lastmod": datetime.utcnow().strftime("%Y-%m-%d"),
            "priority": "0.6",
        })

    for tag_slug in indexes["tags"]:
        urls.append({
            "loc": canonical_url(f"tag/{tag_slug}.html"),
            "lastmod": datetime.utcnow().strftime("%Y-%m-%d"),
            "priority": "0.5",
        })

    urls.extend([
        {
            "loc": canonical_url("dmca.html"),
            "lastmod": datetime.utcnow().strftime("%Y-%m-%d"),
            "priority": "0.3",
        },
        {
            "loc": canonical_url("2257.html"),
            "lastmod": datetime.utcnow().strftime("%Y-%m-%d"),
            "priority": "0.3",
        },
    ])

    sitemap_header = """<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="/sitemap.xsl"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

    sitemap_footer = "\n</urlset>"

    def make_entry(item):
        return f"""
    <url>
        <loc>{esc(item["loc"])}</loc>
        <lastmod>{esc(item["lastmod"])}</lastmod>
        <changefreq>monthly</changefreq>
        <priority>{item["priority"]}</priority>
    </url>"""

    chunks = [
        urls[i:i + 40000]
        for i in range(0, len(urls), 40000)
    ]

    if not chunks:
        chunks = [[]]

    for number, chunk in enumerate(chunks, start=1):
        xml = (
            sitemap_header
            + "".join(make_entry(item) for item in chunk)
            + sitemap_footer
        )

        write_file(DIST / f"sitemap-{number}.xml", xml)

    if len(chunks) == 1:
        write_file(
            DIST / "sitemap.xml",
            sitemap_header
            + "".join(make_entry(item) for item in chunks[0])
            + sitemap_footer
        )
    else:
        index = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
"""

        for number in range(1, len(chunks) + 1):
            index += f"""
    <sitemap>
        <loc>{esc(canonical_url(f"sitemap-{number}.xml"))}</loc>
        <lastmod>{datetime.utcnow().strftime("%Y-%m-%d")}</lastmod>
    </sitemap>"""

        index += "\n</sitemapindex>"

        write_file(DIST / "sitemap.xml", index)

    xsl = r"""<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
 xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
 xmlns:s="http://www.sitemaps.org/schemas/sitemap/0.9">
<xsl:output method="html" encoding="UTF-8" indent="yes"/>
<xsl:template match="/">
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Fantasy Roleplay Hub Sitemap</title>
<style>
body{background:#080a10;color:#f3f4f6;font:15px system-ui;margin:0;padding:35px}
main{max-width:1100px;margin:auto}
h1{color:#c084fc}
table{width:100%;border-collapse:collapse;background:#121624;border-radius:12px}
td,th{padding:14px;text-align:left;border-bottom:1px solid #272b3b}
a{color:#c4a2ff;overflow-wrap:anywhere}
th{color:#f59e0b}
</style>
</head>
<body><main>
<h1>Fantasy Roleplay Hub — XML Sitemap</h1>
<p>Explore the indexed pages of our fantasy scenario directory.</p>
<table>
<tr><th>Page URL</th><th>Last Modified</th><th>Priority</th></tr>
<xsl:for-each select="s:urlset/s:url">
<tr>
<td><a href="{s:loc}"><xsl:value-of select="s:loc"/></a></td>
<td><xsl:value-of select="s:lastmod"/></td>
<td><xsl:value-of select="s:priority"/></td>
</tr>
</xsl:for-each>
</table>
</main></body>
</html>
</xsl:template>
</xsl:stylesheet>
"""

    write_file(DIST / "sitemap.xsl", xsl)


# ============================================================
# LEGAL PAGES
# ============================================================


def build_legal_pages():
    dmca = f"""
<main class="container section">
    <span class="eyebrow">Legal Information</span>
    <h1>DMCA Copyright Policy</h1>

    <p>{esc(SITE_NAME)} respects intellectual property rights and
    expects users and contributors to do the same.</p>

    <h2>Copyright Infringement Notifications</h2>
    <p>If you believe material published on this website infringes
    your copyright, submit a written notification containing:</p>

    <ul>
        <li>Identification of the copyrighted work.</li>
        <li>Identification of the allegedly infringing material and its URL.</li>
        <li>Your contact information.</li>
        <li>A statement of good-faith belief that the use is unauthorized.</li>
        <li>A statement that the information is accurate and that you are
        authorized to act on behalf of the copyright owner.</li>
        <li>Your physical or electronic signature.</li>
    </ul>

    <h2>Contact</h2>
    <p>Email: <a href="mailto:{esc(CONTACT_EMAIL)}">
        {esc(CONTACT_EMAIL)}</a></p>

    <p>We review properly submitted notices and may remove or restrict
    access to material when appropriate.</p>

    <h2>Counter-Notifications</h2>
    <p>If content has been removed in error, you may contact us with
    supporting information and a counter-notification.</p>

    <p class="muted">Last reviewed: <span class="live-year">
        {CURRENT_YEAR}</span></p>
</main>
"""

    write_file(
        DIST / "dmca.html",
        page_template(
            f"DMCA Policy | {SITE_NAME}",
            "Copyright policy, infringement notices, and contact information.",
            "dmca.html",
            dmca,
        )
    )

    section_2257 = f"""
<main class="container section">
    <span class="eyebrow">Compliance Information</span>
    <h1>18 U.S.C. § 2257 Compliance Statement</h1>

    <p>{esc(SITE_NAME)} is an informational and fictional
    fantasy roleplay scenario website.</p>

    <p>The website primarily publishes text-based fictional scenarios,
    writing prompts, character descriptions, and interactive storytelling
    resources.</p>

    <p>{esc(SITE_NAME)} does not claim to produce or host third-party
    explicit visual depictions of actual sexually explicit conduct.</p>

    <p>Where applicable, content is provided as fictional text for
    creative writing and entertainment purposes.</p>

    <p>This statement is an informational description of the site's
    content and is not a representation that every possible statutory
    obligation is automatically satisfied.</p>

    <h2>Content Contact</h2>
    <p>For questions concerning published material, contact:</p>
    <p><a href="mailto:{esc(CONTACT_EMAIL)}">
        {esc(CONTACT_EMAIL)}</a></p>

    <h2>Age Restriction</h2>
    <p>This website is intended for visitors aged 18 and older.
    Visitors must comply with the applicable laws in their jurisdiction.</p>

    <p class="muted">Last reviewed: <span class="live-year">
        {CURRENT_YEAR}</span></p>
</main>
"""

    write_file(
        DIST / "2257.html",
        page_template(
            f"2257 Compliance Statement | {SITE_NAME}",
            "Content classification and compliance information for Fantasy Roleplay Hub.",
            "2257.html",
            section_2257,
        )
    )


# ============================================================
# ROBOTS AND HOSTING CONFIGURATION
# ============================================================


def build_robots():
    content = f"""User-agent: *
Allow: /

Sitemap: {canonical_url("sitemap.xml")}
"""

    write_file(DIST / "robots.txt", content)


def build_hosting_files():
    headers = """/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  X-Frame-Options: SAMEORIGIN

/*.html
  Cache-Control: public, max-age=3600, must-revalidate

/*.css
  Cache-Control: public, max-age=86400

/*.js
  Cache-Control: public, max-age=86400

/sitemap*.xml
  Content-Type: application/xml; charset=utf-8

/sitemap.xsl
  Content-Type: application/xslt+xml; charset=utf-8
"""

    write_file(DIST / "_headers", headers)

    redirects = """# Canonical homepage
/index.htm / 301
/home.html / 301
"""

    write_file(DIST / "_redirects", redirects)


# ============================================================
# HTML VALIDATION
# ============================================================


def validate_output():
    errors = []

    required = [
        "index.html",
        "sitemap.xml",
        "sitemap.xsl",
        "robots.txt",
        "dmca.html",
        "2257.html",
        "_headers",
        "_redirects",
    ]

    for item in required:
        if not (DIST / item).exists():
            errors.append(f"Missing required output: {item}")

    html_files = list(DIST.rglob("*.html"))

    for path in html_files:
        source = path.read_text(encoding="utf-8")

        if "<title>" not in source:
            errors.append(f"Missing title: {path}")

        if 'name="description"' not in source:
            errors.append(f"Missing meta description: {path}")

        if 'name="rating"' not in source:
            errors.append(f"Missing RTA rating: {path}")

        if 'rel="canonical"' not in source:
            errors.append(f"Missing canonical URL: {path}")

    if errors:
        raise RuntimeError(
            "Build validation failed:\n- "
            + "\n- ".join(errors)
        )

    return len(html_files)


# ============================================================
# BUILD REPORT
# ============================================================


def print_report(rows, indexes, html_count):
    total_categories = len(indexes["categories"])
    total_topics = len(indexes["subcategories"])
    total_tags = len(indexes["tags"])

    print("\n" + "=" * 60)
    print(f" {SITE_NAME.upper()} — BUILD COMPLETE")
    print("=" * 60)

    print(f"Base URL:             {BASE_URL}")
    print(f"Scenarios:            {len(rows)}")
    print(f"Unique categories:    {total_categories}")
    print(f"Unique subcategories: {total_topics}")
    print(f"Unique tags:          {total_tags}")
    print(f"HTML pages:           {html_count}")

    print(f"Items per category page: {ITEMS_PER_PAGE}")
    print(f"Related scenarios:       {RELATED_LIMIT}")
    print(f"Newest homepage items:   {NEWEST_LIMIT}")

    print(f"Output directory:     {DIST}")
    print(f"Generated at:         {datetime.utcnow().isoformat()} UTC")

    print("=" * 60)
    print("Deployment:")
    print("  npx wrangler pages deploy dist")
    print("=" * 60)


# ============================================================
# MAIN BUILD PIPELINE
# ============================================================


def main():
    print("\nLoading fantasy scenario database...")

    rows = load_data()

    if DIST.exists():
        shutil.rmtree(DIST)

    DIST.mkdir(parents=True, exist_ok=True)

    indexes = build_indexes(rows)

    print(f"Loaded {len(rows)} valid scenarios.")

    print("Building homepage...")
    build_homepage(rows, indexes)

    print("Building individual scenario pages...")

    for index, row in enumerate(rows, start=1):
        build_detail_page(row, rows)

        if index % 100 == 0:
            print(f"  Generated {index}/{len(rows)} detail pages")

    print("Building paginated category hubs...")
    build_category_pages(indexes)

    print("Building dedicated subcategory hubs...")
    build_collection_hub(
        indexes["subcategories"],
        indexes["subcategory_names"],
        "topic",
        "Fantasy Story Topic",
        "Discover interactive fantasy roleplay scenarios about"
    )

    print("Building dedicated tag hubs...")
    build_collection_hub(
        indexes["tags"],
        indexes["tag_names"],
        "tag",
        "Fantasy Scenario Tag",
        "Explore fantasy roleplay scenarios tagged with"
    )

    print("Generating XML sitemaps...")
    build_sitemaps(rows, indexes)

    print("Generating legal pages...")
    build_legal_pages()

    print("Generating robots.txt...")
    build_robots()

    print("Generating Cloudflare hosting configuration...")
    build_hosting_files()

    print("Validating generated pages...")
    html_count = validate_output()

    print_report(rows, indexes, html_count)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBuild interrupted.")
        raise SystemExit(130)
    except Exception as error:
        print(f"\nBUILD ERROR: {error}")
        raise SystemExit(1)
