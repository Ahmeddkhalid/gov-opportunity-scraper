import requests, os, json, re, time
from bs4 import BeautifulSoup
from datetime import datetime, date
from urllib.parse import urljoin

BASE_URL = "https://www.find-tender.service.gov.uk"
START_URL = f"{BASE_URL}/Search/Results?sort=unix_published_date%3ADESC"
OUTPUT_FILE = "output/tender_opportunities.json"

# === Session setup ===
session = requests.Session()
headers = {"User-Agent": "Mozilla/5.0"}

def parse_date(text):
    try:
        return datetime.strptime(text.split(',')[0].strip(), "%d %B %Y").date()
    except:
        return None

def extract_cpv_codes(detail_url):
    try:
        res = session.get(detail_url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        ul = soup.find("ul", class_="govuk-list govuk-list--bullet")
        cpvs = []
        if ul:
            for li in ul.find_all("li"):
                match = re.match(r"(\d{8}) - (.+)", li.text.strip())
                if match:
                    cpvs.append({
                        "code": match.group(1),
                        "description": match.group(2)
                    })
        return cpvs
    except:
        return []

def load_existing_data():
    if not os.path.exists(OUTPUT_FILE):
        return set(), None, {"tenders": [], "metadata": {}}

    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        tenders = data.get("tenders", [])
        metadata = data.get("metadata", {})
        existing_ids = {t["tender_id"] for t in tenders if "tender_id" in t}
        last_scraped = metadata.get("last_scraped_at")
        last_scraped_dt = datetime.fromisoformat(last_scraped) if last_scraped else None
        return existing_ids, last_scraped_dt, data

def scrape_newest_tenders(existing_ids, last_scraped_dt):
    page = 1
    all_new = []
    stop = False

    while not stop:
        print(f"📄 Page {page}")
        url = f"{START_URL}&page={page}"
        res = session.get(url, headers=headers)
        soup = BeautifulSoup(res.content, "html.parser")
        results = soup.find_all("div", class_="search-result")
        if not results:
            break

        for r in results:
            link_tag = r.find("h2").find("a")
            link = urljoin(BASE_URL, link_tag["href"])
            title = link_tag.text.strip()
            tender_id = link.split("/")[-1].split("?")[0]

            if tender_id in existing_ids:
                print(f"🛑 Already in JSON: {tender_id}")
                stop = True
                break

            org_div = r.find("div", class_="search-result-sub-header")
            organisation = org_div.text.strip() if org_div else "N/A"
            desc_div = r.find("div", id=re.compile("description"))
            description = desc_div.text.strip() if desc_div else ""

            dl = r.find("dl")
            details, pub_date = {}, None
            if dl:
                for item in dl.find_all("div", class_="search-result-entry"):
                    key = item.find("dt").text.strip()
                    val = item.find("dd").text.strip()
                    details[key] = val
                    if "Publication date" in key:
                        pub_date = parse_date(val)

            scraped_at = datetime.utcnow()

            # Stop if scraped_at is earlier than or equal to last_scraped_at
            if last_scraped_dt and scraped_at <= last_scraped_dt:
                print(f"🛑 Reached previously scraped tender from {scraped_at.isoformat()}")
                stop = True
                break

            cpv_data = extract_cpv_codes(link)
            cpv_codes = [cpv["code"] for cpv in cpv_data]
            cpv_descs = [cpv["description"] for cpv in cpv_data]

            tender = {
                "title": title,
                "link": link,
                "organisation": organisation,
                "description": description,
                "details": details,
                "publication_date_text": details.get("Publication date"),
                "publication_date_parsed": pub_date.isoformat() if pub_date else None,
                "scraped_at": scraped_at.isoformat(),
                "tender_id": tender_id,
                "cpv_codes": cpv_codes,
                "cpv_descriptions": cpv_descs
            }
            all_new.append(tender)

        page += 1
        time.sleep(1)

    return all_new

def append_to_json(new_tenders, existing_data):
    if new_tenders:
        existing_data["tenders"] = new_tenders + existing_data.get("tenders", [])
        existing_data["metadata"]["last_updated"] = datetime.now().isoformat()
        existing_data["metadata"]["last_scraped_at"] = max(
            t["scraped_at"] for t in new_tenders
        )
        existing_data["metadata"]["total_tenders"] = len(existing_data["tenders"])

        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        print(f"✅ Appended {len(new_tenders)} new tenders.")
    else:
        print("✅ No new tenders to append.")

if __name__ == "__main__":
    print(f"🚀 Scraping only newest tenders not in JSON yet...")
    ids, last_scraped, data = load_existing_data()
    new_tenders = scrape_newest_tenders(ids, last_scraped)
    append_to_json(new_tenders, data)
