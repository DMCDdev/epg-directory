import os
import importlib
import pkgutil
import xml.etree.ElementTree as ET
from collections import defaultdict
import scrapers

# Direct raw base URL for your GitHub repository
REPO_RAW_BASE = "https://raw.githubusercontent.com/DMCDdev/epg-directory/main/epg"

def slugify(text):
    return text.strip().lower().replace(" ", "-")

def write_xml(filepath, channel_list):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    tv = ET.Element("tv", {"generator-info-name": "epg-directory"})
    
    # 1. Channel Definitions with all aliases
    for meta, _ in channel_list:
        ch = ET.SubElement(tv, "channel", {"id": meta["id"]})
        display_names = meta.get("display_names", [meta["name"]])
        for dn in display_names:
            ET.SubElement(ch, "display-name", {"lang": "en"}).text = dn
        
    # 2. Programme Schedules
    for meta, programs in channel_list:
        for p in programs:
            prog = ET.SubElement(tv, "programme", {
                "start": p["start"],
                "stop": p["stop"],
                "channel": meta["id"]
            })
            ET.SubElement(prog, "title", {"lang": "en"}).text = p["title"]
            if p.get("desc"):
                ET.SubElement(prog, "desc", {"lang": "en"}).text = p["desc"]
            
    ET.indent(tv, space="  ")
    ET.ElementTree(tv).write(filepath, encoding="utf-8", xml_declaration=True)

def generate_readme(all_channels, by_area, by_category):
    lines = [
        "# EPG Directory",
        "",
        "Automated XMLTV Electronic Program Guides grouped by **Area**, **Category**, and **Channel**.",
        "",
        "### Master Guide",
        "| Description | Channels | EPG URL |",
        "| :--- | :---: | :--- |",
        f"| All Channels | {len(all_channels)} | `{REPO_RAW_BASE}/all.xml` |",
        "",
        "### By Area",
        "| Area | Channels | EPG URL |",
        "| :--- | :---: | :--- |"
    ]
    for area in sorted(by_area.keys()):
        slug = slugify(area)
        lines.append(f"| {area} | {len(by_area[area])} | `{REPO_RAW_BASE}/area/{slug}.xml` |")

    lines.extend([
        "",
        "### By Category",
        "| Category | Channels | EPG URL |",
        "| :--- | :---: | :--- |"
    ])
    for cat in sorted(by_category.keys()):
        slug = slugify(cat)
        lines.append(f"| {cat} | {len(by_category[cat])} | `{REPO_RAW_BASE}/category/{slug}.xml` |")

    lines.extend([
        "",
        "### Individual Channels",
        "| Channel Name | tvg-id | Area | Category | Single-Channel EPG URL |",
        "| :--- | :--- | :--- | :--- | :--- |"
    ])
    for meta, _ in sorted(all_channels, key=lambda item: item[0]["name"]):
        areas = ", ".join(meta.get("area", []))
        cats = ", ".join(meta.get("category", []))
        ch_slug = slugify(meta["id"])
        lines.append(f"| {meta['name']} | `{meta['id']}` | {areas} | {cats} | `{REPO_RAW_BASE}/channel/{ch_slug}.xml` |")

    with open("README.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

def main():
    all_channels = []
    by_area = defaultdict(list)
    by_category = defaultdict(list)

    modules = list(pkgutil.iter_modules(scrapers.__path__))
    print(f"Found scraper modules: {[m.name for m in modules]}")

    for _, module_name, _ in modules:
        mod = importlib.import_module(f"scrapers.{module_name}")
        meta, programs = mod.get_programs()
        print(f"Loaded {meta['name']}: {len(programs)} programs")
        all_channels.append((meta, programs))
        for area in meta.get("area", []):
            by_area[area].append((meta, programs))
        for cat in meta.get("category", []):
            by_category[cat].append((meta, programs))

    # Output master, area, category, and single-channel XML files
    write_xml("epg/all.xml", all_channels)
    for area, items in by_area.items():
        write_xml(f"epg/area/{slugify(area)}.xml", items)
    for cat, items in by_category.items():
        write_xml(f"epg/category/{slugify(cat)}.xml", items)
    for meta, programs in all_channels:
        write_xml(f"epg/channel/{slugify(meta['id'])}.xml", [(meta, programs)])

    # Update README with fresh links
    generate_readme(all_channels, by_area, by_category)
    print("Build complete.")

if __name__ == "__main__":
    main()
