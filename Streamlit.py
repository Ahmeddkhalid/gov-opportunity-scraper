import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime

# Load JSON file
json_file = "output/tender_opportunities.json"
if not os.path.exists(json_file):
    st.error(f"JSON file not found: {json_file}")
    st.stop()

# Load and normalize JSON data
with open(json_file, 'r', encoding='utf-8') as f:
    data = json.load(f)

tenders = data.get("tenders", [])
df = pd.json_normalize(tenders)
df['publication_date_parsed'] = pd.to_datetime(df['publication_date_parsed'], errors='coerce')

# Set page config
st.set_page_config(page_title="Tender Opportunities Viewer", layout="wide")
st.title("📋 Tender Opportunities Viewer")

# --- Sidebar ---
st.sidebar.header("🔍 Filters")

# Reset button logic
if st.sidebar.button("🔄 Reset Filters"):
    st.experimental_rerun()

# Search input (title, description, organisation)
search_term = st.sidebar.text_input("Search by keyword (title/org/desc)").strip().lower()

# CPV Code Filter
all_cpv_codes = sorted(df['cpv_codes'].explode().dropna().unique().tolist())
selected_cpvs = st.sidebar.multiselect("Filter by CPV Code", all_cpv_codes)

# Date range filter
min_date = df['publication_date_parsed'].min().date()
max_date = df['publication_date_parsed'].max().date()
date_range = st.sidebar.date_input("Filter by Publication Date Range", [min_date, max_date])

# --- Filtering Logic ---
filtered_df = df.copy()

# Filter by search term
if search_term:
    filtered_df = filtered_df[
        df['title'].str.lower().str.contains(search_term, na=False) |
        df['description'].str.lower().str.contains(search_term, na=False) |
        df['organisation'].str.lower().str.contains(search_term, na=False)
    ]

# Filter by CPV
if selected_cpvs:
    filtered_df = filtered_df[filtered_df['cpv_codes'].apply(
        lambda codes: any(code in codes for code in selected_cpvs) if isinstance(codes, list) else False
    )]

# Filter by date range
if len(date_range) == 2:
    start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    filtered_df = filtered_df[
        filtered_df['publication_date_parsed'].between(start_date, end_date)
    ]

# --- Summary Section ---
st.subheader("📊 Summary")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tenders", len(filtered_df))
col2.metric("Unique Organisations", filtered_df['organisation'].nunique())
cpv_total = filtered_df['cpv_codes'].apply(lambda x: len(x) if isinstance(x, list) else 0).sum()
col3.metric("CPV Codes Present", cpv_total)
if not filtered_df.empty:
    date_min = filtered_df['publication_date_parsed'].min().date()
    date_max = filtered_df['publication_date_parsed'].max().date()
    col4.metric("Date Range", f"{date_min} to {date_max}")
else:
    col4.metric("Date Range", "N/A")

# --- Table ---
st.markdown(f"### 🔎 Showing {len(filtered_df)} filtered tenders")
st.dataframe(filtered_df)

# --- CSV Export ---
st.download_button(
    label="📥 Export Filtered Data to CSV",
    data=filtered_df.to_csv(index=False),
    file_name="filtered_tenders.csv",
    mime="text/csv"
)

# --- Chart ---
if not filtered_df.empty:
    st.subheader("📈 Tenders per CPV Code")
    cpv_chart = filtered_df.explode("cpv_codes").groupby("cpv_codes")["title"].count().sort_values(ascending=False)
    st.bar_chart(cpv_chart)
