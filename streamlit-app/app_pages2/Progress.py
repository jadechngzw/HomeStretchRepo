import streamlit as st
import numpy as np
import pandas as pd

st.title("Progress")

# -----------------------
# HEADER TEXT
# -----------------------
st.markdown("### You're doing great!")

st.markdown("**Movement this week:**")
st.write("5 sessions completed")
st.write("92 minutes of movement")

# -----------------------
# GRAPH (FAKE DATA)
# -----------------------
import time
import numpy as np
import pandas as pd

st.markdown("")

# Create placeholder
chart_placeholder = st.empty()

# Fake data
x = np.linspace(0, 10, 100)
y_full = np.exp(-((x - 5)**2) / 4)

# Animate
for i in range(10, len(y_full), 5):
    df = pd.DataFrame({
        "Movement": y_full[:i]
    })

    chart_placeholder.line_chart(df)

    time.sleep(0.05)  # controls speed
# -----------------------
# SUBTEXT
# -----------------------
st.caption("Any movement counts")

# -----------------------
# WHAT YOU WORKED ON
# -----------------------
st.markdown("### What you worked on:")

def pill(text):
    st.markdown(
        f"""
        <div style="
            background-color:#dbe5f1;
            padding:10px;
            border-radius:20px;
            margin-bottom:8px;
            width:100%;
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )

pill("Balance")
pill("Walking")
pill("Stretching")
pill("Arm & Hand Use")

# -----------------------
# ACCOMPLISHMENTS
# -----------------------
st.markdown("### Accomplishments:")

st.markdown("""
<div style="border-left:5px solid #dbe5f1; padding-left:10px;">
    Longest Walk: 8 min<br><br>
    Most sit to stands: 12<br><br>
    🎉 New exercise completed!
</div>
""", unsafe_allow_html=True)