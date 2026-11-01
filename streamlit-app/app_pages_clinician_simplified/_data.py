from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st


def workbook_path() -> Path | None:
    """Find the repository workbook when running from streamlit-app."""
    candidates = [Path.cwd() / "Data.xlsx", Path(__file__).resolve().parents[2] / "Data.xlsx"]
    return next((path for path in candidates if path.is_file()), None)


@st.cache_data(show_spinner=False)
def _load_workbook(contents: bytes) -> tuple[pd.DataFrame, pd.DataFrame]:
    book = pd.ExcelFile(BytesIO(contents))
    required = {"Typical", "Atypical", "Participant Identification"}
    missing = required.difference(book.sheet_names)
    if missing:
        raise ValueError("Missing workbook sheets: " + ", ".join(sorted(missing)))

    people = book.parse("Participant Identification")
    typical = book.parse("Typical")
    atypical = book.parse("Atypical")
    for frame in (people, typical, atypical):
        frame.columns = [str(column).strip() for column in frame.columns]
    for frame in (typical, atypical):
        if "Exercise" not in frame and "Exercize" in frame:
            frame.rename(columns={"Exercize": "Exercise"}, inplace=True)
        for old in ("ParticpantName", "ParticipantName"):
            if "Participant Name" not in frame and old in frame:
                frame.rename(columns={old: "Participant Name"}, inplace=True)

    typical = typical.assign(**{"Recording Type": "Typical"})
    atypical = atypical.assign(**{"Recording Type": "Atypical"})
    recordings = pd.concat([typical, atypical], ignore_index=True)
    people["Participant ID"] = pd.to_numeric(people["Participant ID"], errors="coerce")
    recordings["Participant ID"] = pd.to_numeric(recordings["Participant ID"], errors="coerce")
    people = people.dropna(subset=["Participant ID"])
    recordings = recordings.dropna(subset=["Participant ID"])

    counts = recordings.pivot_table(
        index="Participant ID", columns="Recording Type", values="Filename", aggfunc="count", fill_value=0
    )
    for kind in ("Typical", "Atypical"):
        if kind not in counts:
            counts[kind] = 0
    roster = people.merge(counts[["Typical", "Atypical"]], on="Participant ID", how="left")
    roster[["Typical", "Atypical"]] = roster[["Typical", "Atypical"]].fillna(0).astype(int)
    roster["Total recordings"] = roster["Typical"] + roster["Atypical"]
    roster["Typical %"] = (
        roster["Typical"].div(roster["Total recordings"].replace(0, pd.NA)).fillna(0) * 100
    ).round().astype(int)

    if "Notes" not in recordings:
        recordings["Notes"] = ""
    recordings["Notes"] = recordings["Notes"].fillna("").astype(str)
    notes = (
        recordings.loc[recordings["Recording Type"] == "Atypical"]
        .groupby("Participant ID")["Notes"]
        .apply(lambda values: "; ".join(value.strip() for value in values if value.strip()))
        .rename("Notes")
    )
    roster = roster.merge(notes, on="Participant ID", how="left")
    roster["Notes"] = roster["Notes"].fillna("")
    return roster.sort_values("Participant ID"), recordings


def get_data() -> tuple[pd.DataFrame, pd.DataFrame] | None:
    """Load the local workbook or ask for it once per Streamlit session."""
    path = workbook_path()
    if path:
        try:
            return _load_workbook(path.read_bytes())
        except Exception as error:
            st.error(f"Could not read {path.name}: {error}")
            return None

    st.info("The HomeStretch workbook was not found beside the app. Upload it to view recording data.")
    upload = st.file_uploader("Upload Data.xlsx", type=["xlsx"], key="workbook_upload")
    if upload is None:
        return None
    try:
        return _load_workbook(upload.getvalue())
    except Exception as error:
        st.error(f"Could not read the workbook: {error}")
        return None
