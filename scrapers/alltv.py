import html
import re
from datetime import datetime, timedelta, timezone
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

def parse_time(time_str, base_date):
    clean = time_str.strip().upper()
    clean = re.sub(r"\bNN\b", "PM", clean)
    clean = re.sub(r"\bMN\b", "AM", clean)
    dt = datetime.strptime(clean, "%I:%M %p")
    return base_date.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)

def get_programs():
    resp = requests.get(URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    time_re = re.compile(
        r"^(\d{1,2}:\d{2}\s*(?:AM|PM|NN|MN))\s*(?:to|-|–)\s*(\d{1,2}:\d{2}\s*(?:AM|PM|NN|MN))$",
        re.I
    )

    day_schedules = {d: [] for d in range(7)}
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
