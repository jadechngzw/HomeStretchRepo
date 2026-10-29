import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

st.title("Alerts")

# -----------------------
# SAMPLE DATA
# -----------------------
alerts = [
    {
        "patient": "Patient 1, 56",
        "condition": "Left-side weakness",
        "tags": ["Stroke", "High Fall Risk"],
        "time": "1 hour ago",
        "alert": "Decreased activity for Patient 1",
        "details": [
            "Last active today",
            "2 sessions in the past month reported"
        ]
    },
    {
        "patient": "Patient 3, 37",
        "condition": "Left-side weakness",
        "tags": ["Stroke", "High Fall Risk"],
        "time": "3 hours ago",
        "alert": "Difficulty reported by Patient 3",
        "details": [
            "Last active today",
            "2 sessions in the past month reported"
        ]
    },
    {
        "patient": "Patient 5, 52",
        "condition": "Left-side weakness",
        "tags": ["Stroke", "High Fall Risk"],
        "time": "2 days ago",
        "alert": "Decreased activity for Patient 5",
        "details": [
            "Last active 5 days ago",
            "2 sessions in the past month reported"
        ]
    },
    {
        "patient": "Patient 2, 60",
        "condition": "Right-side weakness",
        "tags": ["Stroke"],
        "time": "5 hours ago",
        "alert": "Low adherence detected",
        "details": [
            "Missed last 3 sessions",
            "Low completion rate"
        ]
    },
    {
        "patient": "Patient 4, 48",
        "condition": "Left-side weakness",
        "tags": ["Stroke"],
        "time": "1 day ago",
        "alert": "Fatigue increase reported",
        "details": [
            "Higher difficulty this week",
            "Session duration decreasing"
        ]
    }
]

# -----------------------
# ICON LOGIC
# -----------------------
def get_icon(text):
    if "Decreased activity" in text:
        return "📉"
    elif "Difficulty" in text:
        return "💬"
    elif "Fatigue" in text or "Low adherence" in text:
        return "⚠️"
    return "ℹ️"

# -----------------------
# BUILD FULL HTML PAGE
# -----------------------
cards_html = ""

for a in alerts:

    icon = get_icon(a["alert"])

    tags_html = "".join([
        f'<span style="background:#d0e7ff;padding:4px 8px;border-radius:8px;margin-right:6px;font-size:12px;">{t}</span>'
        for t in a["tags"]
    ])

    details_html = "".join([
        f"<li>{d}</li>" for d in a["details"]
    ])

    cards_html += f"""
    <div style="
        background:#e9f2fb;
        padding:16px;
        border-radius:16px;
        margin-bottom:14px;
    ">

        <div style="display:flex; justify-content:space-between;">
            <div>
                <b>{a['patient']}</b> • {a['condition']}<br>
                {tags_html}
            </div>
            <div style="color:#777; font-size:12px;">
                {a['time']}
            </div>
        </div>

        <hr style="margin:10px 0;">

        <div style="font-weight:500; margin-bottom:6px; font-size:16px;">
            {icon} {a['alert']}
        </div>

        <ul style="margin-top:6px;">
            {details_html}
        </ul>

    </div>
    """

# -----------------------
# FINAL RENDER
# -----------------------
components.html(f"""
<div style="max-height:650px; overflow-y:auto; padding-right:10px;">
    {cards_html}
</div>
""", height=700)