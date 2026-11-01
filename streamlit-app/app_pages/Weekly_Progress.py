
import streamlit as st
import pandas as pd
import altair as alt

st.set_page_config(page_title="Weekly Progress", layout="wide")

# =====================================================
# HOMESTRETCH DESIGN
# =====================================================

st.markdown("""
<style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1250px;
    }

    .hs-header {
        background: #C4DCEF;
        border-radius: 16px;
        padding: 24px 30px;
        margin-bottom: 24px;
    }

    .hs-header h1 {
        color: #285F91;
        font-size: 32px;
        font-weight: 600;
        margin: 0;
    }

    .hs-header p {
        color: #527D9F;
        font-size: 14px;
        margin: 6px 0 0;
    }

    .metric-card {
        background: #E8F2FA;
        border-radius: 14px;
        padding: 20px 24px;
        min-height: 125px;
    }

    .metric-label {
        color: #567A98;
        font-size: 14px;
        margin-bottom: 10px;
    }

    .metric-value {
        color: #254E75;
        font-size: 32px;
        font-weight: 650;
        line-height: 1.2;
    }

    .metric-change {
        color: #43876C;
        font-size: 12px;
        margin-top: 7px;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        border-color: #BBD5E9;
        border-radius: 14px;
    }

    .section-title {
        font-size: 19px;
        font-weight: 600;
        color: #285F91;
        margin-bottom: 2px;
    }

    .section-caption {
        color: #73899C;
        font-size: 13px;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)


# =====================================================
# SAMPLE DATA - KEEPING YOUR ORIGINAL VALUES
# =====================================================

days = ["Sun", "Mon", "Tues", "Wed", "Thurs", "Fri", "Sat"]

completion_percent = [23, 78, 62, 56, 66, 42, 62]
session_completion = [0.7, 0.5, 0.6, 0.7, 0.55, 0.4, 0.45]

active_patients = 8
inactive_patients = 4

avg_difficulty = 3.8
difficulty_change = -0.4


# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="hs-header">
    <h1>Weekly Progress</h1>
    <p>Patient activity and rehabilitation trends</p>
</div>
""", unsafe_allow_html=True)


# =====================================================
# SUMMARY METRICS
# =====================================================

col1, col2, col3 = st.columns(3, gap="medium")

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Active Patients</div>
        <div class="metric-value">{active_patients}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Inactive Patients</div>
        <div class="metric-value">{inactive_patients}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Average Reported Difficulty</div>
        <div class="metric-value">{avg_difficulty} / 10</div>
        <div class="metric-change">
            {difficulty_change:+.1f} from last week
        </div>
    </div>
    """, unsafe_allow_html=True)


st.write("")


# =====================================================
# CHART DATA
# =====================================================

df_bar = pd.DataFrame({
    "Day": days,
    "Completion %": completion_percent
})

df_line = pd.DataFrame({
    "Day": days,
    "Completion Rate": [
        round(rate * 100, 1)
        for rate in session_completion
    ]
})


# =====================================================
# DAILY PARTICIPATION CHART
# =====================================================

with st.container(border=True):

    st.markdown("""
    <div class="section-title">
        Daily Exercise Participation
    </div>
    <div class="section-caption">
        Percentage of active patients completing sessions each day
    </div>
    """, unsafe_allow_html=True)

    bar_chart = (
        alt.Chart(df_bar)
        .mark_bar(
            color="#77ADD5",
            cornerRadiusTopLeft=5,
            cornerRadiusTopRight=5
        )
        .encode(
            x=alt.X(
                "Day:N",
                sort=days,
                axis=alt.Axis(
                    title=None,
                    labelAngle=0
                )
            ),
            y=alt.Y(
                "Completion %:Q",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(
                    title="Completion (%)"
                )
            ),
            tooltip=[
                alt.Tooltip("Day:N"),
                alt.Tooltip(
                    "Completion %:Q",
                    format=".0f"
                )
            ]
        )
        .properties(height=270)
        .configure_view(stroke=None)
    )

    st.altair_chart(
        bar_chart,
        use_container_width=True
    )


# =====================================================
# SESSION COMPLETION RATE CHART
# =====================================================

with st.container(border=True):

    st.markdown("""
    <div class="section-title">
        Average Session Completion Rate
    </div>
    <div class="section-caption">
        Percentage of prescribed session activity completed
    </div>
    """, unsafe_allow_html=True)

    line_chart = (
        alt.Chart(df_line)
        .mark_line(
            color="#4388BD",
            strokeWidth=3,
            point=alt.OverlayMarkDef(
                filled=True,
                size=85,
                color="#4388BD"
            )
        )
        .encode(
            x=alt.X(
                "Day:N",
                sort=days,
                axis=alt.Axis(
                    title=None,
                    labelAngle=0
                )
            ),
            y=alt.Y(
                "Completion Rate:Q",
                scale=alt.Scale(domain=[0, 100]),
                axis=alt.Axis(
                    title="Completion (%)"
                )
            ),
            tooltip=[
                alt.Tooltip("Day:N"),
                alt.Tooltip(
                    "Completion Rate:Q",
                    format=".1f",
                    title="Completion (%)"
                )
            ]
        )
        .properties(height=260)
        .configure_view(stroke=None)
    )

    st.altair_chart(
        line_chart,
        use_container_width=True
    )

st.caption(
    "Prototype dashboard — values are currently sample data."
)
