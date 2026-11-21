import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone

API_URL = "https://televi.fandom.com/api.php?action=parse&page=ALLTV2_Program_Schedule_(2026)&prop=wikitext&format=json"
TZ = timezone(timedelta(hours=8))

CHANNEL_META = {
    "id": "AllTV.ph",
    "name": "ALLTV",
    "display_names": ["ALLTV", "ALLTV2", "All TV", "AllTV.ph"],
    "area": ["Philippines"],
    "category": ["Entertainment"]
}

# Fallback schedule in case the Fandom API is temporarily unreachable
FALLBACK_SCHEDULES = {
    "weekday": [
        ("5:30am", "Kapamilya Daily Mass"),
        ("6:00am", "Knowledge Channel School Anywhere"),
        ("7:30am", "The Flying House"),
        ("8:00am", "Superbook Reimagined (season 5)"),
        ("8:30am", "Blockbusters sa Umaga"),
        ("12:00pm", "It's Showtime"),
        ("2:30pm", "Mommy Guard"),
        ("3:15pm", "Senior High (rerun)"),
        ("4:00pm", "Kapamilya Gold Hits"),
        ("5:30pm", "TV Patrol Express"),
        ("5:45pm", "Minute to Win It"),
        ("6:30pm", "TV Patrol"),
        ("8:00pm", "Coco Martin: Sigabo"),
        ("8:45pm", "Someone, Someday"),
        ("9:30pm", "The Loyalty Game: Level Up!"),
        ("10:15pm", "Breeze by the Sea"),
        ("11:00pm", "The World Tonight"),
        ("12:00am", "Off air")
    ],
    "saturday": [
        ("5:00am", "Tomorrow World"),
        ("5:30am", "Kapamilya Daily Mass"),
        ("6:00am", "LEGO City Adventures"),
        ("6:30am", "Crayon Shai Chan"),
        ("7:00am", "Team YeY! (rerun)"),
        ("7:30am", "Wansapanataym (rerun)"),
        ("8:30am", "Sagot ni Doc."),
        ("9:30am", "Dapat Legal"),
        ("10:15am", "Blockbusters sa Umaga"),
        ("12:00pm", "It's Showtime"),
        ("2:30pm", "Kapamilya Action Sabado"),
        ("4:00pm", "Tao Po!"),
        ("4:45pm", "Philippines' Oddest Job"),
        ("5:00pm", "S.O.C.O.: Scene Of the Crime Operatives"),
        ("5:45pm", "TV Patrol Weekend"),
        ("6:45pm", "Ibang Level To!"),
        ("7:30pm", "Kapamilya, Deal or No Deal (season 6)"),
        ("8:30pm", "MMK: Maaalala Mo Kaya"),
        ("9:30pm", "Matteo G. Primetime"),
        ("10:30pm", "Super Kapamilya Blockbusters"),
        ("12:30am", "Off air")
    ],
    "sunday": [
        ("6:00am", "The Healing Eucharist"),
        ("7:00am", "Wikaharian"),
        ("7:25am", "Ready, Set, Read!"),
        ("7:50am", "MathDali"),
        ("8:15am", "Estudyantipid"),
        ("8:40am", "Wow"),
        ("9:00am", "Wansapanataym (rerun)"),
        ("10:00am", "Blockbusters sa Umaga"),
        ("12:00pm", "Vibe+ Playback"),
        ("1:45pm", "Sunday Blockbusters"),
        ("3:15pm", "My Puhunan: Kaya Mo!"),
        ("3:45pm", "Philippines' Most Haunted"),
        ("4:15pm", "Rated Korina"),
        ("5:15pm", "TV Patrol Weekend"),
        ("6:15pm", "Ibang Level To!"),
        ("7:00pm", "ASAP XP"),
        ("9:00pm", "Kapamilya, Deal or No Deal (season 6)"),
        ("10:00pm", "MMK: Maalaala Mo Kaya"),
        ("11:00pm", "Sunday's Best"),
        ("1:00am", "Off air")
    ]
}

def parse_time(time_str, base_date):
    clean = time_str.strip().upper()
    clean = re.sub(r"\bNN\b", "PM", clean)
    clean = re.sub(r"\bMN\b", "AM", clean)
    dt = datetime.strptime(clean, "%I:%M%p")
    return base_date.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)

def fetch_schedules_from_fandom():
    req = urllib.request.Request(
        API_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        wikitext = data.get("parse", {}).get("wikitext", {}).get("*", "")

    if not wikitext:
        return None

    line_re = re.compile(r"^\*\s*(\d{1,2}:\d{2}\s*(?:am|pm|AM|PM))\s*(?:-|–|—)\s*(.+)$")
    cur_mode = None
    schedules = {"weekday": [], "saturday": [], "sunday": []}

    for line in wikitext.splitlines():
        l = line.strip()
        if "Mondays-Fridays" in l:
            cur_mode = "weekday"
        elif "Saturdays" in l:
            cur_mode = "saturday"
        elif "Sundays" in l:
            cur_mode = "sunday"
        elif cur_mode:
            m = line_re.match(l)
            if m:
                schedules[cur_mode].append((m.group(1).strip(), m.group(2).strip()))

    if not schedules["weekday"] or not schedules["saturday"] or not schedules["sunday"]:
        return None
    return schedules

def get_programs():
    try:
        schedules = fetch_schedules_from_fandom()
        if not schedules:
            schedules = FALLBACK_SCHEDULES
    except Exception as e:
        print(f"Warning: Fandom API fetch failed ({e}). Using verified fallback schedule.")
        schedules = FALLBACK_SCHEDULES

    now_ph = datetime.now(TZ)
    programs = []

    for day_offset in range(7):
        target_date = now_ph + timedelta(days=day_offset)
        wd = target_date.weekday()
        if wd == 5:
            day_shows = schedules["saturday"]
        elif wd == 6:
            day_shows = schedules["sunday"]
        else:
            day_shows = schedules["weekday"]

        for i, (t_str, title) in enumerate(day_shows):
            if "off air" in title.lower() or "off-air" in title.lower():
                continue

            start_dt = parse_time(t_str, target_date)

            if i + 1 < len(day_shows):
                next_t_str, _ = day_shows[i + 1]
                stop_dt = parse_time(next_t_str, target_date)
                if stop_dt <= start_dt:
                    stop_dt += timedelta(days=1)
            else:
                stop_dt = start_dt + timedelta(minutes=60)

            programs.append({
                "start": start_dt.strftime("%Y%m%d%H%M%S +0800"),
                "stop": stop_dt.strftime("%Y%m%d%H%M%S +0800"),
                "title": title
            })

    return CHANNEL_META, programs
