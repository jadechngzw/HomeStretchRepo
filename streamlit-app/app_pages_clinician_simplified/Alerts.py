import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _data import get_data

st.title("Recording review")
st.caption("Patients with atypical movement recordings in the workbook.")
data = get_data()
if data is None:
    st.stop()
roster, recordings = data
flagged = roster[roster["Atypical"] > 0].copy()
if flagged.empty:
    st.success("No atypical recordings are listed in this workbook.")
    st.stop()

st.warning("These are recording review cues only; they do not indicate clinical risk or urgent alerts.")
for _, patient in flagged.iterrows():
    pid = patient["Participant ID"]
    detail = recordings[(recordings["Participant ID"] == pid) & (recordings["Recording Type"] == "Atypical")]
    with st.container(border=True):
        st.subheader(f"{patient['Participant']} · ID {int(pid)}")
        st.write(f"{int(patient['Atypical'])} atypical recording(s)")
        if patient["Notes"]:
            st.caption("Workbook notes: " + patient["Notes"])
        cols = [column for column in ("Exercise", "Left or Right", "Filename") if column in detail]
        st.dataframe(detail[cols], hide_index=True, use_container_width=True)
