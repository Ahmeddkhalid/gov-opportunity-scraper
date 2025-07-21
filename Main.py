import streamlit as st

st.set_page_config(
    page_title="Multi-Page App with JSON Data",
    page_icon="🌐",
    layout="wide",
)

st.title("Welcome to My Multi-Page App")
st.write(
    """
    This app demonstrates how to build a multi-page Streamlit app with JSON data.
    Use the navigation on the left to explore the app:
    
    - **Home**: Overview of the app.
    - **Data Overview**: Load and explore the JSON dataset.
    - **Detailed Insights**: Visualize and analyze the JSON data.
    """
)