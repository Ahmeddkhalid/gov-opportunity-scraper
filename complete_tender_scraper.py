import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import time
import json
import os
import re
from datetime import datetime, date, timedelta

# Setup session with retry logic
session = requests.Session()
retries = Retry(
    total=3,
    backoff_factor=2,
    status_forcelist=[500, 502, 503, 504],
    allowed_methods=["GET"]
)
adapter = HTTPAdapter(max_retries=retries)
session.mount('https://', adapter)
session.mount('http://', adapter)

def parse_publication_date(date_string):
    try:
        if ',' in date_string:
            date_part = date_string.split(',')[0].strip()
        else:
            date_part = date_string.strip()
        return datetime.strptime(date_part, '%d %B %Y').date()
    except Exception as e:
        print(f"⚠️ Warning: Could not parse date '{date_string}': {e}")
        return None

def extract_cpv_from_detail_page(link, base_url):
    try:
        full_url = link if link.startswith("http") else base_url + link

        if not full_url.startswith("http"):
            print(f"❌ Invalid URL detected: {full_url}")
            return [], []

        res = session.get(full_url, timeout=15)
        if res.status_code != 200:
            print(f"❌ Failed to fetch detail page: {full_url}")
            return [], []

        soup = BeautifulSoup(res.content, 'html.parser')
        cpv_codes = []
        cpv_descriptions = []

        bullet_lists = soup.find_all('ul', class_='govuk-list govuk-list--bullet')
        for ul in bullet_lists:
            for li in ul.find_all('li'):
                text = li.get_text(strip=True)
                match = re.match(r"^(\d{8})\s*-\s*(.+)", text)
                if match:
                    cpv_codes.append(match.group(1))
                    cpv_descriptions.append(match.group(2))

        return cpv_codes, cpv_descriptions
    except Exception as e:
        print(f"⚠️ Could not extract CPV codes from {link}: {e}")
        return [], []

def extract_tender_titles_and_links(soup, threshold_date=None, base_url="https://www.find-tender.service.gov.uk"):
    tenders = []
    should_continue = True
    search_results = soup.find_all('div', class_='search-result')

    for result in search_results:
        header = result.find('div', class_='search-result-header')
        if not header:
            continue
        h2_tag = header.find('h2')
        if not h2_tag:
            continue
        link_tag = h2_tag.find('a')
        if not link_tag:
            continue

        title = link_tag.get_text().strip()
        href = link_tag.get('href')

        org_div = result.find('div', class_='search-result-sub-header')
        organisation = org_div.get_text().strip() if org_div else "N/A"

        description_div = result.find('div', class_='wrap-text')
        description = ""
        if description_div and description_div.get('id') and 'description' in description_div.get('id'):
            desc_text = description_div.get_text().strip()
            description = desc_text[:200] + "..." if len(desc_text) > 200 else desc_text

        details = {}
        publication_date_text = None
        publication_date_parsed = None

        dl_tag = result.find('dl')
        if dl_tag:
            entries = dl_tag.find_all('div', class_='search-result-entry')
            for entry in entries:
                dt = entry.find('dt')
                dd = entry.find('dd')
                if dt and dd:
                    key = dt.get_text().strip()
                    value = dd.get_text().strip()
                    details[key] = value
                    if 'Publication date' in key:
                        publication_date_text = value
                        publication_date_parsed = parse_publication_date(value)

        if threshold_date:
            if publication_date_parsed:
                if publication_date_parsed < threshold_date:
                    print(f"🛑 Tender from {publication_date_parsed} is older than 6 months. Stopping.")
                    should_continue = False
                    break
            else:
                print(f"⚠️ Skipping tender '{title}' - no valid publication date")
                continue

        cpv_codes, cpv_descriptions = extract_cpv_from_detail_page(href, base_url)

        tender_data = {
            'title': title,
            'link': href,
            'organisation': organisation,
            'description': description,
            'details': details,
            'publication_date_text': publication_date_text,
            'publication_date_parsed': publication_date_parsed.isoformat() if publication_date_parsed else None,
            'scraped_at': datetime.now().isoformat(),
            'tender_id': href.split('/')[-1].split('?')[0] if href else None,
            'cpv_codes': cpv_codes,
            'cpv_descriptions': cpv_descriptions
        }

        tenders.append(tender_data)

    return tenders, should_continue

def get_pagination_info(soup):
    pagination_info = {'current_page': 1, 'max_page': 1, 'next_page_url': None}
    pagination = soup.find('ul', class_='gadget-footer-paginate')
    if pagination:
        current = pagination.find('li', class_='standard-paginate-selected')
        if current:
            current_text = current.get_text().strip()
            if current_text.isdigit():
                pagination_info['current_page'] = int(current_text)
        page_links = []
        for li in pagination.find_all('li', class_='standard-paginate'):
            link = li.find('a')
            if link and link.get('href'):
                page_num = link.get_text().strip()
                if page_num.isdigit():
                    page_links.append(int(page_num))
        if page_links:
            pagination_info['max_page'] = max(page_links)
        next_link = pagination.find('a', class_='standard-paginate-next')
        if next_link and next_link.get('href'):
            pagination_info['next_page_url'] = next_link.get('href')
    return pagination_info

def save_tenders_to_json(all_tenders, filename):
    data = {
        "metadata": {
            "total_tenders": len(all_tenders),
            "last_updated": datetime.now().isoformat(),
            "source_url": "https://www.find-tender.service.gov.uk/Search/Results",
            "scraper_version": "2.0"
        },
        "tenders": all_tenders
    }
    try:
        if os.path.exists(filename):
            backup_filename = f"output/backups/{os.path.basename(filename)}.backup_{int(time.time())}"
            os.rename(filename, backup_filename)
            print(f"📁 Backup created: {backup_filename}")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"💾 Saved {len(all_tenders)} tenders to {filename}")
        return True
    except Exception as e:
        print(f"❌ Error saving JSON: {e}")
        return False

def scrape_find_tender_last_6_months():
    threshold_date = date.today() - timedelta(days=182)
    print(f"🎯 Scraping tenders published from {threshold_date}")
    base_url = "https://www.find-tender.service.gov.uk"
    start_url = f"{base_url}/Search/Results"
    json_filename = f"output/tender_opportunities_last6months_with_cpv.json"
    headers = {'User-Agent': 'Mozilla/5.0'}

    current_page = 1
    all_tenders = []

    should_continue = True
    print("=" * 80)

    while should_continue:
        try:
            url = f"{start_url}?sort=unix_published_date%3ADESC&page={current_page}#dashboard_notices"
            print(f"📄 Scraping page {current_page}: {url}")
            response = session.get(url, headers=headers, timeout=20)

            if response.status_code != 200:
                print(f"❌ Page {current_page} failed: HTTP {response.status_code}")
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            page_tenders, should_continue = extract_tender_titles_and_links(soup, threshold_date, base_url)

            if not page_tenders:
                print(f"📭 No tenders on page {current_page}")
                break

            all_tenders.extend(page_tenders)
            save_tenders_to_json(all_tenders, json_filename)

            pagination_info = get_pagination_info(soup)
            print(f"📄 Page {pagination_info['current_page']} of {pagination_info['max_page']}")

            if not should_continue or current_page >= pagination_info['max_page']:
                break

            current_page += 1
            print("⏳ Waiting 2 seconds before next page...")
            time.sleep(2)

        except requests.exceptions.RequestException as e:
            print(f"🌐 Network error: {e}")
            break
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            break

    print("=" * 80)
    print("📊 SCRAPING COMPLETE")
    print(f"✅ Total tenders scraped: {len(all_tenders)}")
    print(f"📁 Data saved in: {json_filename}")
    return all_tenders

if __name__ == "__main__":
    scrape_find_tender_last_6_months()
