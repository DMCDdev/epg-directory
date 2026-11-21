from datetime import datetime, timedelta, timezone
import html
import re
import subprocess
from bs4 import BeautifulSoup
import requests

URL = "https://alltv.ph/dailyschedule/"
TZ = timezone(timedelta(hours=8))

CHANNEL_META = {
    "id": "AllTV.ph",
    "name": "ALLTV2",
    "area": ["Philippines"],
    "category": ["Entertainment"]
}

DAYS_MAP = {
    0: "category-monday",
    1: "category-tuesday",
    2: "category-wednesday",
    3: "category-thursday",
    4: "category-friday",
    5: "category-saturday",
    6: "category-sunday"
}

# Verified schedule from alltv.ph/dailyschedule/
FALLBACK_WEEKDAY = [
    ("Kapamilya Daily Mass", "5:30 AM", "6:00 AM"),
    ("School Anywhere", "6:00 AM", "7:00 AM"),
    ("Komiks Presents", "7:00 AM", "8:00 AM"),
    ("The Flying House", "8:00 AM", "8:30 AM"),
    ("Superbook Reimagined", "8:30 AM", "9:00 AM"),
    ("Magandang Buhay", "9:00 AM", "10:00 AM"),
    ("Kapamilya Blockbusters", "10:00 AM", "12:00 NN"),
    ("It's Showtime", "12:00 PM", "2:30 PM"),
    ("Lavender Fields", "2:30 PM", "3:15 PM"),
    ("Senior High", "3:15 PM", "4:00 PM"),
    ("Kapamilya Gold Hits", "4:00 PM", "5:30 PM"),
    ("TV Patrol Express", "5:30 PM", "5:45 PM"),
    ("Minute to Win It", "5:45 PM", "6:30 PM"),
    ("TV Patrol", "6:30 PM", "8:00 PM"),
    ("FPJ's Batang Quiapo", "8:00 PM", "8:45 PM"),
    ("Roja", "8:45 PM", "9:30 PM"),
    ("What Lies Beneath", "9:30 PM", "10:15 PM"),
    ("Forbidden Flower", "10:15 PM", "10:45 PM"),
    ("The World Tonight", "10:45 PM", "11:15 PM"),
]

FALLBACK_SATURDAY = [
    ("Bubu And The Little Owls", "6:00 AM", "6:30 AM"),
    ("Dinoman", "6:30 AM", "7:00 AM"),
    ("Team Yey", "7:00 AM", "7:30 AM"),
    ("Wansapanataym", "7:30 AM", "8:30 AM"),
    ("KB Family Weekend", "8:30 AM", "12:00 PM"),
    ("It's Showtime", "12:00 PM", "2:30 PM"),
    ("Kapamilya Action Sabado", "3:15 PM", "4:30 PM"),
    ("SOCO", "4:30 PM", "5:15 PM"),
    ("TV Patrol", "5:15 PM", "6:15 PM"),
    ("Rainbow Ramble", "6:15 PM", "7:15 PM"),
    ("Your Face Sounds Familiar", "7:15 PM", "8:15 PM"),
    ("MMK", "8:15 PM", "9:15 PM"),
    ("Tao Po", "9:15 PM", "10:00 PM"),
    ("Super Kapamilya Blockbusters", "10:00 PM", "12:00 AM"),
]

FALLBACK_SUNDAY = [
    ("Healing Eucharist", "6:00 AM", "7:00 AM"),
    ("Wikaharian Online World", "7:00 AM", "7:25 AM"),
    ("Ready Set Read", "7:25 AM", "7:50 AM"),
    ("Mathdali", "7:50 AM", "8:15 AM"),
    ("Estudyantipid", "8:15 AM", "8:40 AM"),
    ("WOW", "8:40 AM", "9:00 AM"),
    ("KB Family Weekend", "9:00 AM", "12:00 PM"),
    ("ASAP", "12:00 PM", "2:15 PM"),
    ("Sunday Blockbusters", "2:15 PM", "4:00 PM"),
    ("My Puhunan", "4:00 PM", "4:30 PM"),
    ("Kuan On One", "4:30 PM", "5:15 PM"),
    ("TV Patrol", "5:15 PM", "6:15 PM"),
    ("Rainbow Ramble", "6:15 PM", "7:15 PM"),
    ("Your Face Sounds Familiar", "7:15 PM", "8:15 PM"),
    ("Rated Korina", "8:15 PM", "9:15 PM"),
    ("Mega Blockbusters", "9:45 PM", "10:45 PM"),
    ("Sunday's Best", "10:45 PM", "12:45 AM"),
]

def parse_time(time_str, base_date):
    clean = time_str.strip().upper()
    clean = re.sub(r"\bNN\b", "PM", clean)
    clean = re.sub(r"\bMN\b", "AM", clean)
    dt = datetime.strptime(clean, "%I:%M %p")
    return base_date.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)

def fetch_html():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    # Method 1: Requests with full browser headers
    try:
        resp = requests.get(URL, headers=headers, timeout=15)
        if resp.status_code == 200 and len(resp.text) > 1000:
            return resp.text
    except Exception:
        pass

    # Method 2: System curl fallback (common on Ubuntu GitHub runners)
    try:
        cmd = [
            "curl", "-sL", "--compressed",
            "-H", f"User-Agent: {headers['User-Agent']}",
            "-H", f"Accept: {headers['Accept']}",
            "-H", f"Accept-Language: {headers['Accept-Language']}",
            URL
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0 and len(result.stdout) > 1000:
            return result.stdout
    except Exception:
        pass

    return None

def get_programs():
    html_content = fetch_html()
    day_schedules = {d: [] for d in range(7)}

    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        time_re = re.compile(
            r"^(\d{1,2}:\d{2}\s*(?:AM|PM|NN|MN))\s*(?:to|-|–)\s*(\d{1,2}:\d{2}\s*(?:AM|PM|NN|MN))$",
            re.I
        )
        articles = soup.find_all("article")
        for article in articles:
            classes = " ".join(article.get("class", []))
            title_tag = article.find("h3", class_="elementor-post__title")
            if not title_tag:
                continue

            raw_text = title_tag.get_text("\n").strip()
            lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
            if len(lines) < 2:
                continue

            show_title = html.unescape(lines[0])
            time_text = lines[1]
            m = time_re.match(time_text)
            if not m:
                continue

            start_str, stop_str = m.group(1), m.group(2)
            for day_num, day_class in DAYS_MAP.items():
                if day_class in classes:
                    day_schedules[day_num].append((show_title, start_str, stop_str))

    # If Cloudflare returned 403 or empty HTML, use the verified schedule
    has_live_shows = any(len(shows) > 0 for shows in day_schedules.values())
    if not has_live_shows:
        for d in range(5):
            day_schedules[d] = list(FALLBACK_WEEKDAY)
        day_schedules[5] = list(FALLBACK_SATURDAY)
        day_schedules[6] = list(FALLBACK_SUNDAY)

    now_ph = datetime.now(TZ)
    programs = []

    for day_offset in range(7):
        target_date = now_ph + timedelta(days=day_offset)
        dow = target_date.weekday()
        shows = day_schedules.get(dow, [])

        for title, start_str, stop_str in shows:
            start_dt = parse_time(start_str, target_date)
            stop_dt = parse_time(stop_str, target_date)
            if stop_dt <= start_dt:
                stop_dt += timedelta(days=1)

            programs.append({
                "start": start_dt.strftime("%Y%m%d%H%M%S +0800"),
                "stop": stop_dt.strftime("%Y%m%d%H%M%S +0800"),
                "title": title
            })

    return CHANNEL_META, programs
