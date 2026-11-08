"""HomeStretch clinician app: roster, invitations, messages and bicep-curl progress.

Layout follows the HomeStretch clinician designs (blue banner headers, white cards,
roster rows, profile banner with tabs, two-pane messages). All data comes from
clinician_backend, which only returns records of actively linked patients.
"""
import html
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pandas as pd
import altair as alt
import streamlit as st
import clinician_backend as backend
from clinician_charts import (METRICS, metric_frame, exercise_of, is_bicep_curl, recording_time,
                              session_trend_frame, rep_duration_frame, metric_trend_frame, metric_by_rep_frame)

st.set_page_config(page_title='HomeStretch | Clinician', page_icon='🏠', layout='wide')
st.markdown("""<style>
:root {--hs-navy:#174B78;--hs-blue:#2C6FAD;--hs-line:#B7D0E5;--hs-ink:#253746;--hs-muted:#5F7A90;}
[data-testid="stAppViewContainer"] {background:linear-gradient(180deg,#F5F9FD 0%,#FFFFFF 55%);color:var(--hs-ink);}
.block-container {max-width:1320px;padding-top:3.2rem;}
h1,h2,h3 {color:var(--hs-navy)!important;}
[data-testid="stSidebar"] {background:#DCEBF6;}
.hs-banner {background:#C4DCEF;padding:22px 28px;border-radius:16px;margin-bottom:20px;}
.hs-banner h1 {margin:0;color:#285F91!important;font-size:30px;font-weight:650;padding:0;}
.hs-banner p {margin:6px 0 0;color:#527D9F;font-size:14px;}
.hs-section {font-size:1.12rem;font-weight:720;color:var(--hs-navy);margin:4px 0 10px;letter-spacing:-.01em;}
.hs-chip {display:inline-block;padding:2px 10px;border-radius:999px;font-size:.8rem;font-weight:650;border:1px solid;}
.hs-chip.active {background:#E3F2EA;color:#2F6B53;border-color:#B9DCC8;}
.hs-chip.review {background:#FBEDEE;color:#9B3640;border-color:#EDC3C7;}
.hs-chip.idle {background:#EEF1F4;color:#5B6875;border-color:#D3DAE1;}
.hs-chip.pending {background:#FFF5DF;color:#8A5B00;border-color:#F0D9A6;}
.hs-chip.new {background:#E6F0F8;color:#285F91;border-color:#BBD5E9;}
.hs-marker {display:none;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-white-card),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-white-card) {background:linear-gradient(145deg,#FFFFFF 68%,#F7FBFF 100%);border:1.5px solid var(--hs-line)!important;border-radius:17px!important;padding:16px 20px!important;box-shadow:0 4px 15px rgba(28,77,116,.06);}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-white-card),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-white-card) .hs-section,[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-white-card) .hs-section {border-left:4px solid #317DB8;padding-left:12px;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-row),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-row) {background:#E6F2FB;border:1px solid #C9E0F0!important;border-radius:13px!important;padding:4px 12px!important;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-profile-banner),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-profile-banner) {background:linear-gradient(105deg,#D9EBFA 0%,#E9F4FD 60%,#F7FBFF 100%);border:1.5px solid #B4D2E9!important;border-radius:17px!important;padding:16px 24px!important;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-profile-banner),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-profile-banner) h3 {font-size:1.6rem!important;font-weight:750!important;}
[data-testid="stMetric"] {background:linear-gradient(135deg,#E7F3FE,#F3F9FE);border:1.5px solid #C0DAEE;border-radius:15px;padding:14px 18px;}
[data-testid="stMetricValue"] {color:#1C5E96;font-weight:750;}
[data-testid="stMetricLabel"] {color:#486B88;font-weight:600;}
.stTabs [role="tablist"] {background:#EAF3FB;border:1.5px solid #BBD5EA;border-radius:14px;padding:6px;gap:8px;}
.stTabs [role="tab"] {background:#F9FCFF;border:1.5px solid #BBD5EA;border-radius:11px;color:#1C5485!important;font-weight:700;min-height:48px;padding:6px 18px;}
.stTabs [role="tab"][aria-selected="true"] {background:linear-gradient(110deg,#286DAA,#1A568F)!important;color:#FFFFFF!important;border-color:#1A568F!important;}
.stTabs [role="tab"][aria-selected="true"] p {color:#FFFFFF!important;}
.stTabs [data-baseweb="tab-highlight"],.stTabs [data-baseweb="tab-border"] {display:none;}
.stButton>button,.stFormSubmitButton>button {border-radius:11px;border:1.5px solid #A9CBE4;color:#205E96;font-weight:650;}
.stButton>button[kind="primary"],.stFormSubmitButton>button[kind="primary"],[data-testid="stBaseButton-primary"],[data-testid="stBaseButton-primaryFormSubmit"] {background:#367FBD;color:#FFFFFF!important;border-color:#367FBD;}
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p,button[kind="primary"] p {color:#FFFFFF!important;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {background:#FFFFFF;border-radius:10px;}
[data-testid="stForm"] {background:rgba(255,255,255,.85);border:1.5px solid #C4DCEF;border-radius:17px;padding:20px;}
[data-testid="stChatMessage"] {background:#E6F0F8;border-radius:16px;}
[data-testid="stExpander"] {border:1.5px solid #C2D9EA;border-radius:12px;}
@media(max-width:700px){.hs-banner{padding:16px 18px}.hs-banner h1{font-size:24px}}
</style>""", unsafe_allow_html=True)

# Colors: typical (blue), outside baseline (reserved red, always labelled), unassessed (gray).
CLASS_DOMAIN = ['Typical', 'Outside baseline', 'Unassessed']
CLASS_RANGE = ['#367FBD', '#C24C54', '#9AA6B2']
RECENT_DAYS = 7


def banner(title, subtitle=''):
    st.markdown(f'<div class="hs-banner"><h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>', unsafe_allow_html=True)


def card(marker='hs-white-card'):
    box = st.container(border=True)
    box.markdown(f'<span class="hs-marker {marker}"></span>', unsafe_allow_html=True)
    return box


def section(title):
    st.markdown(f'<div class="hs-section">{html.escape(title)}</div>', unsafe_allow_html=True)


def chip(text, kind):
    return f'<span class="hs-chip {kind}">{html.escape(text)}</span>'


def fmt_time(value, with_time=True):
    if isinstance(value, str):
        try: value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError: return value
    if not isinstance(value, datetime): return '—'
    if value.tzinfo: value = value.astimezone()
    return value.strftime('%b %d, %Y · %I:%M %p' if with_time else '%b %d, %Y')


def now():
    return datetime.now(timezone.utc)


def is_recent(recording, days=RECENT_DAYS):
    when = recording_time(recording)
    if when is None: return False
    if when.tzinfo is None: when = when.replace(tzinfo=timezone.utc)
    return when >= now() - timedelta(days=days)


def patient_status(recordings):
    """Display-only status from available recordings; not a clinical assessment."""
    if not recordings: return 'New', 'new'
    latest = recordings[0]
    if (latest.get('num_atypical') or 0) > 0: return 'Review latest set', 'review'
    if any(is_recent(r) for r in recordings): return 'Active', 'active'
    return f'No sets in {RECENT_DAYS} days', 'idle'


def sign_out():
    st.session_state.clear()


def go(view_name, **state):
    """Switch sidebar view; applied before the radio widget is created on the next run."""
    st.session_state.nav_request = view_name
    st.session_state.update(state)
    st.rerun()


# ---------------------------------------------------------------- sign in
if not st.session_state.get('clinician_token'):
    _, center, _ = st.columns([1, 1.25, 1])
    with center:
        st.markdown('<div class="hs-banner" style="text-align:center"><h1>HomeStretch</h1><p>Clinician portal</p></div>', unsafe_allow_html=True)
        st.subheader('Clinician sign in')
        st.caption('Welcome back. Sign in to view your patients.')
        with st.form('sign_in', clear_on_submit=True):
            email = st.text_input('Email')
            password = st.text_input('Password', type='password')
            submitted = st.form_submit_button('Sign in', type='primary', width='stretch')
    if submitted:
        try:
            st.session_state.clinician_token = backend.sign_in(email, password)
            st.rerun()
        except Exception:
            st.error('Could not sign in. Check your account details, clinician access, and server credentials.')
    st.stop()

token = st.session_state.clinician_token
try:
    uid, profile = backend.clinician(token)
except Exception:
    sign_out()
    st.info('Please sign in again. Your session may have expired or access may have changed.')
    st.stop()

# ---------------------------------------------------------------- sidebar
VIEWS = ['Patients', 'Invite patients', 'Messages']
st.session_state.setdefault('view', 'Patients')
if 'nav_request' in st.session_state: st.session_state.view = st.session_state.pop('nav_request')
with st.sidebar:
    st.markdown(f"### {html.escape(profile.get('display_name', 'Clinician'))}")
    st.caption('HomeStretch clinician')
    view = st.radio('Navigate', VIEWS, key='view', label_visibility='collapsed')
    st.divider()
    st.button('Refresh data', width='stretch')
    with st.expander('Your profile'):
        with st.form('clinician_profile'):
            display_name = st.text_input('Full name', value=profile.get('display_name', ''))
            save_profile = st.form_submit_button('Save name')
        if save_profile:
            try:
                backend.update_clinician_profile(token, display_name)
                st.rerun()
            except ValueError as error:
                st.error(str(error))
            except Exception:
                st.error('Could not save your name. Please try again.')
    st.button('Sign out', on_click=sign_out, width='stretch')


def load_sessions(patient_id):
    cache = st.session_state.setdefault('_sessions_this_run', {})
    if patient_id not in cache:
        cache[patient_id] = backend.sessions(token, patient_id)
    return cache[patient_id]


st.session_state['_sessions_this_run'] = {}


# ---------------------------------------------------------------- charts
def x_labels(rows):
    """Ordered per-set labels so several sets on one day stay separate bars."""
    frame = pd.DataFrame(rows)
    order = sorted({(r['time'], r['session']) for r in rows}, key=lambda x: x[0])
    labels = {}
    for t, sid in order:
        label = (t.astimezone() if t.tzinfo else t).strftime('%b %d %H:%M')
        while label in labels.values(): label += ' ·'
        labels[sid] = label
    frame['set'] = frame['session'].map(labels)
    return frame, [labels[sid] for _, sid in order]


def reps_chart(recordings):
    rows = session_trend_frame(recordings)
    if not rows: return None
    frame, order = x_labels(rows)
    return alt.Chart(frame).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, stroke='#FFFFFF', strokeWidth=1).encode(
        x=alt.X('set:O', sort=order, title=None, axis=alt.Axis(labelAngle=-35, labelLimit=140)),
        y=alt.Y('sum(reps):Q', title='Repetitions', axis=alt.Axis(tickMinStep=1)),
        color=alt.Color('classification:N', scale=alt.Scale(domain=CLASS_DOMAIN, range=CLASS_RANGE), legend=alt.Legend(title=None, orient='top')),
        order=alt.Order('classification:N', sort='descending'),
        tooltip=[alt.Tooltip('set:O', title='Set'), alt.Tooltip('classification:N', title='Reps'), alt.Tooltip('sum(reps):Q', title='Count')],
    ).properties(height=280)


def duration_chart(recordings):
    rows = rep_duration_frame(recordings)
    if not rows: return None
    frame, order = x_labels(rows)
    x = alt.X('set:O', sort=order, title=None, axis=alt.Axis(labelAngle=-35, labelLimit=140))
    tooltip = [alt.Tooltip('set:O', title='Set'), alt.Tooltip('mean:Q', title='Mean (s)', format='.2f'),
               alt.Tooltip('min:Q', title='Fastest (s)', format='.2f'), alt.Tooltip('max:Q', title='Slowest (s)', format='.2f'), alt.Tooltip('reps:Q', title='Timed reps')]
    rng = alt.Chart(frame).mark_rule(color='#9DC2E2', strokeWidth=6, opacity=.6).encode(x=x, y=alt.Y('min:Q', title='Seconds per rep', scale=alt.Scale(zero=False)), y2='max:Q', tooltip=tooltip)
    line = alt.Chart(frame).mark_line(color='#2C6FAD', strokeWidth=2, point=alt.OverlayMarkDef(size=70, filled=True, color='#2C6FAD')).encode(x=x, y='mean:Q', tooltip=tooltip)
    return (rng + line).properties(height=280)


def set_label_map(recordings):
    """{session id: legend label} plus chronological label order, for every set that has per-rep metrics."""
    rows = [dict(r, value=None) for k in METRICS for r in metric_by_rep_frame(recordings, k)]
    if not rows: return {}, []
    frame, order = x_labels(rows)
    return dict(zip(frame['session'], frame['set'])), order


def metric_trend_chart(recordings, key, shown=None):
    """Stored per-rep values, unchanged: x = rep number, one line per set.

    `shown` limits which set labels are plotted; colors stay fixed over all sets."""
    rows = metric_by_rep_frame(recordings, key)
    if not rows: return None
    labels, order = set_label_map(recordings)
    frame = pd.DataFrame(rows)
    frame['set'] = frame['session'].map(labels)
    if shown is not None: frame = frame[frame['set'].isin(shown)]
    if frame.empty: return None
    palette = ['#2C6FAD', '#8EC3F0', '#E0413A', '#F2A8A3', '#45A08A', '#9FD8C6', '#E3A33B', '#F4D27F', '#7A5CC2', '#C3B1EC']
    colors = alt.Scale(domain=order, range=[palette[i % len(palette)] for i in range(len(order))])
    tooltip = [alt.Tooltip('set:N', title='Set'), alt.Tooltip('rep:O', title='Rep'), alt.Tooltip('value:Q', title=METRICS[key], format='.3f')]
    return alt.Chart(frame).mark_line(point=alt.OverlayMarkDef(size=55, filled=True)).encode(
        x=alt.X('rep:O', title='Repetition', axis=alt.Axis(labelAngle=0)),
        y=alt.Y('value:Q', title=METRICS[key], scale=alt.Scale(zero=False)),
        color=alt.Color('set:N', scale=colors, legend=alt.Legend(title='Set', orient='top', values=[o for o in order if shown is None or o in shown])),
        tooltip=tooltip,
    ).properties(height=300)


def set_checkboxes(labels, prefix):
    """'Select all' + one checkbox per set label (all checked by default). Returns the checked labels."""
    keys = {label: f'{prefix}_set_{i}' for i, label in enumerate(labels)}
    all_key = f'{prefix}_all'
    for k in keys.values(): st.session_state.setdefault(k, True)

    def toggle_all():
        for k in keys.values(): st.session_state[k] = st.session_state[all_key]

    def sync_all():
        st.session_state[all_key] = all(st.session_state[k] for k in keys.values())

    st.session_state[all_key] = all(st.session_state[k] for k in keys.values())
    st.checkbox('Select all', key=all_key, on_change=toggle_all)
    per_row = 5
    for start in range(0, len(labels), per_row):
        cols = st.columns(per_row)
        for col, label in zip(cols, labels[start:start + per_row]):
            col.checkbox(label, key=keys[label], on_change=sync_all)
    return [label for label in labels if st.session_state[keys[label]]]


def per_rep_chart(recording, key, title):
    values, band = metric_frame(recording, key)
    if not values: return None
    frame = pd.DataFrame(values)
    base = alt.Chart(frame).encode(x=alt.X('rep:Q', title='Repetition', axis=alt.Axis(tickMinStep=1)), y=alt.Y('value:Q', title=title, scale=alt.Scale(zero=False)))
    chart = base.mark_line(color='#CBD5E1') + base.mark_circle(size=70).encode(
        color=alt.Color('status:N', scale=alt.Scale(domain=['Within baseline', 'Outside baseline', 'No baseline'], range=['#367FBD', '#C24C54', '#7A8694']), legend=alt.Legend(title=None, orient='top')),
        tooltip=[alt.Tooltip('rep:Q', title='Rep'), alt.Tooltip('value:Q', format='.2f'), alt.Tooltip('status:N')])
    if band:
        bounds = pd.DataFrame([dict(band, start=min(v['rep'] for v in values), end=max(v['rep'] for v in values))])
        region = alt.Chart(bounds).mark_rect(color='#DDEDE5', opacity=.6).encode(x='start:Q', x2='end:Q', y='lower:Q', y2='upper:Q')
        mean = alt.Chart(bounds).mark_rule(color='#45836C', strokeDash=[5, 4]).encode(y='mean:Q')
        chart = region + mean + chart
    return chart.properties(height=240, title=title)


def rep_duration_bars(recording):
    rows = [{'rep': r.get('rep'), 'seconds': r.get('duration_sec'), 'classification': {'typical': 'Typical', 'atypical': 'Outside baseline'}.get(r.get('classification'), 'Unassessed')}
            for r in recording.get('rep_assessments') or [] if isinstance(r.get('duration_sec'), (int, float)) and isinstance(r.get('rep'), (int, float))]
    if not rows: return None
    return alt.Chart(pd.DataFrame(rows)).mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3).encode(
        x=alt.X('rep:O', title='Repetition', axis=alt.Axis(labelAngle=0)), y=alt.Y('seconds:Q', title='Seconds'),
        color=alt.Color('classification:N', scale=alt.Scale(domain=CLASS_DOMAIN, range=CLASS_RANGE), legend=alt.Legend(title=None, orient='top')),
        tooltip=[alt.Tooltip('rep:O', title='Rep'), alt.Tooltip('seconds:Q', format='.2f'), alt.Tooltip('classification:N')]).properties(height=260)


# ---------------------------------------------------------------- messages
def conversation(link, height=420):
    patient_id = link['patient_id']
    name = link.get('patient_name') or 'Patient'
    if st.session_state.get('message_patient') != patient_id:
        for key in ('message_draft', 'pending_message_id', 'clear_message_draft'):
            st.session_state.pop(key, None)
        st.session_state.message_patient = patient_id
    rows = backend.messages(token, patient_id)
    with st.container(height=height, border=False):
        if not rows: st.caption('No messages yet. Start the conversation below.')
        for row in rows:
            mine = row.get('sender_id') == uid
            with st.chat_message('assistant' if mine else 'user', avatar=':material/medical_services:' if mine else ':material/person:'):
                st.caption(('You' if mine else name) + (f" · {fmt_time(row.get('created_at'))}" if row.get('created_at') else ''))
                st.text(row.get('text', ''))
    if st.session_state.pop('clear_message_draft', False): st.session_state.pop('message_draft', None)
    with st.form(f'message_{patient_id}'):
        text = st.text_area('Message', max_chars=2000, key='message_draft', placeholder=f'Write to {name}…', label_visibility='collapsed')
        send = st.form_submit_button('Send message →', type='primary', width='stretch')
    if send:
        message_id = st.session_state.setdefault('pending_message_id', str(uuid4()))
        backend.send_message(token, patient_id, text, message_id)
        st.session_state.pop('pending_message_id', None)
        st.session_state.clear_message_draft = True
        st.rerun()
    st.caption('Messages are not monitored continuously. Patients should contact emergency services for urgent concerns.')


# ---------------------------------------------------------------- pages
def invitations_page():
    banner('Invite patients', 'Add patients to your roster. They accept the invitation in the HomeStretch app.')
    left, right = st.columns([1, 1.6], gap='medium')
    with left:
        with card():
            section('Send an invitation')
            st.caption('The patient needs a HomeStretch account with this email. Once they accept under Care team in the app, their sets and messages appear here.')
            with st.form('invite', clear_on_submit=True):
                email = st.text_input('Patient email', placeholder='patient@example.com')
                submitted = st.form_submit_button('Send invitation', type='primary', width='stretch')
            if submitted:
                result = backend.invite_patient(token, email)
                if result == 'already_pending': st.info('An invitation to this patient is already pending.')
                else: st.success('Invitation sent. It appears in the patient app and expires in 7 days.')
    with right:
        with card():
            section('Your invitations')
            rows = sorted(backend.invitations(token), key=lambda r: str(r.get('created_at') or ''), reverse=True)
            if not rows: st.caption('No invitations yet.')
            kinds = {'pending': 'pending', 'accepted': 'active', 'declined': 'review', 'cancelled': 'idle'}
            for row in rows:
                status = row.get('status', 'pending')
                expires = row.get('expires_at')
                if status == 'pending' and isinstance(expires, datetime) and expires < now(): status = 'expired'
                with card('hs-row'):
                    a, b, c = st.columns([2.4, 1.2, 1], vertical_alignment='center')
                    a.markdown(f"**{html.escape(row.get('patient_name') or 'Patient')}**")
                    a.caption(f"Sent {fmt_time(row.get('created_at'), with_time=False)}" + (f" · expires {fmt_time(expires, with_time=False)}" if status == 'pending' else ''))
                    b.markdown(chip(status.capitalize(), kinds.get(status, 'idle')), unsafe_allow_html=True)
                    if status == 'pending' and c.button('Cancel', key=f"cancel_{row['id']}", width='stretch'):
                        backend.cancel_invitation(token, row['id'])
                        st.rerun()


def roster_page(links):
    banner('Patient Roster', 'Your connected HomeStretch patients and their latest exercise sets.')
    summaries = []
    for link in links:
        recordings = load_sessions(link['patient_id'])
        recent = [r for r in recordings if is_recent(r)]
        summaries.append((link, recordings, recent))
    try: pending = sum(r.get('status') == 'pending' for r in backend.invitations(token))
    except Exception: pending = None
    k1, k2, k3, k4 = st.columns(4)
    k1.metric('Patients', len(links))
    k2.metric(f'Sets in last {RECENT_DAYS} days', sum(len(x[2]) for x in summaries))
    k3.metric(f'Reps outside baseline ({RECENT_DAYS} d)', sum(int(r.get('num_atypical') or 0) for x in summaries for r in x[2]))
    k4.metric('Pending invitations', '—' if pending is None else pending)
    if not links:
        st.info('No connected patients yet. Open **Invite patients** to add your first patient.')
        if st.button('Invite a patient →', type='primary'):
            go('Invite patients')
        return
    st.caption('Status is a display aid based on uploaded sets only. It is not a measure of adherence or clinical safety.')
    search = st.text_input('Search patients', placeholder='Patient name', label_visibility='collapsed')
    headers = st.columns([2.1, 1.5, 1, 1.3, 2, 1.1, 1])
    for col, label in zip(headers, ['Patient', 'Status', f'Sets ({RECENT_DAYS} d)', 'Latest typical', 'Latest set', '', '']):
        if label: col.markdown(f'**{label}**')
    for link, recordings, recent in summaries:
        name = link.get('patient_name') or 'Patient'
        if search and search.casefold() not in name.casefold(): continue
        status, kind = patient_status(recordings)
        latest = recordings[0] if recordings else None
        with card('hs-row'):
            cols = st.columns([2.1, 1.5, 1, 1.3, 2, 1.1, 1], vertical_alignment='center')
            cols[0].markdown(f'**{html.escape(name)}**')
            cols[1].markdown(chip(status, kind), unsafe_allow_html=True)
            cols[2].markdown(f'**{len(recent)}**')
            with cols[3]:
                assessed = (latest or {}).get('num_typical'), (latest or {}).get('num_atypical')
                if latest and all(isinstance(v, (int, float)) for v in assessed) and sum(assessed):
                    share = assessed[0] / sum(assessed)
                    st.progress(share)
                    st.caption(f'{assessed[0]} of {sum(assessed)} reps')
                else: st.caption('—')
            cols[4].caption(f"{exercise_of(latest)[1]} · {fmt_time(recording_time(latest))}" if latest else 'No sets yet')
            if cols[5].button('Chat', icon=':material/chat:', key=f"msg_{link['patient_id']}", width='stretch'):
                go('Messages', chat_patient=link['patient_id'])
            if cols[6].button('View →', key=f"view_{link['patient_id']}", width='stretch'):
                st.session_state.selected_patient = link['patient_id']
                st.rerun()


def recording_label(row):
    return f"{exercise_of(row)[1]} · {fmt_time(recording_time(row) or row.get('started_at'))}"


def recording_detail(patient_id, recording):
    a, b, c, d = st.columns(4)
    a.metric('Reps', recording.get('num_reps', '—'))
    b.metric('Typical', recording.get('num_typical', '—'))
    c.metric('Outside baseline', recording.get('num_atypical', '—'))
    d.metric('Unassessed', recording.get('num_unassessed', '—'))
    if recording.get('status') == 'interrupted' or recording.get('complete') is False:
        st.warning('This recording was interrupted. Results may be incomplete.')
    flags = [(r.get('rep'), [METRICS.get(f, f) for f in r.get('features_outside_baseline') or []])
             for r in recording.get('rep_assessments') or [] if r.get('features_outside_baseline')]
    left, right = st.columns([1.4, 1], gap='medium')
    with left:
        chart = rep_duration_bars(recording)
        with card():
            section('Time per repetition')
            if chart is not None: st.altair_chart(chart, width='stretch')
            else: st.caption('Per-rep timing is not available for this set (for example, manually counted sets).')
    with right:
        with card():
            section('Set notes')
            if flags:
                st.caption('Reps outside baseline')
                for rep, features in flags: st.markdown(f"**Rep {rep}** · {html.escape(', '.join(features))}")
            else: st.caption('No reps were flagged outside baseline.')
            if recording.get('local_date'):
                daily = backend.surveys(token, patient_id, recording['local_date'])
                for phase, title in [('before', 'Before exercise'), ('after', 'After exercise')]:
                    answer = daily.get(phase)
                    if answer:
                        st.write(f"**{title}:** pain {answer.get('pain')} / 10")
                        for field in ('symptoms', 'notes'):
                            if answer.get(field): st.caption(str(answer[field]))
                        if answer.get('regions'): st.caption(', '.join(answer['regions']))
                    else: st.caption(f'{title}: survey not received')
    section('Movement metrics by repetition')
    st.caption('Shaded bands show the baseline saved with this set. Red points are outside that range, not a diagnosis.')
    columns, shown = st.columns(2), 0
    for key, title in METRICS.items():
        chart = per_rep_chart(recording, key, title)
        if chart is None: continue
        with columns[shown % 2]: st.altair_chart(chart, width='stretch')
        shown += 1
    if not shown: st.info('This set does not contain per-rep movement metrics. Sets recorded with a saved baseline include them.')


def profile_page(link):
    patient_id = link['patient_id']
    name = link.get('patient_name') or 'Patient'
    if st.button('← Back to Patients'):
        st.session_state.selected_patient = None
        st.rerun()
    recordings = load_sessions(patient_id)
    status, kind = patient_status(recordings)
    with card('hs-profile-banner'):
        left, right = st.columns([4, 1], vertical_alignment='center')
        left.subheader(name)
        left.caption('HomeStretch patient' + (f" · connected {fmt_time(link.get('created_at'), with_time=False)}" if link.get('created_at') else ''))
        right.markdown(chip(status, kind), unsafe_allow_html=True)
    curls = [r for r in recordings if is_bicep_curl(r)]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric('Recorded sets', len(recordings))
    k2.metric('Bicep curl sets', len(curls))
    k3.metric('Bicep curl reps', sum(int(r.get('num_reps') or 0) for r in curls))
    latest_time = recording_time(recordings[0]) if recordings else None
    k4.metric('Latest set', latest_time.astimezone().strftime('%b %d') if latest_time else '—')

    tab_progress, tab_sets, tab_messages, tab_manage = st.tabs(['Progress', 'Sets', 'Messages', 'Connection'])
    with tab_progress:
        if not recordings:
            st.info('No sets yet. Completed sets appear here after the patient app uploads them.')
        else:
            exercises = {}
            for r in recordings: exercises.setdefault(exercise_of(r)[0], exercise_of(r)[1])
            ids = list(exercises)
            default = next((i for i, e in enumerate(ids) if 'bicep' in f'{e} {exercises[e]}'.casefold() or 'curl' in f'{e} {exercises[e]}'.casefold()), 0)
            chosen = st.selectbox('Exercise', ids, index=default, format_func=lambda e: exercises[e], key=f'exercise_{patient_id}')
            selected = [r for r in recordings if exercise_of(r)[0] == chosen]
            st.caption(f'{len(selected)} set(s) of {exercises[chosen]} · newest of the latest 100 uploads')
            left, right = st.columns(2, gap='medium')
            with left:
                with card():
                    section('Repetitions per set')
                    chart = reps_chart(selected)
                    if chart is not None: st.altair_chart(chart, width='stretch')
                    else: st.caption('No repetition counts are available.')
            with right:
                with card():
                    section('Time per repetition')
                    chart = duration_chart(selected)
                    if chart is not None:
                        st.altair_chart(chart, width='stretch')
                        st.caption('Line: mean seconds per rep. Bar: fastest to slowest rep in the set.')
                    else: st.caption('Per-rep timing is not available for these sets.')
            with card():
                section('Movement metric across sets')
                keys = [k for k in METRICS if metric_by_rep_frame(selected, k)]
                if not keys:
                    st.caption('These sets have no per-rep movement metrics yet. Sets recorded with a saved baseline include them.')
                else:
                    key = st.selectbox('Metric', keys, format_func=METRICS.get, key=f'metric_{patient_id}')
                    _, set_order = set_label_map(selected)
                    shown = set_checkboxes(set_order, f'trend_{patient_id}_{chosen}')
                    chart = metric_trend_chart(selected, key, shown)
                    if chart is not None: st.altair_chart(chart, width='stretch')
                    else: st.caption('No sets selected. Tick at least one set above.')
                    st.caption('Each line is one set. Points are the per-rep values exactly as stored, in rep order (rep 1, rep 2, …).')
    with tab_sets:
        if not recordings:
            st.info('No sets yet.')
        else:
            recording = st.selectbox('Set (latest 100)', recordings, format_func=recording_label, key=f'set_{patient_id}')
            recording_detail(patient_id, recording)
    with tab_messages:
        with card():
            section(f'Conversation with {name}')
            conversation(link, height=360)
    with tab_manage:
        with card():
            section('Manage connection')
            st.caption('Disconnecting removes your access to this patient’s sets and messages. The patient can be invited again later.')
            confirm = st.checkbox('Remove this patient from my roster')
            if st.button('Disconnect patient', disabled=not confirm):
                backend.disconnect(token, patient_id)
                st.session_state.selected_patient = None
                st.rerun()


def messages_page(links):
    banner('Messages', 'Communicate with your connected patients')
    if not links:
        st.info('Messages are available after a patient accepts your invitation.')
        return
    ids = [l['patient_id'] for l in links]
    if st.session_state.get('chat_patient') not in ids: st.session_state.chat_patient = ids[0]
    left, right = st.columns([1, 2.15], gap='medium')
    with left:
        with card():
            section('Patients')
            search = st.text_input('Search conversations', placeholder='Search patients…', label_visibility='collapsed')
            for link in links:
                name = link.get('patient_name') or 'Patient'
                if search and search.casefold() not in name.casefold(): continue
                selected = link['patient_id'] == st.session_state.chat_patient
                if st.button(('●  ' if selected else '○  ') + name, key=f"chat_{link['patient_id']}", width='stretch', type='primary' if selected else 'secondary'):
                    st.session_state.chat_patient = link['patient_id']
                    st.rerun()
    with right:
        link = next(l for l in links if l['patient_id'] == st.session_state.chat_patient)
        with card():
            section(link.get('patient_name') or 'Patient')
            conversation(link)


try:
    if view == 'Invite patients':
        invitations_page()
    else:
        links = backend.linked_patients(token)
        if view == 'Messages':
            messages_page(links)
        else:
            selected = next((l for l in links if l['patient_id'] == st.session_state.get('selected_patient')), None)
            if selected: profile_page(selected)
            else: roster_page(links)
except Exception as error:
    # Do not render tokens, credentials, or backend tracebacks in the UI.
    if isinstance(error, (PermissionError, ValueError)): st.error(str(error))
    else: st.error('Could not load or save this information. Check the server configuration and try Refresh.')
