import streamlit as st
import pandas as pd
import json

st.title("Data Overview")

# Load JSON data with utf-8 encoding
with open("output/tender_opportunities.json", "r", encoding="utf-8") as file:
    data = json.load(file)

# Remove the 'metadata' section if it exists
if "metadata" in data:
    del data["metadata"]  # This will exclude the metadata section

# If the remaining data is nested, access the relevant part
# Assuming the useful data is stored in a key like "tenders"
if "tenders" in data:
    data = data["tenders"]

# Convert JSON data to a Pandas DataFrame
try:
    df = pd.DataFrame(data)  # Try converting directly
except ValueError:
    st.write("Data is nested; attempting to normalize...")
    df = pd.json_normalize(data)  # Flatten nested structures

# Display the DataFrame
st.write("### JSON Data Loaded")
st.dataframe(df)  # Display as an interactive table

# Allow users to filter or search the data
st.write("### Filtered Data")
filter_column = st.selectbox("Select a column to filter by:", df.columns)
filter_value = st.text_input(f"Enter a value to filter {filter_column}:")
if filter_value:
    filtered_df = df[df[filter_column].astype(str).str.contains(filter_value, case=False)]
    st.write(filtered_df)
else:
    st.write("Enter a value to filter the data.")

# Option to download the data
st.write("### Download JSON Data")
st.download_button(
    label="Download Filtered JSON",
    data=json.dumps(data, indent=4),
    file_name="filtered_data.json",
    mime="application/json",
)