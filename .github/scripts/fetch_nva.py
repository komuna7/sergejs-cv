#!/usr/bin/env python3
"""Writes hands-on vacancies near Rīga from the State Employment Agency open dataset to a JSON file."""
import csv
import io
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

PACKAGE_URL = "https://data.gov.lv/dati/api/3/action/package_show?id=vakances"
AD_PREFIX = "https://cvvp.nva.gov.lv/"
STRONG = re.compile(r"santehni|remontstr|remontatslēdz|siltumtehni|namdar|tehniskais strādnieks|ēku|mājsaimniek", re.I)
OTHER = re.compile(r"palīgstrādn|labiekārto|atslēdznie|apsaimnieko|apkopes", re.I)
EXCLUDE = re.compile(r"ceļu|sterilizāc|bibliotēk|noliktav|ritošā|elektro|elektriķ|auto", re.I)
REGION = re.compile(r"Rīga|Mārup|Ķekav|Salaspil|Ropaž|Ādaž|Olain|Babīt|Jūrmal|Saulkrast|Sigulda|Siguldas|Ogre|Ogres|Stopiņ|Carnikav|Baldon|Garkaln|Ikšķil|Lielvārd|Ķegums|Ķeguma", re.I)


def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "job-search-page/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def money(value):
    try:
        return round(float(value), 2)
    except ValueError:
        return None


def to_job(row):
    title = row["Vakances_nosaukums"].strip()
    url = row["Vakances_paplasinats_apraksts"].strip()
    return {
        "id": row["Vakances_Nr"].strip(),
        "title": title.capitalize() if title.isupper() else title,
        "reg": row["Iestades_registracijas_numurs"].strip(),
        "place": row["Vieta"].strip(),
        "from": money(row["Alga_no"]),
        "to": money(row["Alga_lidz"]),
        "deadline": row["Pieteiksanas_termins"].strip(),
        "load": row["Slodzes_tips"].strip(),
        "url": url if url.startswith(AD_PREFIX) else "",
        "strong": bool(STRONG.search(title)),
    }


def is_wanted(row, today):
    title = row["Vakances_nosaukums"]
    if EXCLUDE.search(title) or not (STRONG.search(title) or OTHER.search(title)):
        return False
    town = ",".join(row["Vieta"].split(",")[1:])  # the first part is the street, and "Rīgas iela" exists in every town
    return bool(REGION.search(town)) and row["Pieteiksanas_termins"].strip() >= today


def main(target):
    package = json.loads(download(PACKAGE_URL))["result"]
    resource = next(r for r in package["resources"] if r.get("format", "").upper() == "CSV")
    text = download(resource["url"]).decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        raise SystemExit("Dataset is empty, keeping the previous file")
    today = date.today().isoformat()
    jobs = sorted((to_job(r) for r in rows if is_wanted(r, today)), key=lambda j: (not j["strong"], j["deadline"], j["title"]))
    payload = {"updated": (resource.get("last_modified") or today)[:10], "scanned": len(rows), "jobs": jobs}
    Path(target).write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(jobs)} of {len(rows)} vacancies written")


if __name__ == "__main__":
    main(sys.argv[1])
