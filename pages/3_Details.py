import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Comprehensive Details Page")

st.write("This page offers detailed insights and interactive visualizations.")

# Example: Create a DataFrame
data = {
    "Category": ["A", "B", "C", "D"],
    "Values": [23, 45, 12, 67],
}
df = pd.DataFrame(data)

# Display the DataFrame
st.write("Here is a sample dataset:")
st.dataframe(df)

# Plot a bar chart
fig, ax = plt.subplots()
ax.bar(df["Category"], df["Values"], color="skyblue")
ax.set_title("Bar Chart Example")
st.pyplot(fig)

# Add interactivity
st.write("Select a category to display its value:")
selected_category = st.selectbox("Category", df["Category"])
if selected_category:
    value = df.loc[df["Category"] == selected_category, "Values"].values[0]
    st.write(f"The value for category {selected_category} is {value}.")