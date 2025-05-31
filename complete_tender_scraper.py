import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime

def extract_tender_titles_and_links(soup):
    """Extract tender titles and their links from a page"""
    tenders = []
    
    # Find all search result containers
    search_results = soup.find_all('div', class_='search-result')
    
    for result in search_results:
        # Find the header with title and link
        header = result.find('div', class_='search-result-header')
        if header:
            # Get the h2 tag containing the link
            h2_tag = header.find('h2')
            if h2_tag:
                link_tag = h2_tag.find('a')
                if link_tag:
                    title = link_tag.get_text().strip()
                    href = link_tag.get('href')
                    
                    # Get organization name
                    org_div = result.find('div', class_='search-result-sub-header')
                    organization = org_div.get_text().strip() if org_div else "N/A"
                    
                    # Get additional details
                    description_div = result.find('div', class_='wrap-text')
                    description = ""
                    if description_div and description_div.get('id') and 'description' in description_div.get('id'):
                        description = description_div.get_text().strip()[:200] + "..." if len(description_div.get_text().strip()) > 200 else description_div.get_text().strip()
                    
                    # Extract notice type, value, and other details
                    details = {}
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
                    
                    # Add metadata
                    tender_data = {
                        'title': title,
                        'link': href,
                        'organization': organization,
                        'description': description,
                        'details': details,
                        'scraped_at': datetime.now().isoformat(),
                        'tender_id': href.split('/')[-1].split('?')[0] if href else None
                    }
                    
                    tenders.append(tender_data)
    
    return tenders

def get_pagination_info(soup):
    """Extract pagination information"""
    pagination_info = {
        'current_page': 1,
        'max_page': 1,
        'next_page_url': None
    }
    
    # Find pagination container
    pagination = soup.find('ul', class_='gadget-footer-paginate')
    if pagination:
        # Find current page
        current = pagination.find('li', class_='standard-paginate-selected')
        if current:
            current_text = current.get_text().strip()
            if current_text.isdigit():
                pagination_info['current_page'] = int(current_text)
        
        # Find all page links to determine max page
        page_links = []
        for li in pagination.find_all('li', class_='standard-paginate'):
            link = li.find('a')
            if link and link.get('href'):
                page_num = link.get_text().strip()
                if page_num.isdigit():
                    page_links.append(int(page_num))
        
        if page_links:
            pagination_info['max_page'] = max(page_links)
        
        # Find next page link
        next_link = pagination.find('a', class_='standard-paginate-next')
        if next_link and next_link.get('href'):
            pagination_info['next_page_url'] = next_link.get('href')
    
    return pagination_info

def save_tenders_to_json(all_tenders, filename="output/tender_opportunities.json"):
    """Save tender data to JSON file with metadata"""
    
    # Prepare data structure with metadata
    data = {
        "metadata": {
            "total_tenders": len(all_tenders),
            "last_updated": datetime.now().isoformat(),
            "source_url": "https://www.find-tender.service.gov.uk/Search/Results",
            "scraper_version": "1.0"
        },
        "tenders": all_tenders
    }
    
    try:
        # Create backup if file exists
        if os.path.exists(filename):
            # Extract filename without path for backup
            base_filename = os.path.basename(filename)
            backup_filename = f"output/backups/{base_filename}.backup_{int(time.time())}"
            os.rename(filename, backup_filename)
            print(f"📁 Created backup: {backup_filename}")
        
        # Save to JSON file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved {len(all_tenders)} tenders to {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Error saving to JSON: {e}")
        return False

def update_json_progress(page_tenders, current_page, filename="output/tender_opportunities.json"):
    """Update JSON file with progress after each page"""
    
    try:
        # Load existing data or create new structure
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {
                "metadata": {
                    "total_tenders": 0,
                    "last_updated": datetime.now().isoformat(),
                    "source_url": "https://www.find-tender.service.gov.uk/Search/Results",
                    "scraper_version": "1.0",
                    "pages_scraped": 0
                },
                "tenders": []
            }
        
        # Add new tenders from current page
        existing_ids = {tender.get('tender_id') for tender in data['tenders'] if tender.get('tender_id')}
        new_tenders = []
        
        for tender in page_tenders:
            tender_id = tender.get('tender_id')
            if tender_id not in existing_ids:
                new_tenders.append(tender)
                existing_ids.add(tender_id)
        
        data['tenders'].extend(new_tenders)
        
        # Update metadata
        data['metadata']['total_tenders'] = len(data['tenders'])
        data['metadata']['last_updated'] = datetime.now().isoformat()
        data['metadata']['pages_scraped'] = current_page
        data['metadata']['new_tenders_this_page'] = len(new_tenders)
        
        # Save updated data
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Updated JSON: +{len(new_tenders)} new tenders (Page {current_page}) | Total: {data['metadata']['total_tenders']}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating JSON: {e}")
        return False

def scrape_find_tender_complete():
    """
    Complete scraper for Find a Tender website with pagination support and JSON saving
    """
    base_url = "https://www.find-tender.service.gov.uk"
    start_url = "https://www.find-tender.service.gov.uk/Search/Results"
    json_filename = "output/tender_opportunities.json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_tenders = []
    current_page = 1
    max_pages = 5  # Limit to first 5 pages for demo (remove this limit for full scraping)
    
    print("🔍 Starting Find a Tender scraper with JSON saving...")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Saving to: {json_filename}")
    print("="*80)
    
    while current_page <= max_pages:
        try:
            # Build URL for current page
            if current_page == 1:
                url = start_url
            else:
                url = f"{start_url}?&page={current_page}#dashboard_notices"
            
            print(f"\n📄 Scraping page {current_page}...")
            print(f"🔗 URL: {url}")
            
            response = requests.get(url, headers=headers, timeout=20)
            
            if response.status_code != 200:
                print(f"❌ Failed to load page {current_page}. Status code: {response.status_code}")
                break
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Get page title and basic info
            if current_page == 1:
                title = soup.find('title')
                print(f"📄 Page Title: {title.get_text() if title else 'No title found'}")
                
                # Look for the results count
                results_count = soup.find('span', class_='search-result-count')
                if results_count:
                    total_notices = results_count.get_text().strip()
                    print(f"📊 Total notices available: {total_notices}")
            
            # Extract tenders from current page
            page_tenders = extract_tender_titles_and_links(soup)
            
            if not page_tenders:
                print(f"❌ No tenders found on page {current_page}")
                break
            
            all_tenders.extend(page_tenders)
            print(f"✅ Found {len(page_tenders)} tenders on page {current_page}")
            
            # Update JSON file with current page data
            update_json_progress(page_tenders, current_page, json_filename)
            
            # Get pagination info
            pagination_info = get_pagination_info(soup)
            
            print(f"📄 Page {pagination_info['current_page']} of {pagination_info['max_page']}")
            
            # Display tenders from this page
            print(f"\n🎯 TENDERS FROM PAGE {current_page}:")
            print("-" * 60)
            
            for i, tender in enumerate(page_tenders, 1):
                print(f"\n🏢 {len(all_tenders) - len(page_tenders) + i}. {tender['title']}")
                print(f"   🏛️  Organization: {tender['organization']}")
                print(f"   🔗 Link: {tender['link']}")
                print(f"   🆔 ID: {tender['tender_id']}")
                
                if tender['description']:
                    print(f"   📝 Description: {tender['description']}")
                
                # Display key details
                for key, value in tender['details'].items():
                    if 'Notice type' in key:
                        print(f"   📋 {key}: {value}")
                    elif 'value' in key.lower() and '£' in value:
                        print(f"   💰 {key}: {value}")
                    elif 'deadline' in key.lower() or 'date' in key.lower():
                        print(f"   📅 {key}: {value}")
                    elif 'location' in key.lower():
                        print(f"   📍 {key}: {value}")
                
                print("-" * 40)
            
            # Check if we should continue to next page
            if current_page >= pagination_info['max_page']:
                print(f"\n✅ Reached last page ({pagination_info['max_page']})")
                break
            
            if not pagination_info['next_page_url']:
                print(f"\n✅ No more pages available")
                break
            
            current_page += 1
            
            # Be respectful - add delay between requests
            print(f"⏳ Waiting 2 seconds before next page...")
            time.sleep(2)
            
        except requests.exceptions.Timeout:
            print(f"⏰ Request timed out on page {current_page}")
            break
        except requests.exceptions.RequestException as e:
            print(f"🌐 Network error on page {current_page}: {e}")
            break
        except Exception as e:
            print(f"❌ Error on page {current_page}: {e}")
            break
    
    # Final summary
    print("\n" + "="*80)
    print("📊 SCRAPING SUMMARY")
    print("="*80)
    print(f"✅ Total tenders extracted: {len(all_tenders)}")
    print(f"📄 Pages scraped: {current_page}")
    print(f"🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Data saved to: {json_filename}")
    
    # Final save to ensure all data is preserved
    save_tenders_to_json(all_tenders, json_filename)
    
    if all_tenders:
        print(f"\n🎯 SAMPLE OF EXTRACTED TENDERS:")
        print("-" * 60)
        for i, tender in enumerate(all_tenders[:5], 1):  # Show first 5
            print(f"{i}. {tender['title']}")
            print(f"   Organization: {tender['organization']}")
            print(f"   Link: {tender['link']}")
            print()
    
    print(f"\n🌐 Visit {start_url} for complete details and to apply")
    print("💡 Tips:")
    print("   • Remove the max_pages limit to scrape all pages")
    print("   • JSON file is updated after each page for progress tracking")
    print("   • Backup files are created automatically")
    print("   • Duplicate tenders are automatically filtered out")
    print("   • Use the JSON file for further analysis or import into other tools")
    
    print("📁 Check 'output/tender_opportunities.json' for the complete dataset")
    
    return all_tenders

if __name__ == "__main__":
    tenders = scrape_find_tender_complete()
    
    # Optional: Display JSON file info
    if tenders:
        print(f"\n💾 Extracted {len(tenders)} tenders successfully!")
        print("📁 Check 'output/tender_opportunities.json' for the complete dataset")
        print("Data is also available in the 'tenders' variable for further processing.") 