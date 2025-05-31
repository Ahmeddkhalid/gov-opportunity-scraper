import json
import requests
from bs4 import BeautifulSoup
import random
from datetime import datetime
import os

def validate_scraped_data(json_file="../output/tender_opportunities.json"):
    """Comprehensive validation of scraped data quality"""
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file '{json_file}' not found!")
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return None
    
    tenders = data.get('tenders', [])
    metadata = data.get('metadata', {})
    total = len(tenders)
    
    print("📊 DATA QUALITY VALIDATION REPORT")
    print("="*60)
    print(f"🕒 Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 File: {json_file}")
    print(f"📊 Total tenders: {total}")
    
    if total == 0:
        print("❌ No tenders found in JSON file!")
        return None
    
    # Metadata validation
    print(f"\n📋 METADATA:")
    print(f"   Last updated: {metadata.get('last_updated', 'Unknown')}")
    print(f"   Pages scraped: {metadata.get('pages_scraped', 'Unknown')}")
    print(f"   Source: {metadata.get('source_url', 'Unknown')}")
    
    # Check data completeness
    print(f"\n✅ DATA COMPLETENESS:")
    
    has_title = sum(1 for t in tenders if t.get('title') and len(t.get('title', '').strip()) > 0)
    has_link = sum(1 for t in tenders if t.get('link') and len(t.get('link', '').strip()) > 0)
    has_org = sum(1 for t in tenders if t.get('organisation') and t.get('organisation') != "N/A")
    has_description = sum(1 for t in tenders if t.get('description') and len(t.get('description', '').strip()) > 0)
    has_tender_id = sum(1 for t in tenders if t.get('tender_id'))
    has_details = sum(1 for t in tenders if t.get('details') and len(t.get('details', {})) > 0)
    
    print(f"   📝 Titles: {has_title}/{total} ({has_title/total*100:.1f}%)")
    print(f"   🔗 Links: {has_link}/{total} ({has_link/total*100:.1f}%)")
    print(f"   🏛️  Organisations: {has_org}/{total} ({has_org/total*100:.1f}%)")
    print(f"   📄 Descriptions: {has_description}/{total} ({has_description/total*100:.1f}%)")
    print(f"   🆔 Tender IDs: {has_tender_id}/{total} ({has_tender_id/total*100:.1f}%)")
    print(f"   📋 Details: {has_details}/{total} ({has_details/total*100:.1f}%)")
    
    # Check for duplicates
    print(f"\n🔄 DUPLICATE CHECK:")
    tender_ids = [t.get('tender_id') for t in tenders if t.get('tender_id')]
    unique_ids = set(tender_ids)
    duplicates = len(tender_ids) - len(unique_ids)
    print(f"   Duplicates found: {duplicates}")
    
    if duplicates > 0:
        # Find which IDs are duplicated
        id_counts = {}
        for tid in tender_ids:
            id_counts[tid] = id_counts.get(tid, 0) + 1
        
        duplicate_ids = [tid for tid, count in id_counts.items() if count > 1]
        print(f"   Duplicate IDs: {duplicate_ids[:5]}{'...' if len(duplicate_ids) > 5 else ''}")
    
    # Validate link patterns
    print(f"\n🔗 LINK VALIDATION:")
    valid_links = sum(1 for t in tenders if t.get('link', '').startswith('https://www.find-tender.service.gov.uk/Notice/'))
    invalid_links = total - valid_links
    print(f"   Valid link format: {valid_links}/{total} ({valid_links/total*100:.1f}%)")
    
    if invalid_links > 0:
        print(f"   ⚠️  Invalid links: {invalid_links}")
        # Show examples of invalid links
        invalid_examples = [t.get('link', '') for t in tenders if not t.get('link', '').startswith('https://www.find-tender.service.gov.uk/Notice/')][:3]
        for example in invalid_examples:
            print(f"      Example: {example}")
    
    # Organisation analysis
    print(f"\n🏛️  ORGANISATION ANALYSIS:")
    organisations = [t.get('organisation', '') for t in tenders if t.get('organisation') and t.get('organisation') != "N/A"]
    unique_orgs = set(organisations)
    print(f"   Unique organisations: {len(unique_orgs)}")
    
    # Most common organisations
    org_counts = {}
    for org in organisations:
        org_counts[org] = org_counts.get(org, 0) + 1
    
    top_orgs = sorted(org_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    print(f"   Top organisations:")
    for org, count in top_orgs:
        print(f"      {org}: {count} tenders")
    
    # Quality score calculation
    print(f"\n📊 QUALITY SCORE:")
    
    scores = {
        'completeness': (has_title + has_link + has_tender_id) / (3 * total) * 100,
        'link_validity': (valid_links / total) * 100,
        'organisation_rate': (has_org / total) * 100,
        'duplicate_penalty': max(0, 100 - (duplicates / total) * 100)
    }
    
    overall_score = sum(scores.values()) / len(scores)
    
    for metric, score in scores.items():
        status = "✅" if score >= 90 else "⚠️" if score >= 70 else "❌"
        print(f"   {status} {metric.replace('_', ' ').title()}: {score:.1f}%")
    
    print(f"\n🎯 OVERALL QUALITY: {overall_score:.1f}%")
    
    if overall_score >= 90:
        print("   ✅ Excellent - Data quality is very high")
    elif overall_score >= 70:
        print("   ⚠️  Good - Minor issues detected")
    else:
        print("   ❌ Poor - Significant issues found, review scraper logic")
    
    return {
        'total_tenders': total,
        'completeness_rate': has_title/total,
        'valid_links_rate': valid_links/total,
        'organisation_rate': has_org/total,
        'duplicates': duplicates,
        'overall_score': overall_score,
        'quality_status': 'excellent' if overall_score >= 90 else 'good' if overall_score >= 70 else 'poor'
    }

def generate_validation_sample(json_file="../output/tender_opportunities.json", sample_size=5):
    """Generate random sample for manual verification"""
    
    if not os.path.exists(json_file):
        print(f"❌ JSON file '{json_file}' not found!")
        return None
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return None
    
    tenders = data.get('tenders', [])
    
    if not tenders:
        print("❌ No tenders found in JSON file!")
        return None
    
    actual_sample_size = min(sample_size, len(tenders))
    sample = random.sample(tenders, actual_sample_size)
    
    print(f"\n🎯 MANUAL VALIDATION SAMPLE ({actual_sample_size} tenders)")
    print("="*60)
    print("👀 Please manually verify these randomly selected tenders:")
    print()
    
    for i, tender in enumerate(sample, 1):
        print(f"📋 SAMPLE {i}:")
        print(f"   Title: {tender.get('title', 'N/A')}")
        print(f"   Organisation: {tender.get('organisation', 'N/A')}")
        print(f"   ID: {tender.get('tender_id', 'N/A')}")
        print(f"   🔗 Verify at: {tender.get('link', 'N/A')}")
        
        # Show key details for quick verification
        details = tender.get('details', {})
        if details:
            for key, value in list(details.items())[:3]:  # Show first 3 details
                print(f"   {key}: {value}")
        
        print("-" * 40)
    
    print("\n✅ MANUAL VERIFICATION CHECKLIST:")
    print("   1. Click each link - does it work and go to the correct tender?")
    print("   2. Does the title on the website match our extracted title?")
    print("   3. Does the organisation name match?")
    print("   4. Are the key details (notice type, dates, values) accurate?")
    print("   5. Is the tender ID correct (last part of the URL)?")
    
    return sample

def quick_website_comparison(json_file="../output/tender_opportunities.json"):
    """Compare our scraped count with website's current total"""
    
    print(f"\n🌐 WEBSITE COMPARISON:")
    print("-" * 30)
    
    try:
        # Get current website total
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) WebKit/537.36'}
        response = requests.get("https://www.find-tender.service.gov.uk/Search/Results", headers=headers, timeout=15)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            results_count = soup.find('span', class_='search-result-count')
            
            if results_count:
                website_total = int(results_count.get_text().strip())
                print(f"🌐 Website currently shows: {website_total} notices")
            else:
                print("⚠️  Could not extract current website total")
                return None
        else:
            print(f"❌ Failed to access website (Status: {response.status_code})")
            return None
        
        # Get our scraped total
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                our_data = json.load(f)
                our_total = our_data.get('metadata', {}).get('total_tenders', 0)
                pages_scraped = our_data.get('metadata', {}).get('pages_scraped', 0)
                
            print(f"💾 We scraped: {our_total} notices ({pages_scraped} pages)")
            
            if our_total < website_total:
                coverage = (our_total / website_total) * 100
                print(f"📊 Coverage: {coverage:.1f}%")
                
                if pages_scraped < 10:  # Assuming limited scraping
                    print("   ℹ️  Lower coverage expected due to page limit")
                else:
                    print("   ⚠️  Lower coverage - check for scraping issues")
            elif our_total == website_total:
                print("✅ Perfect match - Full coverage achieved!")
            else:
                print("⚠️  We have MORE than website shows - possible duplicate issue")
            
            return {
                'website_total': website_total,
                'our_total': our_total,
                'coverage': (our_total / website_total) * 100 if website_total > 0 else 0
            }
        else:
            print(f"❌ JSON file '{json_file}' not found!")
            return None
            
    except Exception as e:
        print(f"❌ Error during website comparison: {e}")
        return None

def test_random_links(json_file="../output/tender_opportunities.json", num_tests=3):
    """Test random links to ensure they're working"""
    
    print(f"\n🔗 LINK FUNCTIONALITY TEST:")
    print("-" * 30)
    
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading JSON file: {e}")
        return None
    
    tenders = data.get('tenders', [])
    
    if not tenders:
        print("❌ No tenders found in JSON file!")
        return None
    
    # Test random links
    test_tenders = random.sample(tenders, min(num_tests, len(tenders)))
    
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) WebKit/537.36'}
    working_links = 0
    
    for i, tender in enumerate(test_tenders, 1):
        link = tender.get('link', '')
        title = tender.get('title', 'Unknown')
        
        print(f"🔗 Testing link {i}: {title[:50]}...")
        
        try:
            response = requests.get(link, headers=headers, timeout=10)
            if response.status_code == 200:
                print(f"   ✅ Working (Status: {response.status_code})")
                working_links += 1
            else:
                print(f"   ❌ Failed (Status: {response.status_code})")
        except Exception as e:
            print(f"   ❌ Error: {str(e)[:50]}...")
    
    success_rate = (working_links / len(test_tenders)) * 100
    print(f"\n📊 Link test results: {working_links}/{len(test_tenders)} working ({success_rate:.1f}%)")
    
    if success_rate == 100:
        print("✅ All tested links are working!")
    elif success_rate >= 80:
        print("⚠️  Most links working, some issues detected")
    else:
        print("❌ Significant link issues found")
    
    return {
        'tested': len(test_tenders),
        'working': working_links,
        'success_rate': success_rate
    }

def save_validation_report(json_file="../output/tender_opportunities.json", report_file="validation_report/validation_report.txt"):
    """Save comprehensive validation report to file"""
    
    import sys
    from io import StringIO
    
    # Capture output
    old_stdout = sys.stdout
    sys.stdout = captured_output = StringIO()
    
    try:
        # Run all validations
        print(f"TENDER DATA VALIDATION REPORT")
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        validate_scraped_data(json_file)
        quick_website_comparison(json_file)
        test_random_links(json_file)
        
        # Get the captured output
        report_content = captured_output.getvalue()
        
    finally:
        # Restore stdout
        sys.stdout = old_stdout
    
    # Save to file
    try:
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)
        print(f"📁 Validation report saved to: {report_file}")
        return True
    except Exception as e:
        print(f"❌ Error saving report: {e}")
        return False

def full_validation(json_file="../output/tender_opportunities.json", sample_size=5):
    """Run complete validation suite"""
    
    print("🚀 STARTING FULL VALIDATION SUITE")
    print("="*60)
    
    # 1. Data quality validation
    quality_results = validate_scraped_data(json_file)
    
    # 2. Website comparison
    comparison_results = quick_website_comparison(json_file)
    
    # 3. Link testing
    link_results = test_random_links(json_file)
    
    # 4. Generate manual validation sample
    sample = generate_validation_sample(json_file, sample_size)
    
    # 5. Save report
    save_validation_report(json_file)
    
    # Final summary
    print(f"\n🎯 VALIDATION SUMMARY:")
    print("="*30)
    
    if quality_results:
        print(f"📊 Overall Quality: {quality_results['overall_score']:.1f}% ({quality_results['quality_status']})")
        print(f"📋 Total Tenders: {quality_results['total_tenders']}")
        print(f"🔄 Duplicates: {quality_results['duplicates']}")
    
    if comparison_results:
        print(f"🌐 Website Coverage: {comparison_results['coverage']:.1f}%")
    
    if link_results:
        print(f"🔗 Link Success Rate: {link_results['success_rate']:.1f}%")
    
    print(f"\n💡 Next Steps:")
    if quality_results and quality_results['overall_score'] >= 90:
        print("   ✅ Data quality is excellent - ready for use!")
    elif quality_results and quality_results['overall_score'] >= 70:
        print("   ⚠️  Review any issues noted above")
        print("   📝 Perform manual spot checks on the sample")
    else:
        print("   ❌ Review scraper logic for significant issues")
        print("   🔧 Check extraction patterns and selectors")
    
    print("   📁 Check validation_report.txt for detailed results")

if __name__ == "__main__":
    # Run full validation if script is executed directly
    full_validation() 