import streamlit as st
import pandas as pd
import json
from datetime import datetime

st.set_page_config(page_title="CPV Breakdown", layout="wide")
st.title("📊 CPV Code Overview")

json_file = "output/tender_opportunities.json"

try:
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    tenders = data.get("tenders", [])

    cpv_records = []
    for tender in tenders:
        codes = tender.get("cpv_codes", [])
        descriptions = tender.get("cpv_descriptions", [])
        for code, desc in zip(codes, descriptions):
            cpv_records.append({
                "cpv_code": code,
                "cpv_description": desc
            })

    cpv_df = pd.DataFrame(cpv_records)

    cpv_summary = (
        cpv_df
        .groupby(["cpv_code", "cpv_description"])
        .size()
        .reset_index(name="tender_count")
        .sort_values(by="tender_count", ascending=False)
    )

    st.subheader("📌 CPV Summary")
    st.dataframe(cpv_summary, use_container_width=True)

    st.subheader("🗓️ Upcoming Tender Notices")

    today = datetime.today()
    upcoming_tenders = []

    for tender in tenders:
        details = tender.get("details", {})
        deadline_raw = details.get("Submission deadline")
        try:
            deadline_dt = pd.to_datetime(deadline_raw, dayfirst=True, errors="coerce")
        except:
            deadline_dt = None

        if deadline_dt and deadline_dt >= pd.Timestamp(today):
            upcoming_tenders.append({
                "title": tender.get("title", "Untitled"),
                "organisation": tender.get("organisation", "Unknown"),
                "deadline": deadline_raw,
                "link": tender.get("link", "#"),
                "cpv_descriptions": ", ".join(tender.get("cpv_descriptions", [])),
                "days_left": (deadline_dt - pd.Timestamp(today)).days
            })

    upcoming_tenders = sorted(upcoming_tenders, key=lambda x: pd.to_datetime(x["deadline"], dayfirst=True))

    if not upcoming_tenders:
        st.info("✅ No upcoming tenders found.")
    else:
        for tender in upcoming_tenders:
            with st.container():
                st.markdown(f"### 📌 {tender['title']}")
                st.markdown(f"**🏛 Organisation:** {tender['organisation']}")
                st.markdown(f"**🗓 Deadline:** {tender['deadline']} ({tender['days_left']} days left)")
                st.markdown(f"**📋 CPV:** {tender['cpv_descriptions']}")
                st.markdown(f"[🔗 View Notice]({tender['link']})")
                st.markdown("---")

except Exception as e:
    st.error(f"❌ Error loading or processing file: {e}")
