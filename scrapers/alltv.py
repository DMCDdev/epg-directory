import re
from datetime import datetime, timedelta, timezone
import requests
from bs4 import BeautifulSoup

URL = "https://alltv.ph"
TZ = timezone(timedelta(hours=8))

CHANNEL_META = {
    "id": "AllTV.ph",
    "name": "ALLTV2",
    "area": ["Philippines"],
    "category": ["Entertainment"]
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
    lines = [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]

    schedules = []
    current_day = []
    last_hour = -1

    for i, line in enumerate(lines):
        match = time_re.match(line)
        if match and i > 0:
            title = lines[i - 1]
            if title.upper() in ["ALL DAYS", "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY", "DAILY SCHEDULE"]:
                continue
            start_str, stop_str = match.group(1), match.group(2)
            temp_dt = parse_time(start_str, datetime(2026, 1, 1))
            if last_hour != -1 and temp_dt.hour < last_hour - 4:
                if current_day:
                    schedules.append(current_day)
                current_day = []
            current_day.append((title, start_str, stop_str))
            last_hour = temp_dt.hour

    if current_day:
        schedules.append(current_day)

    # Safely pick weekday, saturday, and sunday blocks without bracket indexing
    it = iter(schedules)
    weekday = next(it, [])
    saturday = next(it, weekday)
    sunday = next(it, saturday)

    now_ph = datetime.now(TZ)
    programs = []
    for day_offset in range(7):
        target_date = now_ph + timedelta(days=day_offset)
        dow = target_date.weekday()
        if dow == 5:
            day_progs = saturday
        elif dow == 6:
            day_progs = sunday
        else:
            day_progs = weekday

        for title, start_str, stop_str in day_progs:
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
