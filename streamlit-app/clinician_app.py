"""HomeStretch clinician app: roster, invitations, messages and bicep-curl progress.

Styled after the original HomeStretch Figma clinician dashboard: light-blue title bar,
a plain text navigation row, flat pale-blue panels and soft status pills. All data comes
from clinician_backend, which only returns records of actively linked patients.
"""
import base64
import html
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4
import pandas as pd
import altair as alt
import streamlit as st
import clinician_backend as backend
from clinician_charts import (METRICS, metric_frame, exercise_of, is_bicep_curl, recording_time,
                              session_trend_frame, rep_duration_frame, metric_trend_frame, metric_by_rep_frame)

ASSETS = Path(__file__).parent / 'assets'


def logo_uri(variant='blue'):
    """Logo as a data URI so it can be placed inside custom HTML (blue on light, white on blue)."""
    data = (ASSETS / f'logo-{variant}.png').read_bytes()
    return 'data:image/png;base64,' + base64.b64encode(data).decode()


st.set_page_config(page_title='HomeStretch | Clinician', page_icon=str(ASSETS / 'logo-blue.png'), layout='wide')
st.markdown("""<style>
:root {--hs-bar:#BED0E5;--hs-blue:#4B78AF;--hs-brand:#3C79B4;--hs-ink:#2E3A46;--hs-muted:#6B7C8E;
       --hs-panel:#EEF3F9;--hs-line:#D5E0EC;--hs-btn:#D8E3F0;}
[data-testid="stAppViewContainer"] {background:#FFFFFF;color:var(--hs-ink);}
[data-testid="stHeader"] {background:transparent;}
[data-testid="stSidebar"],[data-testid="stSidebarCollapsedControl"] {display:none;}
.block-container {max-width:1280px;padding-top:0;padding-bottom:3rem;}
h1,h2,h3 {color:var(--hs-ink)!important;font-weight:600!important;letter-spacing:0;}

/* Title bar: full-width light blue, title centred, logo + wordmark on the left. */
.hs-topbar {position:relative;background:var(--hs-bar);margin:-1rem calc(50% - 50vw) 0;height:64px;display:flex;align-items:center;justify-content:center;}
.hs-topbar .hs-title {color:var(--hs-blue);font-size:1.25rem;font-weight:500;}
.hs-brand {display:flex;align-items:center;gap:10px;}
.hs-topbar .hs-brand {position:absolute;left:max(24px, calc(50vw - 640px + 1rem));}
.hs-brand img {width:30px;height:30px;}
.hs-brand span {color:var(--hs-brand);font-size:1.05rem;font-weight:600;}
.hs-intro {color:var(--hs-muted);font-size:.9rem;margin:2px 0 18px;}
@media(max-width:760px){.hs-topbar .hs-brand span{display:none}.hs-topbar .hs-title{font-size:1.1rem}}

/* Navigation row: plain text links, active one underlined. */
.st-key-hs_navrow {border-bottom:1px solid var(--hs-line);padding:6px 0 0;margin-bottom:10px;}
.st-key-hs_nav [role="radiogroup"] {gap:28px;flex-wrap:wrap;}
.st-key-hs_nav label:has(input[type="radio"]) {margin:0;padding:6px 0 8px;border-bottom:2px solid transparent;cursor:pointer;}
.st-key-hs_nav label[data-baseweb="radio"] > div:first-child,
.st-key-hs_nav label[data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) {display:none;}
.st-key-hs_nav label:has(input[type="radio"]) p {color:var(--hs-muted);font-size:.95rem;}
.st-key-hs_nav label:has(input:checked) {border-bottom-color:var(--hs-blue);}
.st-key-hs_nav label:has(input:checked) p {color:var(--hs-blue);font-weight:600;}

.hs-section {font-size:.95rem;font-weight:600;color:var(--hs-blue);margin:0 0 8px;}
.hs-marker {display:none;}
[data-testid="stElementContainer"]:has(> div > [data-testid="stMarkdownContainer"] .hs-marker),[data-testid="stElementContainer"]:has(.hs-marker) {display:none;}
.hs-chip {display:inline-block;padding:2px 10px;border-radius:4px;font-size:.78rem;font-weight:500;color:#2E3A46;}
.hs-chip.active {background:#B9DDBD;}
.hs-chip.review {background:#F2B6B3;}
.hs-chip.idle {background:#E3E7EC;color:#56616D;}
.hs-chip.pending {background:#F6DE9A;}
.hs-chip.new {background:var(--hs-btn);color:#34598A;}

/* Flat panels instead of shadowed cards. */
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-white-card),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-white-card) {background:var(--hs-panel);border:none!important;border-radius:6px!important;padding:14px 18px!important;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-row),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-row) {background:#FFFFFF;border:none!important;border-bottom:1px solid var(--hs-line)!important;border-radius:0!important;padding:2px 4px!important;}
[data-testid="stVerticalBlockBorderWrapper"]:has(.hs-profile-banner),[data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .hs-profile-banner) {background:#FFFFFF;border:none!important;border-bottom:1px solid var(--hs-line)!important;border-radius:0!important;padding:4px 0 10px!important;}
.st-key-hs_chatlist button {justify-content:flex-start;text-align:left;}
.st-key-hs_chatlist button > div {justify-content:flex-start;}
.hs-avatar {width:52px;height:52px;border-radius:50%;background:#E3E7EC;display:flex;align-items:center;justify-content:center;color:#6B7C8E;font-weight:600;font-size:1.05rem;}
.hs-table-head p {color:var(--hs-muted)!important;font-size:.82rem;font-weight:500;}

/* Summary figures: number beside its label, like the Figma dashboard. */
.hs-kpis {display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:4px 0 18px;}
.hs-kpi {background:var(--hs-panel);border-radius:6px;padding:12px 16px;display:flex;align-items:center;gap:12px;}
.hs-kpi b {color:var(--hs-blue);font-size:1.5rem;font-weight:500;line-height:1;}
.hs-kpi span {color:var(--hs-ink);font-size:.82rem;line-height:1.25;}

/* Tabs: plain text with an underline. */
.stTabs [role="tablist"] {gap:28px;border-bottom:1px solid var(--hs-line);}
.stTabs [role="tab"] {padding:6px 0;}
.stTabs [role="tab"] p {color:var(--hs-muted);font-size:.92rem;}
.stTabs [role="tab"][aria-selected="true"] p {color:var(--hs-blue);font-weight:600;}
.stTabs [data-baseweb="tab-highlight"] {background:var(--hs-blue);}
.stTabs [data-baseweb="tab-border"] {display:none;}

/* Buttons and inputs: flat, small radius, muted blue. */
.stButton>button,.stFormSubmitButton>button,[data-testid="stPopover"] button {border-radius:4px;border:1px solid var(--hs-line);background:#FFFFFF;color:#34598A;font-weight:500;box-shadow:none;}
.stButton>button:hover,.stFormSubmitButton>button:hover {border-color:var(--hs-bar);background:var(--hs-panel);color:#34598A;}
.stButton>button[kind^="primary"],.stFormSubmitButton>button[kind^="primary"] {background:var(--hs-bar)!important;border-color:var(--hs-bar)!important;color:#2F5687!important;}
.stButton>button[kind^="primary"]:hover,.stFormSubmitButton>button[kind^="primary"]:hover {background:#ADC4DE!important;border-color:#ADC4DE!important;}
.stButton>button[kind="tertiary"] {border:none;background:transparent;padding-left:0;}
[data-testid="stBaseButton-primary"] p,[data-testid="stBaseButton-primaryFormSubmit"] p,button[kind="primary"] p {color:#2F5687!important;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {background:#FFFFFF;}
[data-testid="stTextInput"] [data-baseweb="input"],[data-testid="stTextArea"] [data-baseweb="textarea"],[data-baseweb="select"]>div {border-radius:4px;border-color:var(--hs-line);background:#FFFFFF;}
[data-testid="stForm"] {background:transparent;border:none;padding:0;}
[data-testid="stProgressBarTrack"] {background:#E3E7EC;}
[data-testid="stProgressBarTrack"] > div {background:#9CC9A2;}
[data-testid="stChatMessage"] {background:#FFFFFF;border-radius:6px;}
[data-testid="stExpander"] details {border:1px solid var(--hs-line);border-radius:4px;}
[data-testid="stAlert"] > div {border-radius:4px;}

/* Sign-in page: pale panel under a "Login" bar, logo + wordmark centred. */
.hs-login-brand {display:flex;flex-direction:column;align-items:center;gap:10px;margin:44px 0 8px;}
.hs-login-brand img {width:64px;height:64px;}
.hs-login-brand span {color:var(--hs-brand);font-size:1.6rem;font-weight:600;}
.hs-login-brand small {color:var(--hs-muted);font-size:.9rem;}
.st-key-hs_login {background:var(--hs-panel);border-radius:6px;padding:8px 28px 24px;margin-top:28px;}
</style>""", unsafe_allow_html=True)

# Colors: typical (muted blue), outside baseline (soft red, always labelled), unassessed (gray).
CLASS_DOMAIN = ['Typical', 'Outside baseline', 'Unassessed']
CLASS_RANGE = ['#8FB0D6', '#D9787A', '#C9D1DA']
RECENT_DAYS = 7


def chart_style(chart):
    """Flat Altair styling that matches the panels: light grid, no frame, muted labels."""
    return (chart.configure(background='transparent', font='sans-serif')
            .configure_view(stroke=None)
            .configure_axis(gridColor='#DCE4EE', domainColor='#C3CFDC', tickColor='#C3CFDC', labelColor='#5F6F80', titleColor='#5F6F80', titleFontWeight='normal', labelFontSize=11, titleFontSize=11)
            .configure_legend(labelColor='#3F4C59', labelFontSize=11, symbolType='square')
            .configure_title(color='#4B78AF', fontWeight='normal', fontSize=13, anchor='start'))


def top_bar():
    brand = f'<div class="hs-brand"><img src="{logo_uri()}" alt=""><span>HomeStretch</span></div>'
    st.markdown(f'<div class="hs-topbar">{brand}</div>', unsafe_allow_html=True)


def banner(subtitle=''):
    """Short line under the navigation; the page name itself sits in the title bar."""
    if subtitle: st.markdown(f'<p class="hs-intro">{html.escape(subtitle)}</p>', unsafe_allow_html=True)


def kpis(items):
    cells = ''.join(f'<div class="hs-kpi"><b>{html.escape(str(value))}</b><span>{html.escape(label)}</span></div>' for value, label in items)
    st.markdown(f'<div class="hs-kpis">{cells}</div>', unsafe_allow_html=True)


def card(marker='hs-white-card'):
    box = st.container(border=True)
    box.markdown(f'<span class="hs-marker {marker}"></span>', unsafe_allow_html=True)
    return box


def section(title):
    st.markdown(f'<div class="hs-section">{html.escape(title)}</div>', unsafe_allow_html=True)


def chip(text, kind):
    return f'<span class="hs-chip {kind}">{html.escape(text)}</span>'


def initials(name):
    parts = [p for p in str(name).split() if p]
    return ''.join(p[0] for p in parts[:2]).upper() or 'P'


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
    st.markdown('<div class="hs-topbar"><div class="hs-title">Clinician Login</div></div>', unsafe_allow_html=True)
    _, center, _ = st.columns([1, 1.1, 1])
    with center:
        with st.container(key='hs_login'):
            st.markdown(f'<div class="hs-login-brand"><img src="{logo_uri()}" alt="HomeStretch logo"><span>HomeStretch</span>'
                        '<small>Clinician portal</small></div>', unsafe_allow_html=True)
            with st.form('sign_in', clear_on_submit=True):
                email = st.text_input('Email')
                password = st.text_input('Password', type='password')
                submitted = st.form_submit_button('Sign in', type='primary', width='stretch')
    if submitted:
        try:
            st.session_state.clinician_token = backend.sign_in(email, password)
            st.rerun()
        except PermissionError as error:
            # Wrong email/password, or the account has no clinician role.
            with center: st.error(str(error))
        except Exception:
            with center: st.error('The server could not reach Firebase. In the terminal that runs Streamlit, set '
                                  'GOOGLE_APPLICATION_CREDENTIALS to the Firebase Admin key file, then restart the app.')
    st.stop()

token = st.session_state.clinician_token
try:
    uid, profile = backend.clinician(token)
except Exception:
    sign_out()
    st.info('Please sign in again. Your session may have expired or access may have changed.')
    st.stop()

# ---------------------------------------------------------------- title bar + navigation
VIEWS = ['Patients', 'Invite patients', 'Messages']
st.session_state.setdefault('view', 'Patients')
if 'nav_request' in st.session_state: st.session_state.view = st.session_state.pop('nav_request')
top_bar()
clinician_name = profile.get('display_name') or 'Clinician'
with st.container(key='hs_navrow'):
    nav_col, refresh_col, account_col = st.columns([6, 1.1, 1.9], vertical_alignment='center')
    with nav_col, st.container(key='hs_nav'):
        view = st.radio('Navigate', VIEWS, key='view', horizontal=True, label_visibility='collapsed')
    refresh_col.button('Refresh', icon=':material/refresh:', width='stretch')
    with account_col.popover(clinician_name, icon=':material/account_circle:', width='stretch'):
        st.caption('Signed in as a HomeStretch clinician')
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
    rng = alt.Chart(frame).mark_rule(color='#BED0E5', strokeWidth=6).encode(x=x, y=alt.Y('min:Q', title='Seconds per rep', scale=alt.Scale(zero=False)), y2='max:Q', tooltip=tooltip)
    line = alt.Chart(frame).mark_line(color='#4B78AF', strokeWidth=2, point=alt.OverlayMarkDef(size=55, filled=True, color='#4B78AF')).encode(x=x, y='mean:Q', tooltip=tooltip)
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
    palette = ['#4B78AF', '#9DB9DA', '#C8615F', '#E6A9A4', '#5E9A72', '#A9D0B1', '#C99A3E', '#E9CF8C', '#7C6BA8', '#C2B7DA']
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
    picked = sum(st.session_state[k] for k in keys.values())
    summary = f'Sets: All ({len(labels)})' if picked == len(labels) else 'Sets: none' if picked == 0 else f'Sets: {picked} of {len(labels)}'
    with st.popover(summary, width='stretch'):
        st.checkbox('Select all', key=all_key, on_change=toggle_all)
        for label in labels:
            st.checkbox(label, key=keys[label], on_change=sync_all)
    return [label for label in labels if st.session_state[keys[label]]]


def per_rep_chart(recording, key, title):
    values, band = metric_frame(recording, key)
    if not values: return None
    frame = pd.DataFrame(values)
    base = alt.Chart(frame).encode(x=alt.X('rep:Q', title='Repetition', axis=alt.Axis(tickMinStep=1)), y=alt.Y('value:Q', title=title, scale=alt.Scale(zero=False)))
    chart = base.mark_line(color='#C9D3DE') + base.mark_circle(size=70).encode(
        color=alt.Color('status:N', scale=alt.Scale(domain=['Within baseline', 'Outside baseline', 'No baseline'], range=['#4B78AF', '#C8615F', '#8C97A3']), legend=alt.Legend(title=None, orient='top')),
        tooltip=[alt.Tooltip('rep:Q', title='Rep'), alt.Tooltip('value:Q', format='.2f'), alt.Tooltip('status:N')])
    if band:
        bounds = pd.DataFrame([dict(band, start=min(v['rep'] for v in values), end=max(v['rep'] for v in values))])
        region = alt.Chart(bounds).mark_rect(color='#E3EFE5', opacity=.8).encode(x='start:Q', x2='end:Q', y='lower:Q', y2='upper:Q')
        mean = alt.Chart(bounds).mark_rule(color='#6E9C7B', strokeDash=[5, 4]).encode(y='mean:Q')
        chart = region + mean + chart
    return chart.properties(height=240, title=title)


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
        send = st.form_submit_button('Send message', type='primary', width='stretch')
    if send:
        message_id = st.session_state.setdefault('pending_message_id', str(uuid4()))
        backend.send_message(token, patient_id, text, message_id)
        st.session_state.pop('pending_message_id', None)
        st.session_state.clear_message_draft = True
        st.rerun()
    st.caption('Messages are not monitored continuously. Patients should contact emergency services for urgent concerns.')


# ---------------------------------------------------------------- pages
def invitations_page():
    banner('Add patients to your roster. They accept the invitation in the HomeStretch app.')
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
    banner('Your connected HomeStretch patients and their latest exercise sets.')
    summaries = []
    for link in links:
        recordings = load_sessions(link['patient_id'])
        recent = [r for r in recordings if is_recent(r)]
        summaries.append((link, recordings, recent))
    try: pending = sum(r.get('status') == 'pending' for r in backend.invitations(token))
    except Exception: pending = None
    kpis([(len(links), 'Connected patients'),
          (sum(len(x[2]) for x in summaries), f'Sets in the last {RECENT_DAYS} days'),
          (sum(int(r.get('num_atypical') or 0) for x in summaries for r in x[2]), f'Reps outside baseline ({RECENT_DAYS} days)'),
          ('—' if pending is None else pending, 'Pending invitations')])
    if not links:
        st.info('No connected patients yet. Open **Invite patients** to add your first patient.')
        if st.button('Invite a patient', type='primary'):
            go('Invite patients')
        return
    st.caption('Status is a display aid based on uploaded sets only. It is not a measure of adherence or clinical safety.')
    search = st.text_input('Search patients', placeholder='Search patients', label_visibility='collapsed')
    headers = st.columns([2.1, 1.5, 1, 1.3, 2, 1.1, 1])
    for col, label in zip(headers, ['Patient', 'Status', f'Sets ({RECENT_DAYS} d)', 'Latest typical', 'Latest set', '', '']):
        if label: col.markdown(f'<div class="hs-table-head"><p>{label}</p></div>', unsafe_allow_html=True)
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
            if cols[6].button('View', key=f"view_{link['patient_id']}", width='stretch'):
                st.session_state.selected_patient = link['patient_id']
                st.rerun()


def recording_label(row):
    return f"{exercise_of(row)[1]} · {fmt_time(recording_time(row) or row.get('started_at'))}"


def recording_detail(patient_id, recording):
    kpis([(recording.get('num_reps', '—'), 'Reps'), (recording.get('num_typical', '—'), 'Typical'),
          (recording.get('num_atypical', '—'), 'Outside baseline'), (recording.get('num_unassessed', '—'), 'Unassessed')])
    if recording.get('status') == 'interrupted' or recording.get('complete') is False:
        st.warning('This recording was interrupted. Results may be incomplete.')
    flags = [(r.get('rep'), [METRICS.get(f, f) for f in r.get('features_outside_baseline') or []])
             for r in recording.get('rep_assessments') or [] if r.get('features_outside_baseline')]
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
        with columns[shown % 2]: st.altair_chart(chart_style(chart), width='stretch')
        shown += 1
    if not shown: st.info('This set does not contain per-rep movement metrics. Sets recorded with a saved baseline include them.')


def profile_page(link):
    patient_id = link['patient_id']
    name = link.get('patient_name') or 'Patient'
    if st.button('Back to patients', icon=':material/arrow_back:', type='tertiary'):
        st.session_state.selected_patient = None
        st.rerun()
    recordings = load_sessions(patient_id)
    status, kind = patient_status(recordings)
    with card('hs-profile-banner'):
        avatar, left, right = st.columns([.6, 6, 1.4], vertical_alignment='center')
        avatar.markdown(f'<div class="hs-avatar">{html.escape(initials(name))}</div>', unsafe_allow_html=True)
        left.markdown(f'<div style="font-size:1.2rem;font-weight:600;margin-bottom:-6px">{html.escape(name)}</div>', unsafe_allow_html=True)
        left.caption('HomeStretch patient' + (f" · connected {fmt_time(link.get('created_at'), with_time=False)}" if link.get('created_at') else ''))
        right.markdown(chip(status, kind), unsafe_allow_html=True)
    curls = [r for r in recordings if is_bicep_curl(r)]
    latest_time = recording_time(recordings[0]) if recordings else None
    kpis([(len(recordings), 'Recorded sets'), (len(curls), 'Bicep curl sets'),
          (sum(int(r.get('num_reps') or 0) for r in curls), 'Bicep curl reps'),
          (latest_time.astimezone().strftime('%b %d') if latest_time else '—', 'Latest set')])

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
                    if chart is not None: st.altair_chart(chart_style(chart), width='stretch')
                    else: st.caption('No repetition counts are available.')
            with right:
                with card():
                    section('Time per repetition')
                    chart = duration_chart(selected)
                    if chart is not None:
                        st.altair_chart(chart_style(chart), width='stretch')
                        st.caption('Line: mean seconds per rep. Bar: fastest to slowest rep in the set.')
                    else: st.caption('Per-rep timing is not available for these sets.')
            with card():
                section('Movement metric across sets')
                keys = [k for k in METRICS if metric_by_rep_frame(selected, k)]
                if not keys:
                    st.caption('These sets have no per-rep movement metrics yet. Sets recorded with a saved baseline include them.')
                else:
                    metric_col, sets_col = st.columns([2, 1], vertical_alignment='bottom')
                    with metric_col: key = st.selectbox('Metric', keys, format_func=METRICS.get, key=f'metric_{patient_id}')
                    _, set_order = set_label_map(selected)
                    with sets_col: shown = set_checkboxes(set_order, f'trend_{patient_id}_{chosen}')
                    chart = metric_trend_chart(selected, key, shown)
                    if chart is not None: st.altair_chart(chart_style(chart), width='stretch')
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
    banner('Message your connected patients.')
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
            chat_list = st.container(key='hs_chatlist')
            for link in links:
                name = link.get('patient_name') or 'Patient'
                if search and search.casefold() not in name.casefold(): continue
                selected = link['patient_id'] == st.session_state.chat_patient
                if chat_list.button(name, key=f"chat_{link['patient_id']}", width='stretch', type='primary' if selected else 'secondary'):
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
