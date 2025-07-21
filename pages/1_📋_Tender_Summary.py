import streamlit as st
import json
import os
from utils.validation import (
    validate_scraped_data,
    quick_website_comparison,
    test_random_links
)

st.set_page_config(page_title="Tender Summary", layout="wide")
st.title("📋 Tender Summary")

json_file = "output/tender_opportunities.json"


if not os.path.exists(json_file):
    st.error("Tender file not found.")
    st.stop()

validation = validate_scraped_data(json_file)
if validation is None:
    st.error("Validation failed — check if the JSON file is empty or malformed.")
    st.stop()

comparison = quick_website_comparison(json_file)
if comparison is None:
    st.warning("⚠️ Could not fetch website comparison — skipping coverage metric.")

links = test_random_links(json_file)
if links is None:
    st.warning("⚠️ Could not test links — skipping link success metric.")

st.subheader("🔍 Key Stats")
st.metric("Total Tenders", validation.get("total_tenders", "N/A"))
st.metric("Overall Score", f"{validation.get('overall_score', 0):.1f}%")

from datetime import datetime

with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)
    scraped_raw = data.get("metadata", {}).get("last_scraped_at")

try:
    dt = datetime.fromisoformat(scraped_raw.replace("Z", ""))
    scraped_at = dt.strftime('%Y-%m-%d %H:%M')
except Exception as e:
    scraped_at = "Unknown"


st.metric("Scraped At", scraped_at)
if links:
    st.metric("Link Success", f"{links.get('success_rate', 0):.1f}%")
