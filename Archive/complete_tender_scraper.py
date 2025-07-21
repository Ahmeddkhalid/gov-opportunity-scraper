import requests
from bs4 import BeautifulSoup
import time
import json
import os
from datetime import datetime, date
import re

def parse_publication_date(date_string):
    """Parse publication date from the tender listing format like '30 May 2025, 9:52pm'"""
    try:
        # Extract just the date part (before the comma)
        if ',' in date_string:
            date_part = date_string.split(',')[0].strip()
        else:
            date_part = date_string.strip()
        
        # Parse the date in format "30 May 2025"
        parsed_date = datetime.strptime(date_part, '%d %B %Y').date()
        return parsed_date
    except Exception as e:
        print(f"⚠️ Warning: Could not parse date '{date_string}': {e}")
        return None

def extract_tender_titles_and_links(soup, target_date=None):
    """Extract tender titles and their links from a page, with optional date filtering"""
    tenders = []
    should_continue = True  # Flag to indicate if we should continue scraping more pages
    
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
                    
                    # Get organisation name
                    org_div = result.find('div', class_='search-result-sub-header')
                    organisation = org_div.get_text().strip() if org_div else "N/A"
                    
                    # Get additional details
                    description_div = result.find('div', class_='wrap-text')
                    description = ""
                    if description_div and description_div.get('id') and 'description' in description_div.get('id'):
                        description = description_div.get_text().strip()[:200] + "..." if len(description_div.get_text().strip()) > 200 else description_div.get_text().strip()
                    
                    # Extract notice type, value, and other details including publication date
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
                                
                                # Check for publication date
                                if 'Publication date' in key:
                                    publication_date_text = value
                                    publication_date_parsed = parse_publication_date(value)
                    
                    # If we have a target date, check if this tender matches
                    if target_date:
                        if publication_date_parsed:
                            if publication_date_parsed != target_date:
                                # Since results are sorted by newest first, if we encounter a date
                                # that's not our target, we can stop processing
                                if publication_date_parsed < target_date:
                                    print(f"🔍 Found date {publication_date_parsed} which is before target {target_date}. Stopping.")
                                    should_continue = False
                                    break
                                else:
                                    # Skip this tender as it's from a different date (future date)
                                    print(f"⏭️ Skipping tender from {publication_date_parsed} (looking for {target_date})")
                                    continue
                        else:
                            # Skip tenders without valid publication dates
                            print(f"⚠️ Skipping tender '{title}' - no valid publication date found")
                            continue
                    
                    # Add metadata
                    tender_data = {
                        'title': title,
                        'link': href,
                        'organisation': organisation,
                        'description': description,
                        'details': details,
                        'publication_date_text': publication_date_text,
                        'publication_date_parsed': publication_date_parsed.isoformat() if publication_date_parsed else None,
                        'scraped_at': datetime.now().isoformat(),
                        'tender_id': href.split('/')[-1].split('?')[0] if href else None
                    }
                    
                    tenders.append(tender_data)
    
    return tenders, should_continue

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

def scrape_find_tender_complete(target_date_str="30 May 2025"):
    """
    Complete scraper for Find a Tender website with date filtering and sorting by newest
    
    Args:
        target_date_str (str): Date to filter for in format "30 May 2025"
    """
    # Parse the target date
    try:
        target_date = datetime.strptime(target_date_str, '%d %B %Y').date()
        print(f"🎯 Target date: {target_date}")
    except ValueError as e:
        print(f"❌ Invalid date format. Please use format like '30 May 2025'. Error: {e}")
        return []
    
    base_url = "https://www.find-tender.service.gov.uk"
    start_url = "https://www.find-tender.service.gov.uk/Search/Results"
    json_filename = f"output/tender_opportunities_{target_date.strftime('%Y%m%d')}.json"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_tenders = []
    current_page = 1
    should_continue = True
    
    print("🔍 Starting Find a Tender scraper with date filtering...")
    print(f"🎯 Target date: {target_date_str}")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Saving to: {json_filename}")
    print("="*80)
    
    while should_continue:
        try:
            # Build URL for current page with sorting by newest published date
            if current_page == 1:
                # Add sorting parameter for newest published first
                url = f"{start_url}?sort=unix_published_date%3ADESC"
            else:
                url = f"{start_url}?sort=unix_published_date%3ADESC&page={current_page}#dashboard_notices"
            
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
            
            # Extract tenders from current page with date filtering
            page_tenders, should_continue = extract_tender_titles_and_links(soup, target_date)
            
            if not page_tenders:
                if should_continue:
                    print(f"❌ No matching tenders found on page {current_page}")
                else:
                    print(f"✅ No more tenders from target date {target_date_str} found. Stopping.")
                break
            
            all_tenders.extend(page_tenders)
            print(f"✅ Found {len(page_tenders)} tenders from {target_date_str} on page {current_page}")
            
            # Update JSON file with current page data
            update_json_progress(page_tenders, current_page, json_filename)
            
            # Get pagination info
            pagination_info = get_pagination_info(soup)
            
            print(f"📄 Page {pagination_info['current_page']} of {pagination_info['max_page']}")
            
            # Display tenders from this page
            print(f"\n🎯 TENDERS FROM PAGE {current_page} (DATE: {target_date_str}):")
            print("-" * 60)
            
            for i, tender in enumerate(page_tenders, 1):
                print(f"\n🏢 {len(all_tenders) - len(page_tenders) + i}. {tender['title']}")
                print(f"   🏛️  Organisation: {tender['organisation']}")
                print(f"   📅 Published: {tender['publication_date_text']}")
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
                        if 'Publication date' not in key:  # Don't repeat publication date
                            print(f"   📅 {key}: {value}")
                    elif 'location' in key.lower():
                        print(f"   📍 {key}: {value}")
                
                print("-" * 40)
            
            # Check if we should continue to next page
            if not should_continue:
                print(f"\n✅ Reached end of {target_date_str} tenders")
                break
                
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
    print(f"🎯 Target date: {target_date_str}")
    print(f"✅ Total tenders from {target_date_str}: {len(all_tenders)}")
    print(f"📄 Pages scraped: {current_page}")
    print(f"🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Data saved to: {json_filename}")
    
    # Final save to ensure all data is preserved
    save_tenders_to_json(all_tenders, json_filename)
    
    if all_tenders:
        print(f"\n🎯 TENDERS FROM {target_date_str}:")
        print("-" * 60)
        for i, tender in enumerate(all_tenders[:10], 1):  # Show first 10
            print(f"{i}. {tender['title']}")
            print(f"   Organisation: {tender['organisation']}")
            print(f"   Published: {tender['publication_date_text']}")
            print(f"   Link: {tender['link']}")
            print()
        
        if len(all_tenders) > 10:
            print(f"... and {len(all_tenders) - 10} more tenders")
    
    print(f"\n🌐 Visit {start_url} for complete details and to apply")
    print("💡 Tips:")
    print(f"   • Found {len(all_tenders)} tenders published on {target_date_str}")
    print("   • Results are filtered by exact date match")
    print("   • Scraping stops efficiently when encountering older dates")
    print("   • JSON file includes parsed publication dates for further analysis")
    print("   • Use different target dates to scrape other specific days")
    
    print(f"📁 Check '{json_filename}' for the complete dataset")
    
    return all_tenders

if __name__ == "__main__":
    # You can change this date as needed
    target_date = "27 June 2025"  # Change this to your desired date
    tenders = scrape_find_tender_complete(target_date)
    
    # Optional: Display JSON file info
    if tenders:
        print(f"\n💾 Extracted {len(tenders)} tenders from {target_date} successfully!")
        print(f"📁 Check the JSON file for the complete dataset")
        print("Data is also available in the 'tenders' variable for further processing.")
    else:
        print(f"\n📭 No tenders found for {target_date}") 