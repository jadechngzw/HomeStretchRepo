import streamlit as st
import pandas as pd
import numpy as np
from numpy.random import default_rng

# -----------------------
# Setup
# -----------------------
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

if "page" not in st.session_state:
    st.session_state.page = "patients"

if "program" not in st.session_state:
    st.session_state.program = []
    
rng = default_rng()

st.title("Patients")

if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = None

# -----------------------
# Generate Data
# -----------------------
n = 20

ages = rng.integers(35, 80, n)

statuses = rng.choice(
    ["Active", "Needs Review", "Inactive"],
    size=n,
    p=[0.6, 0.3, 0.1]
)

last_activity = rng.choice(
    ["Today", "1 day ago", "3 days ago", "5 days ago", "10 days ago"],
    size=n
)

compliance = rng.integers(30, 100, n)

notes_options = [
    "Reported difficulty, decrease in activity",
    "Fatigue reported",
    "Improving steadily",
    "",
    "Balance issues noted"
]

notes = rng.choice(notes_options, size=n)

data = {
    "Patient": [f"Patient {i+1}, {ages[i]}" for i in range(n)],
    "Status": statuses,
    "Last Activity": last_activity,
    "Compliance": compliance,
    "Notes": notes
}

df = pd.DataFrame(data)

# -----------------------
# Helper: Status Colors
# -----------------------
def render_status(status):
    if status == "Active":
        color = "#b7e4c7"
    elif status == "Needs Review":
        color = "#ffe066"
    else:
        color = "#ff6b6b"

    st.markdown(
        f"""
        <div style="
            background-color: {color};
            padding: 5px 10px;
            border-radius: 10px;
            text-align: center;
            font-size: 12px;
            width: fit-content;">
            {status}
        </div>
        """,
        unsafe_allow_html=True
    )

# -----------------------
# MAIN LOGIC
# -----------------------

# -------- PATIENT LIST --------
if st.session_state.page == "patients":

    if st.session_state.selected_patient is None:

        st.subheader("Patient List")

        col1, col2, col3, col4, col5, col6 = st.columns([2,1,1,2,2,1])
        col1.write("**Patient**")
        col2.write("**Status**")
        col3.write("**Last Activity**")
        col4.write("**Compliance**")
        col5.write("**Notes**")

        st.divider()

        for i, row in df.iterrows():
            col1, col2, col3, col4, col5, col6 = st.columns([2,1,1,2,2,1])

            col1.write(row["Patient"])

            with col2:
                render_status(row["Status"])

            col3.write(row["Last Activity"])

            with col4:
                st.progress(row["Compliance"] / 100)
                st.caption(f"{row['Compliance']}%")

            col5.write(row["Notes"])

            if col6.button("View", key=f"btn_{i}"):
                st.session_state.selected_patient = row["Patient"]
                st.session_state.page = "patients"
    # -------- PATIENT PROFILE --------
    else:

        patient = st.session_state.selected_patient

        # -----------------------
        # HEADER
        # -----------------------
        col1, col2 = st.columns([1, 5])

        with col1:
            st.image("person.jpg", width="content")

        with col2:
            st.subheader(patient)
            st.caption("Left-side weakness")
            st.caption("Started HomeStretch: Jan 2026")

            # Tags
            st.markdown("""
            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;margin-right:5px;'>Stroke</span>
            <span style='background:#ffe066;padding:5px 10px;border-radius:10px;margin-right:5px;'>High Fall Risk</span>
            <span style='background:#d0e7ff;padding:5px 10px;border-radius:10px;'>Uses Cane</span>
            """, unsafe_allow_html=True)

        # Summary bar
        st.markdown("""
        <div style='background:#e9f2fb;padding:10px;border-radius:10px;margin-top:10px;'>
            Home Activity: Stable &nbsp;&nbsp; • &nbsp;&nbsp; Adherence: Moderate &nbsp;&nbsp; • &nbsp;&nbsp; Last Active: Today
        </div>
        """, unsafe_allow_html=True)

        st.divider()

        # -----------------------
        # TABS
        # -----------------------
        tab1, tab2, tab3 = st.tabs(["Information", "Session", "Latest Session"])
        # =======================
        # INFORMATION TAB
        # =======================
        with tab1:

            colA, colB = st.columns(2)

            # ---- Clinical Overview ----
            with colA:
                st.markdown("### Clinical Overview")

                st.markdown("""
                **Stroke Type**  
                Ischemic Stroke  

                **Assistive Devices**  
                Cane, Walker, AFO  

                **Date of Stroke**  
                Aug 20, 2025  

                **Living Situation**  
                With caregiver  
                Stairs at home  
                """)

            # ---- Current Program ----
            with colB:
                st.markdown("### Current Program")

                st.markdown("""
                **Frequency**  
                3 sessions / week  

                **Session Duration**  
                ~28 min  

                **Exercises**  
                6  

                **Last Update**  
                Jan 18, 2026  
                """)

                if st.button("Program Builder"):
                    st.session_state.page = "builder"
            # ---- Functional Baseline ----
            colC, colD = st.columns(2)

            with colC:
                st.markdown("### Functional Baseline")

                st.markdown("""
                **Gait**  
                Independent (Supervision outdoors)  

                **Upper Limb**  
                Limited (fine motor control)  
                """)

            with colD:
                st.markdown("### ")

                st.markdown("""
                **Sit to Stand**  
                8 reps, Unassisted  

                **Balance Confidence**  
                Moderate  
                """)

            # ---- Notes ----
            st.markdown("### Notes")

            st.info("""
            **Last entry – Feb 7**  
            Improved weight shifting.  
            Still fatigues quickly.
            """)

            colN1, colN2 = st.columns(2)
            colN1.button("View All Notes")
            colN2.button("Add Note")

        # =======================
        # SESSION TAB
        # =======================
        with tab2:

            col1, col2 = st.columns(2)

            # ---- LEFT SIDE ----
            with col1:
                st.markdown("### Engagement Insights")
                st.markdown("""
                • Tends to skip weekends  
                • Completes better in mornings  
                • Increased difficulty this week  
                """)

                st.markdown("### Session Overview")

                st.metric("Adherence", "82%")
                st.metric("Sessions This Week", "3")
                st.metric("Avg Duration", "28 min")

            # ---- RIGHT SIDE ----
            with col2:
                st.markdown("### Timeline")

                for i in range(10):  # or your real session data
                    date = f"Feb {25 - i*2}, 2026"

                    if st.button(f"{date} | Completed in 28 min", key=f"session_{i}"):
                        st.session_state.selected_session = date
                        st.session_state.page = "session_detail"

        st.divider()

        # Back button
        if st.button("⬅ Back to Patients"):
            st.session_state.selected_patient = None

# -------- PROGRAM BUILDER --------
elif st.session_state.page == "builder":

    st.title("Program Builder")

    col1, col2, col3 = st.columns([1,2,1])

    # LEFT: Exercise Library
    with col1:
        st.subheader("Exercise Library")

        exercises = [
            "Shoulder Rolls",
            "Sit-to-Stand",
            "Heel Raises",
            "Weight Shifts"
        ]

        for ex in exercises:
            if st.button(f"➕ {ex}"):
                st.session_state.program.append({
                    "name": ex,
                    "sets": 3,
                    "reps": "8-10"
                })

    # MIDDLE: Program
    with col2:
        st.subheader("My Exercise Plan")

        for i, ex in enumerate(st.session_state.program):

            st.write(f"### {ex['name']}")

            c1, c2, c3 = st.columns(3)

            ex["sets"] = c1.number_input("Sets", 1, 10, ex["sets"], key=f"s_{i}")
            ex["reps"] = c2.text_input("Reps", ex["reps"], key=f"r_{i}")

            if c3.button("❌", key=f"del_{i}"):
                st.session_state.program.pop(i)
                st.rerun()

            st.divider()

    # RIGHT: Schedule
    with col3:
        st.subheader("Schedule")

        for day in ["Mon", "Tue", "Wed", "Thu", "Fri"]:
            st.checkbox(day)

        st.text_area("Notes")

    st.divider()

    if st.button("⬅ Back to Patient Profile"):
        st.session_state.page = "patients"
# -------- SESSION DETAIL PAGE --------
elif st.session_state.page == "session_detail":

    import numpy as np

    session = st.session_state.selected_session

    st.title(session)
    if st.button("⬅ Back to Patient Profile"):
        st.session_state.page = "patients"

    # -----------------------
    # FAKE DATA
    # -----------------------
    t = np.linspace(0, 60, 200)
    imu_signal = np.sin(t / 3) + np.random.normal(0, 0.1, 200)
    reps_signal = np.abs(np.sin(t / 5)) * 10
    balance = np.random.normal(0.6, 0.1, 200)

    symmetry_left = np.random.uniform(0.4, 0.7, 50)
    symmetry_right = np.random.uniform(0.3, 0.6, 50)

    rom_values = np.random.uniform(30, 90, 10)

    # -----------------------
    # TOP SUMMARY
    # -----------------------
    st.markdown("### Session Summary")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Duration", "28 min")
    m2.metric("Reps", "68")
    m3.metric("Stability", "62%")
    m4.metric("Fatigue", "3.8")

    st.divider()

    col1, col2 = st.columns(2)

    # -----------------------
    # LEFT COLUMN
    # -----------------------
    with col1:

        st.subheader("Patient Video")
        st.empty()

        st.markdown("### Core Metrics")

        st.progress(0.62)
        st.caption("Alignment: 62%")

        st.progress(0.62)
        st.caption("Stability: 62%")

        st.progress(0.42)
        st.caption("Compensation Ratio: 0.42")

        st.progress(0.62)
        st.caption("Movement Speed: 62%")

        st.markdown("### Movement Signal")
        st.line_chart(imu_signal)

        st.markdown("### Repetition Pattern")
        st.area_chart(reps_signal)

    # -----------------------
    # RIGHT COLUMN
    # -----------------------
    with col2:

        st.markdown("### Balance Over Time")
        st.line_chart(balance)

        st.markdown("### Left vs Right Symmetry")
        sym_df = {
            "Left": symmetry_left,
            "Right": symmetry_right
        }
        st.bar_chart(sym_df)

        st.markdown("### Range of Motion")
        st.bar_chart(rom_values)

        st.divider()

        # -----------------------
        # SPLIT CONTENT ACROSS BOTH COLUMNS
        # -----------------------

        exercises = [
            ("Shoulder Rolls", 10, "2 min"),
            ("Gentle Knee Extensions", 18, "4 min"),
            ("Sit to Stand", 0, "0 min"),
            ("Heel Raises", 20, "3 min"),
            ("Seated Arm Raises", 20, "3 min"),
            ("Weight Shifts", 15, "2 min"),
        ]

        left_ex = exercises[:3]
        right_ex = exercises[3:]

        # LEFT COLUMN (add exercises)
        with col1:

            st.markdown("### Exercises")

            for name, reps, time in left_ex:
                st.markdown(f"""
                **{name}**  
                Reps: {reps}  
                Time: {time}
                """)
                st.divider()
            
            st.markdown("### Post Exercise Survey")

            c1, c2 = st.columns(2)

            with c1:
                st.markdown("**Symptoms**")
                st.success("Getting Better")

                st.markdown("**Pain**")
                st.metric("", "7")

            with c2:
                st.markdown("**Notes**")
                st.caption("Felt tired today")               

        # RIGHT COLUMN (rest of exercises + survey)
        with col2:

            st.markdown("### Exercises")

            for name, reps, time in right_ex:
                st.markdown(f"""
                **{name}**  
                Reps: {reps}  
                Time: {time}
                """)
                st.divider()

            st.markdown("### Skipped")
            st.warning("Sit to Stand")
        # =======================
        # LATEST SESSION TAB
        # =======================
        with tab3:

            st.markdown("### Latest Session Overview")

            m1, m2, m3 = st.columns(3)
            m1.metric("Duration", "28 min")
            m2.metric("Reps", "68")
            m3.metric("Stability", "62%")

            st.markdown("### Movement Signal")
            st.line_chart(np.random.randn(100))

            st.markdown("### Key Metrics")

            st.progress(0.62)
            st.caption("Alignment: 62%")

            st.progress(0.58)
            st.caption("Balance: 58%")

            st.progress(0.45)
            st.caption("Compensation: 0.45")

            st.info("Latest session shows moderate fatigue but stable movement patterns.")
                    