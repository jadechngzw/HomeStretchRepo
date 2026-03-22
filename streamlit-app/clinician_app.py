import streamlit as st

st.title("March 20, 2026")

col1, col2 = st.columns(2)

with col1:
    # stuff for left side
    st.image("examplepic.jpg", caption="Video of patient working out")
with col2:
    # stuff for right side
