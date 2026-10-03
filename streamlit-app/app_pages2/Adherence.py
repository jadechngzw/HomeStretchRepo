import streamlit as st
from datetime import datetime, timedelta

st.title("Adherence")

# -----------------------------------------------------------
# Config
# -----------------------------------------------------------
SEVERAL_MISSED = 3  # "several scheduled sessions" threshold -- tune with the care team
EXERCISE_PAGE = "app_pages2/Exercise.py"
MESSAGES_PAGE = "app_pages2/Messages.py"

LIGHTS = {
    "green": ("#b7e4c7", "Green Light"),
    "yellow": ("#ffe066", "Yellow Light"),
    "red": ("#ff6b6b", "Red Light"),
    None: ("#e9f2fb", ""),  # neutral (no light in the spec)
}


# -----------------------------------------------------------
# Session state
# -----------------------------------------------------------
def fresh_state():
    return {
        "adh_log": [],
        "adh_snoozed_until": None,
        "adh_self_reported": False,
        "adh_show_details": False,
        "adh_skipped": False,
        "adh_finished": False,
        "adh_device_checked": False,
        "adh_show_device_check": False,
        "adh_show_checkin": False,
        "adh_checkin": None,  # None / "good" / "tired" / "unwell"
        "adh_barrier": None,  # None / "too_difficult" / "need_help" / "already_exercising" / "dont_want"
    }


for _k, _v in fresh_state().items():
    st.session_state.setdefault(_k, _v)


def reset_actions():
    for k, v in fresh_state().items():
        st.session_state[k] = v


def log(event):
    st.session_state.adh_log.insert(0, f"{datetime.now():%I:%M %p} — {event}")


# -----------------------------------------------------------
# Prototype controls (replace with real data later)
# -----------------------------------------------------------
with st.expander("Prototype controls — simulate patient data"):
    c1, c2 = st.columns(2)
    plan = c1.selectbox(
        "Today's plan",
        ["Scheduled today", "Rest day", "Clinician-paused plan"],
        key="ctl_plan",
    )
    planned = c1.number_input("Sets planned today", 1, 10, 2, key="ctl_planned")
    done = c1.number_input("Sets completed today", 0, 10, 0, key="ctl_done")
    allows = c1.checkbox("Plan allows remaining sets today", True, key="ctl_allows")

    missed = c2.number_input("Scheduled sessions missed in a row", 0, 10, 0, key="ctl_missed")
    flag = c2.checkbox("Unresolved symptom / clinician-review flag", key="ctl_flag")
    sensor = c2.checkbox("Previous session had unreliable sensor data", key="ctl_sensor")
    difficult = c2.checkbox(
        "Previous session was difficult (elevated peak HR, inconsistent reps, "
        "or incomplete without a safety flag)",
        key="ctl_difficult",
    )
    st.button("Reset today's actions", on_click=reset_actions)

facts = {
    "plan": plan,
    "planned": planned,
    "done": done,
    "allows": allows,
    "missed": missed,
    "flag": flag,
    "sensor": sensor,
    "difficult": difficult,
}


# -----------------------------------------------------------
# Rule engine: facts + patient actions -> which case to show
# Priority order matters: safety first, then completion state,
# then device / barriers / strain, then the default reminder.
# -----------------------------------------------------------
def build_case(f):
    ss = st.session_state

    # Rest day or clinician-paused plan -> no reminder
    if f["plan"] != "Scheduled today":
        note = " Your plan is currently paused by your care team." if f["plan"] == "Clinician-paused plan" else ""
        return dict(
            id="rest",
            light=None,
            situation="Rest day or clinician-paused plan",
            response="Do not send an exercise reminder",
            message="No exercises are scheduled today." + note,
            actions=[("View plan", "view_plan")],
        )

    # Unresolved symptom / clinician-review flag -> red
    if f["flag"]:
        return dict(
            id="flag",
            light="red",
            situation="Scheduled exercise, no recorded completion + unresolved symptom or clinician-review flag",
            response="Replace exercise reminder with the prescribed follow-up instruction",
            message="Your last session needs a follow-up. Please follow your care team's instructions before restarting.",
            actions=[("Message my care team", "messages")],
        )

    # Patient reported feeling unwell during the supportive check-in -> red
    if ss.adh_checkin == "unwell":
        return dict(
            id="checkin_unwell",
            light="red",
            situation="Check-in answer: not well / new symptoms",
            response="Hold exercise reminder and direct patient to care team",
            message="Thanks for telling us. Please hold off on exercising and contact your care team about how you're feeling.",
            actions=[("Message my care team", "messages")],
        )

    # Patient chose "Skip today"
    if ss.adh_skipped:
        return dict(
            id="skipped",
            light=None,
            situation="Patient skipped today",
            response="Suppress today's reminders",
            message="Okay, we'll skip today. Your care team can see that you skipped.",
            actions=[("Undo", "undo_skip")],
        )

    # Patient selected "Already done"
    if ss.adh_self_reported:
        return dict(
            id="self_reported",
            light="green",
            situation='Patient selects "Already done"',
            response="Save completion as self-reported and suppress that reminder",
            message="Marked as done.",
            actions=[("Undo", "undo_done"), ("Add details", "add_details")],
        )

    # Patient chose "Finish for today" after partial completion
    if ss.adh_finished:
        return dict(
            id="finished",
            light="green",
            situation="Patient finished for today after partial completion",
            response="Suppress remaining reminders for today",
            message=f"You're finished for today. You completed {f['done']} of {f['planned']} planned sets. Nice work!",
            actions=[],
        )

    # All planned sets completed -> nothing to remind
    if f["done"] >= f["planned"]:
        return dict(
            id="complete",
            light="green",
            situation="Today's planned exercise is fully completed",
            response="No reminder needed",
            message=f"You've completed all {f['planned']} planned sets today. Great work!",
            actions=[],
        )

    # Today's exercise partially completed -> green
    if f["done"] > 0:
        actions = []
        if f["allows"]:
            actions.append(("View remaining", "view_remaining"))
        actions += [("Later", "remind_later"), ("Finish for today", "finish_today")]
        return dict(
            id="partial",
            light="green",
            situation="Today's exercise is partially completed",
            response="Show recorded progress; offer remaining prescribed activity only if the plan allows and no unresolved flag exists",
            message=f"You've completed {f['done']} of {f['planned']} planned sets today.",
            actions=actions,
        )

    # Previous session had unreliable sensor data -> yellow
    if f["sensor"] and not ss.adh_device_checked:
        return dict(
            id="sensor",
            light="yellow",
            situation="Previous session had unreliable sensor data",
            response="Offer a device setup check",
            message="We couldn't fully record your last session. Let's check your watch before starting.",
            actions=[("Check watch", "check_watch"), ("Already done", "device_done"), ("Later", "remind_later")],
        )

    # Several scheduled sessions with no completion -> ask about barriers
    if f["missed"] >= SEVERAL_MISSED:
        barrier_replies = {
            "too_difficult": "Thanks for letting us know. We'll share this with your care team so they can look at adjusting your plan.",
            "need_help": "Thanks for asking. We'll let your care team know you need help so they can reach out.",
            "already_exercising": "Good to hear! You can log what you've been doing so your care team has the full picture.",
            "dont_want": "That's okay, and thanks for being honest. We'll let your care team know so they can check in with you.",
        }
        if ss.adh_barrier:
            actions = [("Change answer", "clear_barrier")]
            if ss.adh_barrier == "already_exercising":
                actions.insert(0, ("Log my activity", "add_details"))
            return dict(
                id="barrier_reply",
                light=None,
                situation="Barrier reported after several missed sessions",
                response="Acknowledge, notify care team, offer support",
                message=barrier_replies[ss.adh_barrier],
                actions=actions,
            )
        return dict(
            id="barriers",
            light=None,
            situation="Several scheduled sessions have no recorded completion",
            response="Ask about barriers and offer support",
            message="We haven't recorded a session recently. Is something making exercise difficult?",
            actions=[
                ("Too difficult", "barrier_too_difficult"),
                ("Need help", "barrier_need_help"),
                ("Already exercising", "barrier_already_exercising"),
                ("I don't want to exercise", "barrier_dont_want"),
            ],
        )

    # Previous session was difficult -> supportive check-in (yellow)
    if f["difficult"] and ss.adh_checkin is None:
        return dict(
            id="strain",
            light="yellow",
            situation="Scheduled exercise, no recorded completion + previous exercise was difficult / peak HR elevated / reps inconsistent / incomplete without a safety flag",
            response="Offer a supportive check-in before starting",
            message="Your previous session showed some strain. How are you feeling today?",
            actions=[("Check in", "check_in"), ("Remind me later", "remind_later"), ("Skip today", "skip_today")],
        )

    # Check-in answered "a little tired or sore" -> gentle yellow reminder
    if ss.adh_checkin == "tired":
        return dict(
            id="checkin_tired",
            light="yellow",
            situation="Check-in answer: a little tired or sore",
            response="Send a gentle reminder",
            message="Thanks for checking in. Take it at your own pace today, and stop if anything feels off.",
            actions=[("Start", "start"), ("Remind me later", "remind_later"), ("Skip today", "skip_today")],
        )

    # Default: scheduled, no completion, previous session was fine -> green reminder
    intro = "Thanks for checking in. Glad you're feeling good. " if ss.adh_checkin == "good" else ""
    return dict(
        id="reminder",
        light="green",
        situation="Scheduled exercise, no recorded completion + previous exercise was good",
        response="Send a reminder",
        message=intro + "You have exercises scheduled today. Ready to get started?",
        actions=[("Start", "start"), ("Remind me later", "remind_later"), ("Mark it done", "mark_done")],
    )


# -----------------------------------------------------------
# Action handling
# -----------------------------------------------------------
def handle_action(key):
    ss = st.session_state

    if key in ("start", "view_remaining", "view_plan"):
        log(f"Opened exercises ({key})")
        st.switch_page(EXERCISE_PAGE)

    if key == "messages":
        st.switch_page(MESSAGES_PAGE)

    elif key == "remind_later":
        ss.adh_snoozed_until = datetime.now() + timedelta(hours=1)
        log("Snoozed reminder for 1 hour")
    elif key == "mark_done":
        ss.adh_self_reported = True
        log("Marked as done (self-reported)")
    elif key == "undo_done":
        ss.adh_self_reported = False
        ss.adh_show_details = False
        log("Undid self-reported completion")
    elif key == "add_details":
        ss.adh_show_details = True
    elif key == "check_in":
        ss.adh_show_checkin = True
    elif key == "skip_today":
        ss.adh_skipped = True
        log("Skipped today")
    elif key == "undo_skip":
        ss.adh_skipped = False
        log("Undid skip")
    elif key == "check_watch":
        ss.adh_show_device_check = True
    elif key == "device_done":
        ss.adh_device_checked = True
        ss.adh_show_device_check = False
        log("Confirmed watch is ready")
    elif key == "finish_today":
        ss.adh_finished = True
        log("Finished for today after partial completion")
    elif key.startswith("barrier_"):
        ss.adh_barrier = key.replace("barrier_", "", 1)
        log(f"Reported barrier: {ss.adh_barrier}")
    elif key == "clear_barrier":
        ss.adh_barrier = None

    st.rerun()


# -----------------------------------------------------------
# Today summary
# -----------------------------------------------------------
scheduled = facts["plan"] == "Scheduled today"

m1, m2, m3 = st.columns(3)
m1.metric("Today's plan", facts["plan"])
m2.metric("Sets today", f"{facts['done']} / {facts['planned']}" if scheduled else "—")
m3.metric("Missed in a row", facts["missed"])

if scheduled:
    st.progress(min(facts["done"] / facts["planned"], 1.0))

st.divider()

# -----------------------------------------------------------
# Main card
# -----------------------------------------------------------
case = build_case(facts)
bg, light_label = LIGHTS[case["light"]]

pill = ""
if light_label:
    pill = (
        "<span style='font-size:12px;font-weight:600;background:rgba(255,255,255,0.65);"
        f"padding:3px 10px;border-radius:10px;'>{light_label}</span>"
    )

top_margin = "10px" if pill else "0"
card_html = (
    f'<div style="background-color:{bg};color:#1f2937;padding:18px 20px;border-radius:12px;">'
    f"{pill}"
    f'<div style="font-size:18px;font-weight:600;margin-top:{top_margin};">{case["message"]}</div>'
    "</div>"
)
st.markdown(card_html, unsafe_allow_html=True)

snoozed = st.session_state.adh_snoozed_until
if snoozed and datetime.now() < snoozed:
    st.info(f"Reminder snoozed. We'll remind you again around {snoozed:%I:%M %p}.")

st.write("")

# Action buttons (rows of up to 3, or 2 when there are 4+)
actions = case["actions"]
if actions:
    per_row = 3 if len(actions) <= 3 else 2
    for start in range(0, len(actions), per_row):
        row = actions[start:start + per_row]
        cols = st.columns(per_row)
        for col, (label, akey) in zip(cols, row):
            if col.button(label, key=f"act_{case['id']}_{akey}"):
                handle_action(akey)

# -----------------------------------------------------------
# Follow-up panels
# -----------------------------------------------------------
ss = st.session_state

# Supportive check-in
if ss.adh_show_checkin and ss.adh_checkin is None:
    with st.container(border=True):
        st.markdown("**How are you feeling today?**")
        feeling = st.radio(
            "Feeling",
            ["Feeling good", "A little tired or sore", "Not well / new symptoms"],
            key="adh_checkin_choice",
            label_visibility="collapsed",
        )
        if st.button("Submit check-in"):
            ss.adh_checkin = {
                "Feeling good": "good",
                "A little tired or sore": "tired",
                "Not well / new symptoms": "unwell",
            }[feeling]
            ss.adh_show_checkin = False
            log(f"Check-in submitted: {ss.adh_checkin}")
            st.rerun()

# Device setup check
if ss.adh_show_device_check and not ss.adh_device_checked:
    with st.container(border=True):
        st.markdown("**Quick watch check**")
        st.checkbox("My watch is charged and snug on my wrist", key="dev_1")
        st.checkbox("Bluetooth is on", key="dev_2")
        st.checkbox("I've opened the watch app so it can sync", key="dev_3")
        if st.button("My watch is ready"):
            ss.adh_device_checked = True
            ss.adh_show_device_check = False
            log("Confirmed watch is ready")
            st.rerun()

# Add details for a self-reported session
if ss.adh_show_details:
    with st.container(border=True):
        st.markdown("**Tell us what you did**")
        st.selectbox(
            "Activity",
            ["Exercises from my plan", "Walking", "Other activity"],
            key="detail_type",
        )
        st.slider("About how long (minutes)?", 5, 60, 20, key="detail_minutes")
        st.text_input("Anything else? (optional)", key="detail_notes")
        s1, s2 = st.columns(2)
        if s1.button("Save details"):
            ss.adh_self_reported = True
            ss.adh_show_details = False
            ss.adh_barrier = None
            log(f"Self-reported: {ss.detail_type}, {ss.detail_minutes} min")
            st.rerun()
        if s2.button("Cancel"):
            ss.adh_show_details = False
            st.rerun()

# -----------------------------------------------------------
# Dev views
# -----------------------------------------------------------
#st.divider()

#with st.expander("Rule matched (dev view)"):
    #st.markdown(f"**Situation:** {case['situation']}")
    #st.markdown(f"**System response:** {case['response']}")
    #st.caption(f"case id: `{case['id']}`")

#with st.expander("Activity log (what would sync to the care team)"):
    #if ss.adh_log:
        #for entry in ss.adh_log:
            #st.caption(entry)
    #else:
        #st.caption("No actions yet.")