import requests
from bs4 import BeautifulSoup
from datetime import datetime, date
from office365.runtime.auth.authentication_context import AuthenticationContext
from office365.sharepoint.client_context import ClientContext


# SharePoint credentials (replace with yours)
USERNAME = "ahmed.khalid@arcadis.com"
PASSWORD = "Karm@koul5669"

# SharePoint site and list info
SITE_URL = "https://arcadiso365.sharepoint.com/teams/ArcadisRailConsultancyHS2Team"
LIST_NAME = "tenders register1"

def scrape_today_tenders():
    today = date.today()
    url = "https://www.find-tender.service.gov.uk/Search/Results?sort=unix_published_date%3ADESC"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, "html.parser")

    tenders = []
    results = soup.find_all("div", class_="search-result")
    for result in results:
        try:
            title_tag = result.find("h2")
            link = title_tag.find("a")["href"]
            title = title_tag.text.strip()
            org = result.find("div", class_="search-result-sub-header").text.strip()
            description_tag = result.find("div", class_="wrap-text")
            description = description_tag.text.strip() if description_tag else ""

            published_text = ""
            details = result.find_all("div", class_="search-result-entry")
            for entry in details:
                key = entry.find("dt").text.strip()
                if "Publication date" in key:
                    published_text = entry.find("dd").text.strip().split(",")[0]

            published_date = datetime.strptime(published_text, "%d %B %Y").date()
            if published_date != today:
                continue

            tenders.append({
                "title": title,
                "link": link,
                "organisation": org,
                "description": description,
                "published_date": published_date.isoformat()
            })

        except Exception as e:
            print(f"❌ Skipping tender due to error: {e}")
    return tenders

def upload_to_sharepoint(tenders):
    ctx_auth = AuthenticationContext(SITE_URL)
    if ctx_auth.acquire_token_for_user(USERNAME, PASSWORD):
        ctx = ClientContext(SITE_URL, ctx_auth)
        sp_list = ctx.web.lists.get_by_title(LIST_NAME)

        for tender in tenders:
            item_create_info = {
                'Title': tender["title"],
                'Organisation': tender["organisation"],
                'Description': tender["description"],
                'Published date': tender["published_date"],
                'URL Link': {
                    '__metadata': {'type': 'SP.FieldUrlValue'},
                    'Description': 'View tender',
                    'Url': tender["link"]
                }
            }
            item = sp_list.add_item(item_create_info)
            ctx.execute_query()
            print(f"✅ Uploaded: {tender['title']}")
    else:
        print("❌ Failed to authenticate to SharePoint")

if __name__ == "__main__":
    print("🔍 Scraping today's tenders...")
    today_tenders = scrape_today_tenders()
    print(f"📦 Found {len(today_tenders)} tenders for today.")
    if today_tenders:
        print("⬆️ Uploading to SharePoint...")
        upload_to_sharepoint(today_tenders)
