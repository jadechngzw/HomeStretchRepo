import streamlit as st

st.set_page_config(
    page_title = "Dashboard"
)

# st.title("Welcome to the Clinician App")
# st.sidebar.success("Select a page")

pg = st.navigation([
    st.Page("app_pages2/Messages.py", title="Messages", icon=None),
    st.Page("app_pages2/Exercise.py", title="Exercise", icon=None),
    st.Page("app_pages2/Progress.py", title="Progress", icon=None),
])

pg.run()
