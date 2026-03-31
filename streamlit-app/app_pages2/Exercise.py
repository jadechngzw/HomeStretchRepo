import streamlit as st

# -----------------------
# STATE
# -----------------------
if "current_view" not in st.session_state:
    st.session_state.current_view = "list"

if "selected_exercise" not in st.session_state:
    st.session_state.selected_exercise = None

if "completed_exercises" not in st.session_state:
    st.session_state.completed_exercises = []

# -----------------------
# DATA
# -----------------------
exercises = [
    {"name": "Shoulder Rolls", "type": "(warm up)", "details": "Both directions x10", "time": "~ 1 min"},
    {"name": "Gentle Knee Extensions", "type": "(warm up)", "details": "2 sets | 10 reps", "time": "~ 3 min"},
    {"name": "Sit to Stand", "type": "", "details": "2 sets | 10 reps", "time": "~ 3 min"},
    {"name": "Heel Raises", "type": "", "details": "2 sets | 10 reps", "time": "~ 3 min"},
    {"name": "Bicep Curls", "type": "", "details": "2 sets | 10 reps", "time": "~4 min"},
]

# ===============================
# 📋 EXERCISE LIST PAGE
# ===============================
if st.session_state.current_view == "list":

    st.title("Exercise")
    st.subheader("Weekly Overview")

    for i, ex in enumerate(exercises):

        if st.button(f"{ex['name']}", key=f"ex_{i}"):

            st.session_state.selected_exercise = ex
            st.session_state.current_view = "detail"

        st.markdown(f"""
        <div style="
            background:#dbe5f1;
            padding:18px;
            border-radius:18px;
            margin-bottom:14px;
        ">
            <b>{ex['name']}</b> <i>{ex['type']}</i><br><br>
            {ex['details']}<br>
            {ex['time']}
        </div>
        """, unsafe_allow_html=True)

    # SHOW SURVEY BUTTON IF DONE
    if len(st.session_state.completed_exercises) == len(exercises):
        st.divider()
        if st.button("Go to Post Exercise Survey"):
            st.session_state.current_view = "survey"

elif st.session_state.current_view == "detail":

    ex = st.session_state.selected_exercise

    st.title(ex["name"])

    st.caption("Follow the video and complete your reps")

    # -----------------------
    # MAIN VIDEO (clean, no clutter)
    # -----------------------
    st.markdown("""
    <div style="
        background:#e9f2fb;
        height:240px;
        border-radius:20px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:18px;
        margin-bottom:20px;
    ">
        Stickman Demo Video
    </div>
    """, unsafe_allow_html=True)

    # -----------------------
    # CONTROLS (centered row)
    # -----------------------
    col1, col2, col3 = st.columns([2,1,2])

    with col1:
        st.markdown("<div style='text-align:right'>⏮</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("<div style='text-align:center;font-size:24px;'>▶</div>", unsafe_allow_html=True)

    with col3:
        st.markdown("<div style='text-align:left'>⏭</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)

    # -----------------------
    # SECOND VIDEO (optional)
    # -----------------------
    st.markdown("""
    <div style="
        background:#e9f2fb;
        height:180px;
        border-radius:20px;
        display:flex;
        align-items:center;
        justify-content:center;
        margin-bottom:25px;
    ">
        Patient Video
    </div>
    """, unsafe_allow_html=True)

    # -----------------------
    # REP COUNTER (big + clean)
    # -----------------------
    if "rep_count" not in st.session_state:
        st.session_state.rep_count = 0

    st.markdown(f"""
    <div style="
        background:#dbe5f1;
        height:120px;
        border-radius:20px;
        display:flex;
        align-items:center;
        justify-content:center;
        font-size:60px;
        font-weight:500;
        margin-bottom:25px;
    ">
        {st.session_state.rep_count}
    </div>
    """, unsafe_allow_html=True)

    # -----------------------
    # ACTION BUTTONS
    # -----------------------
    c1, c2 = st.columns([1,1])

    if c1.button("+ Rep", use_container_width=True):
        st.session_state.rep_count += 1

    if c2.button("Complete Exercise", use_container_width=True):

        if ex["name"] not in st.session_state.completed_exercises:
            st.session_state.completed_exercises.append(ex["name"])

        st.session_state.rep_count = 0
        st.session_state.current_view = "list"

    st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)

    if st.button("⬅ Back"):
        st.session_state.current_view = "list"
    
elif st.session_state.current_view == "survey":

    st.title("Post-Exercise Survey")

    # -----------------------
    # SYMPTOMS
    # -----------------------
    st.markdown("### How are your symptoms changing?")

    st.selectbox(
        "",
        ["Getting Better", "About the Same", "Worse"]
    )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # -----------------------
    # BODY MAP
    # -----------------------
    st.markdown("### Mark areas where you feel pain")

    st.image("body.png", use_container_width=True)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # -----------------------
    # PAIN SLIDER
    # -----------------------
    st.markdown("### Overall Pain (0–10)")

    pain = st.slider("", 0, 10, 5)

    # -----------------------
    # NOTES
    # -----------------------
    st.markdown("### Additional Notes")

    notes = st.text_area("", placeholder="Felt tired today...")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # -----------------------
    # SUBMIT
    # -----------------------
    if st.button("Submit"):
        st.success("Survey submitted!")

    if st.button("⬅ Back"):
        st.session_state.current_view = "list"