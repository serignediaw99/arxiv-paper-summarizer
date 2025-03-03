import streamlit as st
import requests

# Set FastAPI backend URL
FASTAPI_URL = "http://127.0.0.1:8000"

st.title("🔍 AI Paper Recommender")

# Input for keywords
keywords = st.text_input("Enter keywords for topics you are interested in (comma-separated):")

if st.button("Search"):
    if keywords:
        response = requests.get(f"{FASTAPI_URL}/search", params={"keywords": keywords})
        
        if response.status_code == 200:
            papers = response.json().get("papers", [])
            
            if papers:
                for paper in papers:
                    st.subheader(paper["title"])
                    st.write(paper["summary"])
            else:
                st.warning("No papers found for the given keywords.")
        else:
            st.error("Error fetching papers. Please try again.")
    else:
        st.warning("Please enter some keywords.")