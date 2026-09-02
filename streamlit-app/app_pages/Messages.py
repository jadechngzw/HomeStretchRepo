import streamlit as st
st.set_page_config(layout="wide")
st.title("Messages")

# -----------------------
# STATE
# -----------------------
if "selected_chat" not in st.session_state:
    st.session_state.selected_chat = None

if "messages" not in st.session_state:
    st.session_state.messages = {}

patients = [f"Patient {i}" for i in range(1, 10)]

# Initialize storage
for p in patients:
    if p not in st.session_state.messages:
        st.session_state.messages[p] = []

# -----------------------
# LAYOUT
# -----------------------
col1, col2 = st.columns([1, 2])

# ======================
# LEFT: PATIENT LIST
# ======================
with col1:

    st.markdown("### Patients")

    st.markdown("""
    <div style="
        max-height: 500px;
        overflow-y: auto;
        padding-right: 5px;
    ">
    """, unsafe_allow_html=True)

    for p in patients:

        if st.button(p, key=f"patient_{p}", use_container_width=True):
            st.session_state.selected_chat = p

    st.markdown("</div>", unsafe_allow_html=True)

# ======================
# RIGHT: CHAT WINDOW
with col2:

    if st.session_state.selected_chat is None:

        st.markdown("""
        <div style="
            height:400px;
            display:flex;
            align-items:center;
            justify-content:center;
            color:#aaa;
        ">
            Click on a patient to message them...
        </div>
        """, unsafe_allow_html=True)

    else:
        patient = st.session_state.selected_chat

        st.subheader(patient)
        st.caption("Secure messaging with patient")
        # -----------------------
        # SCROLLABLE CHAT AREA
        # -----------------------
        st.markdown("""
        <div style="
            max-height:400px;
            overflow-y:auto;
            padding-right:10px;
        ">
        """, unsafe_allow_html=True)

        for msg in st.session_state.messages[patient]:

            if msg["sender"] == "patient":
                st.markdown(f"""
                <div style="
                    background:#f3f6fb;
                    padding:10px;
                    border-radius:10px;
                    margin-bottom:6px;
                    width:70%;
                ">
                    {msg["text"]}
                </div>
                """, unsafe_allow_html=True)

            else:
                st.markdown(f"""
                <div style="
                    background:#dbe5f1;
                    padding:10px;
                    border-radius:10px;
                    margin-bottom:6px;
                    margin-left:auto;
                    width:70%;
                ">
                    {msg["text"]}
                </div>
                """, unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

        # -----------------------
        # FIXED INPUT BAR (BOTTOM FEEL)
        # -----------------------
        input_col, send_col = st.columns([6,1])

        msg_input = input_col.text_input(
            "",
            placeholder="Send Message...",
            key="msg_input"
        )

        if send_col.button("➤"):

            if msg_input.strip() != "":
                st.session_state.messages[patient].append({
                    "sender": "clinician",
                    "text": msg_input
                })

                st.rerun()