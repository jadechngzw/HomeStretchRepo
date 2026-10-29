
import os
import secrets
import hashlib
import base64
import logging
import time
import threading
from urllib.parse import quote

from pathlib import Path
from html import escape
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware


# =====================================================
# CONFIGURATION
# =====================================================

load_dotenv(Path(__file__).with_name(".env"))

CLIENT_ID = os.environ["EPIC_CLIENT_ID"]
CLIENT_SECRET = os.environ["EPIC_CLIENT_SECRET"]
REDIRECT_URI = os.environ["EPIC_REDIRECT_URI"]
FHIR_BASE = os.environ["EPIC_FHIR_BASE"].rstrip("/")
SESSION_SECRET = os.environ["SESSION_SECRET"]
HANDOFF_SECRET = os.environ["HOMESTRETCH_HANDOFF_SECRET"]

STREAMLIT_PATIENTS_URL = os.getenv(
    "STREAMLIT_PATIENTS_URL",
    "http://localhost:8501/Patients"
)
# This scope worked with your clinician sandbox login.
SCOPES = "openid fhirUser"

# Epic's published synthetic test patient.
TEST_PATIENT_ID = "erXuFYUfucBZaryVksYEcMg3"

logger = logging.getLogger("homestretch.epic")

app = FastAPI(title="HomeStretch Epic Integration")

# Local development only.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
    https_only=False,
)


# =====================================================
# EPIC TO STREAMLIT HANDOFF
# Local development only
# =====================================================

_handoffs = {}
_handoff_lock = threading.Lock()

HANDOFF_TTL_SECONDS = 300


@app.post("/internal/consume-handoff")
def consume_handoff(
    payload: dict,
    request: Request,
    x_homestretch_secret: str | None = Header(default=None)
):
    """
    Transfer a synthetic Epic patient summary to Streamlit.

    Tickets are single-use and expire after five minutes.
    Epic access tokens are never sent to Streamlit.
    """

    if (
        not x_homestretch_secret
        or not secrets.compare_digest(
            x_homestretch_secret,
            HANDOFF_SECRET
        )
    ):
        raise HTTPException(
            status_code=403,
            detail="Forbidden"
        )

    ticket = payload.get("ticket")

    if not isinstance(ticket, str) or len(ticket) > 256:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket"
        )

    with _handoff_lock:
        entry = _handoffs.pop(ticket, None)

    if (
        entry is None
        or time.monotonic() > entry["expires"]
    ):
        raise HTTPException(
            status_code=404,
            detail="Ticket expired or already used"
        )

    return entry["patient"]

# =====================================================
# SMART ON FHIR CONFIGURATION
# =====================================================

def get_smart_config():
    response = requests.get(
        FHIR_BASE + "/.well-known/smart-configuration",
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def make_pkce():
    verifier = secrets.token_urlsafe(48)

    digest = hashlib.sha256(
        verifier.encode("utf-8")
    ).digest()

    challenge = base64.urlsafe_b64encode(
        digest
    ).rstrip(b"=").decode("ascii")

    return verifier, challenge


# =====================================================
# HOMESTRETCH PAGE STYLING
# =====================================================

def page(title, content, status_code=200):
    return HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport"
                  content="width=device-width, initial-scale=1">

            <title>{escape(title)}</title>

            <style>
                body {{
                    font-family: Arial, sans-serif;
                    background: #F7FAFD;
                    color: #285F91;
                    max-width: 780px;
                    margin: 55px auto;
                    padding: 20px;
                }}

                .header {{
                    background: #C4DCEF;
                    padding: 28px;
                    border-radius: 16px;
                    margin-bottom: 22px;
                }}

                .header h1 {{
                    margin: 0 0 8px;
                    font-size: 32px;
                }}

                .header p {{
                    margin: 0;
                    color: #527D9F;
                }}

                .card {{
                    background: white;
                    border: 1px solid #BBD5E9;
                    border-radius: 14px;
                    padding: 26px;
                    margin-bottom: 18px;
                }}

                h2 {{
                    margin-top: 0;
                    color: #285F91;
                }}

                .button {{
                    display: inline-block;
                    background: #367FBD;
                    color: white;
                    padding: 12px 20px;
                    border-radius: 9px;
                    text-decoration: none;
                    margin-top: 10px;
                }}

                .label {{
                    color: #71879A;
                    font-size: 13px;
                    margin-bottom: 5px;
                }}

                .value {{
                    font-size: 17px;
                    font-weight: 600;
                    margin-bottom: 18px;
                    overflow-wrap: anywhere;
                }}

                .success {{
                    color: #27845E;
                    font-weight: 600;
                }}

                .note {{
                    font-size: 13px;
                    color: #71879A;
                }}
            </style>
        </head>

        <body>
            <div class="header">
                <h1>HomeStretch</h1>
                <p>Epic SMART on FHIR Sandbox Integration</p>
            </div>

            {content}
        </body>
        </html>
        """,
        status_code=status_code,
    )


# =====================================================
# HOME PAGE
# =====================================================

@app.get("/")
def home():
    return page(
        "HomeStretch Epic Integration",
        """
        <div class="card">
            <h2>Epic Sandbox Connection</h2>

            <p>
                Connect HomeStretch to Epic's FHIR sandbox
                using a test clinician account.
            </p>

            <p>
                After authorization, HomeStretch will
                attempt to retrieve a synthetic patient
                using the FHIR Patient.Read API.
            </p>

            <a class="button" href="/login">
                Connect to Epic Sandbox
            </a>
        </div>

        <div class="card">
            <p class="note">
                Development environment only.
                No real patient information is used.
            </p>
        </div>
        """
    )


# =====================================================
# LOGIN - START SMART AUTHORIZATION
# =====================================================

@app.get("/login")
def login(request: Request):
    config = get_smart_config()

    verifier, challenge = make_pkce()
    state = secrets.token_urlsafe(32)

    request.session["oauth_state"] = state
    request.session["pkce_verifier"] = verifier

    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    }

    authorization_url = (
        config["authorization_endpoint"]
        + "?"
        + urlencode(params)
    )

    return RedirectResponse(
        authorization_url,
        status_code=302,
    )


# =====================================================
# OAUTH CALLBACK
# =====================================================

@app.get("/callback")
def callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
):
    # Epic returned an OAuth error.
    if error:
        return page(
            "Epic Authorization Error",
            f"""
            <div class="card">
                <h2>Epic Authorization Error</h2>

                <p><strong>Error:</strong>
                    {escape(error)}
                </p>

                <p>
                    {escape(error_description or
                            "No additional details provided.")}
                </p>

                <a class="button" href="/">
                    Try Again
                </a>
            </div>
            """,
            status_code=400,
        )

    # Validate OAuth state.
    expected_state = request.session.pop(
        "oauth_state", None
    )

    verifier = request.session.pop(
        "pkce_verifier", None
    )

    if (
        not expected_state
        or not state
        or not secrets.compare_digest(
            expected_state, state
        )
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid OAuth state",
        )

    if not code or not verifier:
        raise HTTPException(
            status_code=400,
            detail="Missing OAuth authorization data",
        )

    # =================================================
    # EXCHANGE AUTHORIZATION CODE FOR ACCESS TOKEN
    # =================================================

    config = get_smart_config()

    try:
        token_response = requests.post(
            config["token_endpoint"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": REDIRECT_URI,
                "code_verifier": verifier,
            },
            auth=(CLIENT_ID, CLIENT_SECRET),
            headers={
                "Accept": "application/json",
            },
            timeout=20,
        )

    except requests.RequestException:
        logger.exception("Epic token request failed")
        return page(
            "Connection Error",
            """
            <div class="card">
                <h2>Connection Error</h2>
                <p>Unable to reach Epic's token endpoint.</p>
            </div>
            """,
            status_code=502,
        )

    if not token_response.ok:
        logger.warning(
            "Epic token exchange returned HTTP %s",
            token_response.status_code,
        )

        return page(
            "Token Exchange Error",
            f"""
            <div class="card">
                <h2>Token Exchange Failed</h2>

                <p>
                    Epic returned HTTP
                    {token_response.status_code}.
                </p>

                <p>
                    Check your client ID, client secret,
                    redirect URI, and sandbox configuration.
                </p>
            </div>
            """,
            status_code=400,
        )

    token_data = token_response.json()
    access_token = token_data.get("access_token")

    if not access_token:
        raise HTTPException(
            status_code=502,
            detail="Epic did not return an access token",
        )

    # =================================================
    # RETRIEVE SYNTHETIC PATIENT BY FHIR ID
    # =================================================

    patient_url = (
        f"{FHIR_BASE}/Patient/{TEST_PATIENT_ID}"
    )

    try:
        patient_response = requests.get(
            patient_url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/fhir+json",
            },
            timeout=20,
        )

    except requests.RequestException:
        logger.exception("Epic Patient.Read request failed")

        return page(
            "Patient Retrieval Error",
            """
            <div class="card">
                <h2>Patient Retrieval Error</h2>
                <p>Unable to reach Epic's FHIR API.</p>
            </div>
            """,
            status_code=502,
        )

    if not patient_response.ok:
        return page(
            "Patient Retrieval Error",
            f"""
            <div class="card">
                <h2>Epic Authorization Succeeded</h2>

                <p class="success">
                    Clinician authentication completed.
                </p>

                <p>
                    Patient.Read returned HTTP
                    {patient_response.status_code}.
                </p>

                <p>
                    401: Check token authorization.<br>
                    403: Check API permissions and scopes.<br>
                    404: Check the patient ID and endpoint.
                </p>

                <a class="button" href="/">
                    Return Home
                </a>
            </div>
            """,
            status_code=patient_response.status_code,
        )

    patient = patient_response.json()

    if patient.get("resourceType") != "Patient":
        return page(
            "Unexpected FHIR Response",
            """
            <div class="card">
                <h2>Unexpected Response</h2>
                <p>
                    Epic returned a resource other
                    than Patient.
                </p>
            </div>
            """,
            status_code=502,
        )

    # =================================================
    # EXTRACT PATIENT INFORMATION
    # =================================================

    names = patient.get("name") or [{}]
    name = names[0]

    given_names = name.get("given") or []
    family_name = name.get("family") or ""

    full_name = " ".join(
        [*given_names, family_name]
    ).strip() or "Unknown"

    patient_id = patient.get(
        "id", "Unavailable"
    )

    gender = patient.get(
        "gender", "Unavailable"
    )

    birth_date = patient.get(
        "birthDate", "Unavailable"
    )

    # =================================================
    # CREATE STREAMLIT HANDOFF
    # =================================================

    patient_summary = {
        "id": str(patient_id),
        "name": full_name,
        "gender": str(gender),
        "birthDate": str(birth_date),
        "source": "Epic FHIR R4 Sandbox",
    }

    ticket = secrets.token_urlsafe(32)

    with _handoff_lock:

        now = time.monotonic()

        # Remove expired tickets.
        for key in list(_handoffs):
            if _handoffs[key]["expires"] <= now:
                del _handoffs[key]

        _handoffs[ticket] = {
            "patient": patient_summary,
            "expires": now + HANDOFF_TTL_SECONDS,
        }

    joiner = (
        "&" if "?" in STREAMLIT_PATIENTS_URL else "?"
    )

    streamlit_link = (
        STREAMLIT_PATIENTS_URL
        + joiner
        + "epic_ticket="
        + quote(ticket)
    )

    # =================================================
    # DISPLAY SUCCESS PAGE
    # =================================================

    return page(
        "Epic Patient Retrieved",
        f"""
        <div class="card">
            <h2>Epic Sandbox Connected</h2>

            <p class="success">
                Clinician authentication successful.
            </p>

            <p>
                HomeStretch successfully retrieved
                a synthetic patient using Epic's
                FHIR Patient.Read API.
            </p>

            <div class="label">Patient Name</div>
            <div class="value">
                {escape(full_name)}
            </div>

            <div class="label">FHIR Patient ID</div>
            <div class="value">
                {escape(str(patient_id))}
            </div>

            <div class="label">Gender</div>
            <div class="value">
                {escape(str(gender))}
            </div>

            <div class="label">Date of Birth</div>
            <div class="value">
                {escape(str(birth_date))}
            </div>

            <div class="label">FHIR Resource</div>
            <div class="value">Patient</div>

            <p class="note">
                Source: Epic FHIR R4 Sandbox
            </p>
        </div>

         <div class="card">
            <h2>Open HomeStretch Clinician Dashboard</h2>

            <p>
                Transfer this synthetic Epic patient
                to your local Streamlit Patients page.
            </p>

            <a
                class="button"
                href="{escape(streamlit_link, quote=True)}"
            >
                Open in Streamlit
            </a>

            <p class="note">
                This one-time link expires in five minutes
                and works only once.
            </p>
        </div>
        """
    )
