import os
import importlib
import pkgutil
import xml.etree.ElementTree as ET
from collections import defaultdict
import scrapers

REPO_RAW_BASE = "https://githubusercontent.com"

def slugify(text):
    return text.strip().lower().replace(" ", "-")

def write_xml(filepath, channel_list):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tv = ET.Element("tv", {"generator-info-name": "epg-directory"})
    
    for meta, _ in channel_list:
        ch = ET.SubElement(tv, "channel", {"id": meta["id"]})
        ET.SubElement(ch, "display-name", {"lang": "en"}).text = meta["name"]
        
    for meta, programs in channel_list:
        for p in programs:
            prog = ET.SubElement(tv, "programme", {
                "start": p["start"],
                "stop": p["stop"],
                "channel": meta["id"]
            })
            ET.SubElement(prog, "title", {"lang": "en"}).text = p["title"]
            
    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write(filepath, encoding="utf-8", xml_declaration=True)

def generate_readme(all_channels, by_area, by_category):
    lines = [
        "# 📺 EPG Directory",
        "",
        "Automated XMLTV Electronic Program Guides grouped by **Area**, **Category**, and **Channel**.",
        "",
        "### 🌐 Master Guide",
        "| Description | Channels | EPG URL |",
        "| :--- | :---: | :--- |",
        f"| All Channels | {len(all_channels)} | `{REPO_RAW_BASE}/all.xml` |",
        "",
        "### 📍 By Area",
        "| Area | Channels | EPG URL |",
        "| :--- | :---: | :--- |"
    ]
    for area in sorted(by_area.keys()):
        slug = slugify(area)
        lines.append(f"| {area} | {len(by_area[area])} | `{REPO_RAW_BASE}/area/{slug}.xml` |")

    lines.extend([
        "",
        "### 🗂️ By Category",
        "| Category | Channels | EPG URL |",
        "| :--- | :---: | :--- |"
    ])
    for cat in sorted(by_category.keys()):
        slug = slugify(cat)
        lines.append(f"| {cat} | {len(by_category[cat])} | `{REPO_RAW_BASE}/category/{slug}.xml` |")

    lines.extend([
        "",
        "### 📋 Supported Channels",
        "| Channel Name | `tvg-id` | Area | Category |",
        "| :--- | :--- | :--- | :--- |"
    ])
    for meta, _ in sorted(all_channels, key=lambda x: x["name"]):
        areas = ", ".join(meta.get("area", []))
        cats = ", ".join(meta.get("category", []))
        lines.append(f"| {meta['name']} | `{meta['id']}` | {areas} | {cats} |")

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    all_channels = []
    by_area = defaultdict(list)
    by_category = defaultdict(list)

    for _, module_name, _ in pkgutil.iter_modules(scrapers.__path__):
        try:
            mod = importlib.import_module(f"scrapers.{module_name}")
            meta, programs = mod.get_programs()
            all_channels.append((meta, programs))
            for area in meta.get("area", []):
                by_area[area].append((meta, programs))
            for cat in meta.get("category", []):
                by_category[cat].append((meta, programs))
            print(f"Loaded {meta['name']}: {len(programs)} programs")
        except Exception as e:
            print(f"Error scraping {module_name}: {e}")

    write_xml("epg/all.xml", all_channels)
    for area, items in by_area.items():
        write_xml(f"epg/area/{slugify(area)}.xml", items)
    for cat, items in by_category.items():
        write_xml(f"epg/category/{slugify(cat)}.xml", items)

    generate_readme(all_channels, by_area, by_category)

if __name__ == "__main__":
    main()
