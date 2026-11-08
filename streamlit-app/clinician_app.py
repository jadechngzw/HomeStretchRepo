import streamlit as st
from uuid import uuid4
import pandas as pd
import altair as alt
import clinician_backend as backend
from clinician_charts import metric_frame, METRICS

st.set_page_config(page_title='HomeStretch | Clinician', page_icon='🏠', layout='wide')
st.markdown("""<style>
.stApp {background: linear-gradient(180deg,#EFF6FB 0,#FFFFFF 440px);color:#253746;}
h1,h2,h3 {color:#367FBD !important;}
[data-testid="stSidebar"] {background:#DCEBF6;}
.stButton button,.stFormSubmitButton button {border-radius:24px;background:#D5E5F5;color:#286DA6;border:1px solid #B5D2EA;padding:.55rem 1.5rem;}
[data-testid="stTextInput"] input,[data-testid="stTextArea"] textarea {background:white;border-radius:12px;}
[data-testid="stForm"] {background:rgba(255,255,255,.8);border:1px solid #C4DCEF;border-radius:24px;padding:24px;}
[data-testid="stChatMessage"] {background:#E6F0F8;border-radius:20px;}
</style>""",unsafe_allow_html=True)
st.title('HomeStretch')

def sign_out():
    st.session_state.clear()

if not st.session_state.get('clinician_token'):
    _, center, _ = st.columns([1,1.25,1])
    with center:
        st.subheader('Clinician sign in')
        st.caption('Welcome back. Sign in to view your patients.')
        with st.form('sign_in', clear_on_submit=True):
            email=st.text_input('Email')
            password=st.text_input('Password', type='password')
            submitted=st.form_submit_button('Sign in',use_container_width=True)
    if submitted:
        try:
            st.session_state.clinician_token=backend.sign_in(email,password)
            st.rerun()
        except Exception:
            st.error('Could not sign in. Check your account details, clinician access, and server credentials.')
    st.stop()

token=st.session_state.clinician_token
try:
    uid, profile=backend.clinician(token)
except Exception:
    sign_out()
    st.info('Please sign in again. Your session may have expired or access may have changed.')
    st.stop()

st.sidebar.write(profile.get('display_name','Clinician'))
with st.sidebar.expander('Your profile'):
    with st.form('clinician_profile'):
        display_name=st.text_input('Full name',value=profile.get('display_name',''))
        save_profile=st.form_submit_button('Save name')
    if save_profile:
        try:
            backend.update_clinician_profile(token,display_name)
            st.rerun()
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error('Could not save your name. Please try again.')
st.sidebar.button('Sign out', on_click=sign_out)
section=st.sidebar.radio('View',['Patients','Invitations','Messages'])
st.sidebar.button('Refresh')

try:
    if section=='Invitations':
        st.subheader('Invite a patient')
        st.caption('The patient needs a HomeStretch account. They will see your invitation in Messages and must accept before you can see their data.')
        with st.form('invite',clear_on_submit=True):
            email=st.text_input('Patient email')
            submitted=st.form_submit_button('Send invitation')
        if submitted:
            backend.invite_patient(token,email)
            st.success('Invitation is available in the patient app.')
        rows=backend.invitations(token)
        if rows: st.dataframe(pd.DataFrame([{'Patient':r.get('patient_name'),'Status':r.get('status'),'Expires':r.get('expires_at')} for r in rows]),hide_index=True,width='stretch')
        else: st.info('No invitations yet.')
        st.stop()

    links=backend.linked_patients(token)
    if not links:
        st.info('No connected patients yet. Open Invitations to invite your first patient.')
        st.stop()
    link=st.selectbox('Patient',links,format_func=lambda x:x.get('patient_name') or x['patient_id'])
    patient_id=link['patient_id']
    if st.session_state.get('message_patient') != patient_id:
        for key in ('message_draft','pending_message_id','clear_message_draft'):
            st.session_state.pop(key,None)
        st.session_state.message_patient=patient_id
    if section=='Messages':
        st.subheader('Messages')
        st.caption('Messages are not monitored continuously.')
        rows=backend.messages(token,patient_id)
        if not rows: st.info('No messages yet.')
        for row in rows:
            with st.chat_message('You' if row['sender_id']==uid else link.get('patient_name','Patient'),avatar=':material/person:'):
                st.caption('You' if row['sender_id']==uid else link.get('patient_name','Patient'))
                st.text(row['text'])
        if st.session_state.pop('clear_message_draft',False): st.session_state.pop('message_draft',None)
        with st.form('message'):
            text=st.text_area('Message',max_chars=2000,key='message_draft')
            send=st.form_submit_button('Send')
        if send:
            message_id=st.session_state.setdefault('pending_message_id',str(uuid4()))
            backend.send_message(token,patient_id,text,message_id)
            st.session_state.pop('pending_message_id',None)
            st.session_state.clear_message_draft=True
            st.rerun()
        st.stop()

    recordings=backend.sessions(token,patient_id)
    if not recordings:
        st.info('No recordings yet. Completed sets will appear here after the patient app uploads them.')
        st.stop()
    def label(row):
        exercise=row.get('exercise',{})
        name=exercise.get('name','Exercise') if isinstance(exercise,dict) else str(exercise)
        return f"{name} · {row.get('started_at','Unknown date')}"
    recording=st.selectbox('Recording (latest 100)',recordings,format_func=label)
    st.subheader((recording.get('exercise') or {}).get('name','Exercise') if isinstance(recording.get('exercise'),dict) else str(recording.get('exercise','Exercise')))
    a,b,c=st.columns(3)
    a.metric('Reps',recording.get('num_reps','Not available'))
    b.metric('Outside baseline',recording.get('num_atypical','Not available'))
    c.metric('Unassessed',recording.get('num_unassessed','Not available'))
    if recording.get('status')=='interrupted' or recording.get('complete') is False: st.warning('This recording was interrupted. Results may be incomplete.')
    if recording.get('local_date'):
        daily=backend.surveys(token,patient_id,recording['local_date'])
        with st.expander('Daily surveys',expanded=True):
            for phase,title in [('before','Before exercise'),('after','After exercise')]:
                answer=daily.get(phase)
                if answer:
                    st.write(f"**{title}:** Pain {answer.get('pain')} / 10")
                    if answer.get('symptoms'): st.text(answer['symptoms'])
                    if answer.get('regions'): st.text(', '.join(answer['regions']))
                    if answer.get('notes'): st.text(answer['notes'])
                else: st.caption(f'{title}: not received')
    st.caption('Shaded bands show this patient’s saved baseline range. Highlighted points are outside that range, not a diagnosis.')
    available=0
    columns=st.columns(2)
    for key,title in METRICS.items():
        values,band=metric_frame(recording,key)
        if not values: continue
        available+=1
        frame=pd.DataFrame(values)
        base=alt.Chart(frame).encode(x=alt.X('rep:Q',title='Repetition',axis=alt.Axis(tickMinStep=1)),y=alt.Y('value:Q',title=title,scale=alt.Scale(zero=False)))
        chart=base.mark_line(color='#CBD5E1') + base.mark_circle(size=70).encode(color=alt.Color('status:N',scale=alt.Scale(domain=['Within baseline','Outside baseline','No baseline'],range=['#367FBD','#C24C54','#7A8694']),legend=alt.Legend(title=None)),tooltip=[alt.Tooltip('rep:Q',title='Rep'),alt.Tooltip('value:Q',format='.2f'),alt.Tooltip('status:N')])
        if band:
            bounds=pd.DataFrame([dict(band,start=min(v['rep'] for v in values),end=max(v['rep'] for v in values))])
            region=alt.Chart(bounds).mark_rect(color='#DDEDE5',opacity=.6).encode(x='start:Q',x2='end:Q',y='lower:Q',y2='upper:Q')
            mean=alt.Chart(bounds).mark_rule(color='#45836C',strokeDash=[5,4]).encode(y='mean:Q')
            chart=region+mean+chart
        with columns[(available-1)%2]: st.altair_chart(chart.properties(height=240,title=title),width='stretch')
    if not available: st.info('This recording does not contain per-rep movement metrics. New baseline-based recordings will include them.')
    with st.expander('Manage connection'):
        confirm=st.checkbox('Remove this patient from my care team')
        if st.button('Disconnect patient',disabled=not confirm):
            backend.disconnect(token,patient_id)
            st.rerun()
except Exception as error:
    # Do not render tokens, credentials, or backend tracebacks in the UI.
    if isinstance(error,(PermissionError,ValueError)): st.error(str(error))
    else: st.error('Could not load or save this information. Check the server configuration and try Refresh.')
