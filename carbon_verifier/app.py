"""
Carbon Credit / Afforestation Verifier — Web UI (All-in-One)
==============================================================
Everything happens from this one UI — single location check, batch
(multiple projects) check, PDF download, and email alert settings.
No separate terminal commands needed.

Run with:
    streamlit run app.py
"""

import io
import zipfile

import streamlit as st
import pandas as pd

from carbon_verify import run_verification
from report_utils import generate_pdf_report
from batch_verify import send_email_alert

st.set_page_config(
    page_title="Carbon Credit Verifier",
    page_icon="🌳",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Styling — forest background image (clear, lightly tinted) + glass-card look
# ---------------------------------------------------------------------------
FOREST_BG_URL = "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1920&q=90"

st.markdown(
    f"""
    <style>
    .stApp {{
        background-image: linear-gradient(rgba(4, 20, 10, 0.78), rgba(4, 20, 10, 0.85)),
            url('{FOREST_BG_URL}');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }}
    .main .block-container {{
        background-color: rgba(17, 24, 21, 0.92);
        border-radius: 16px;
        padding: 2.2rem 2.5rem;
        margin-top: 1.5rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }}
    .main .block-container, .main .block-container p,
    .main .block-container span, .main .block-container label,
    .main .block-container div {{
        color: #f1f5f2;
        font-weight: 600;
    }}
    section[data-testid="stSidebar"] {{
        background-color: rgba(17, 24, 21, 0.95);
    }}
    section[data-testid="stSidebar"] * {{
        color: #f1f5f2 !important;
        font-weight: 600;
    }}
    h1, h2, h3 {{
        color: #4ade80 !important;
        font-weight: 800 !important;
    }}
    .stTextInput input, .stNumberInput input, .stDateInput input {{
        background-color: #1f2b25 !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        border: 1px solid #4ade80 !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        color: #f1f5f2 !important;
        font-weight: 700 !important;
    }}
    .stTabs [aria-selected="true"] {{
        color: #4ade80 !important;
        border-bottom-color: #4ade80 !important;
    }}
    .stCaption, .st-emotion-cache-caption {{
        color: #cbd5c9 !important;
        font-weight: 500 !important;
    }}
    .risk-badge {{
        display: inline-block;
        padding: 6px 18px;
        border-radius: 999px;
        font-weight: 800;
        font-size: 1.1rem;
        margin-top: 6px;
    }}
    .risk-low {{ background-color: #22c55e; color: #052e12; }}
    .risk-medium {{ background-color: #facc15; color: #422006; }}
    .risk-high {{ background-color: #ef4444; color: #450a0a; }}
    .risk-unknown {{ background-color: #9ca3af; color: #111827; }}
    footer {{visibility: hidden;}}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("🌳 Carbon Credit / Afforestation Verifier")
st.write(
    "Check whether a plantation or carbon-credit claim is genuine using "
    "satellite data — for a single location or many projects at once."
)

# ---------------------------------------------------------------------------
# Earth Engine credentials — supports both hosted (st.secrets) and local (authenticate)
# ---------------------------------------------------------------------------
def get_ee_service_account():
    """Returns the service-account JSON from Streamlit secrets if this app
    is hosted. On a local run this will be empty and the normal
    `earthengine authenticate` flow is used instead."""
    try:
        return st.secrets["EE_SERVICE_ACCOUNT_JSON"]
    except Exception:
        return None


ee_service_account_json = get_ee_service_account()
ee_project_id = None
try:
    ee_project_id = st.secrets.get("EE_PROJECT_ID", None)
except Exception:
    pass

if ee_service_account_json is None:
    st.info(
        "Running in local mode (using your own authenticated Earth Engine "
        "account). If this app is hosted and you're seeing this message, "
        "EE_SERVICE_ACCOUNT_JSON still needs to be set in Streamlit "
        "secrets — see the 'Hosting' section in README.md.",
        icon="ℹ️",
    )

# ---------------------------------------------------------------------------
# Sidebar — Email Alert Settings (optional, all from the UI)
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("📧 Email Alert Settings")
    st.caption("Optional — fill this in if you want an email when a HIGH RISK result is found.")
    enable_email = st.checkbox("Send email on high risk")
    email_config = None
    if enable_email:
        sender_email = st.text_input("Sender Gmail address")
        sender_password = st.text_input("App Password (16-char, from Gmail settings)", type="password")
        receiver_email = st.text_input("Send alerts to (receiver email)")
        if sender_email and sender_password and receiver_email:
            email_config = {
                "smtp_server": "smtp.gmail.com",
                "smtp_port": 587,
                "sender_email": sender_email,
                "sender_password": sender_password,
                "receiver_email": receiver_email,
            }
        else:
            st.info("Email alerts will work once all three fields are filled in.")

st.divider()

# ---------------------------------------------------------------------------
# Project ID — entered once here, shared across both tabs
# ---------------------------------------------------------------------------
if "gcp_project_id" not in st.session_state:
    st.session_state.gcp_project_id = ee_project_id or "carbon-verifier"

st.session_state.gcp_project_id = st.text_input(
    "🔑 Google Cloud Project ID (required by Earth Engine)",
    value=st.session_state.gcp_project_id,
    placeholder="e.g. carbon-verifier-123456",
    help="Find this at console.cloud.google.com (top project dropdown), or on the Earth Engine registration page. Enter once — it's used for both Single and Batch checks below.",
)

st.divider()

# ---------------------------------------------------------------------------
# Helper to render a single result nicely
# ---------------------------------------------------------------------------
def render_result(report, key_prefix=""):
    m1, m2, m3 = st.columns(3)
    m1.metric("Before NDVI", f"{report['before_mean_ndvi']:.3f}" if report["before_mean_ndvi"] is not None else "N/A")
    m2.metric("After NDVI", f"{report['after_mean_ndvi']:.3f}" if report["after_mean_ndvi"] is not None else "N/A")
    m3.metric("Change", f"{report['percent_change']:.1f}%" if report["percent_change"] is not None else "N/A")

    risk = report["risk_level"]
    risk_class = {
        "LOW RISK": "risk-low", "MEDIUM RISK": "risk-medium", "HIGH RISK": "risk-high",
    }.get(risk, "risk-unknown")
    st.markdown(f"<span class='risk-badge {risk_class}'>{risk}</span>", unsafe_allow_html=True)
    st.write("")
    st.info(report["note"])

    with st.expander("🔧 Raw Report (JSON)"):
        st.json(report)

    pdf_bytes = generate_pdf_report(report, project_name=report.get("name", f"Lat {report['location']['lat']}"))
    st.download_button(
        "⬇️ Download PDF Report", data=pdf_bytes,
        file_name=f"carbon_report_{key_prefix}.pdf", mime="application/pdf",
        use_container_width=True, key=f"dl_{key_prefix}",
    )
    st.caption(
        f"Images used — before: {report['before_image_count']}, after: {report['after_image_count']}. "
        "If this shows 0, try a different date range or location (likely cloud cover)."
    )


# ---------------------------------------------------------------------------
# Tabs — Single Check | Batch Check
# ---------------------------------------------------------------------------
tab1, tab2 = st.tabs(["🔍 Single Location Check", "📋 Batch Check (Multiple Projects)"])

# ============================== TAB 1: SINGLE ==============================
with tab1:
    st.subheader("📍 Location Details")
    col1, col2, col3 = st.columns(3)
    with col1:
        lat = st.number_input("Latitude", value=26.4499, format="%.6f")
    with col2:
        lon = st.number_input("Longitude", value=80.3319, format="%.6f")
    with col3:
        acres = st.number_input("Area (acres)", value=2.0, min_value=0.1, step=0.5)

    st.map(pd.DataFrame({"lat": [lat], "lon": [lon]}), zoom=12)

    st.subheader("📅 Date Ranges")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Before (baseline) period**")
        before_start = st.date_input("Start date", value=pd.to_datetime("2019-01-01"), key="bs")
        before_end = st.date_input("End date", value=pd.to_datetime("2019-12-31"), key="be")
    with col_b:
        st.markdown("**After (latest) period**")
        after_start = st.date_input("Start date", value=pd.to_datetime("2024-01-01"), key="as")
        after_end = st.date_input("End date", value=pd.to_datetime("2024-12-31"), key="ae")

    with st.expander("⚙️ Advanced (only if Earth Engine asks for a project id)"):
        project_id = st.text_input("Override Project ID for this check (optional)", value="", key="single_project")

    if st.button("🔍 Verify Now", type="primary", use_container_width=True):
        with st.spinner("Fetching and analyzing satellite images..."):
            try:
                report = run_verification(
                    lat=lat, lon=lon, acres=acres,
                    before_start=str(before_start), before_end=str(before_end),
                    after_start=str(after_start), after_end=str(after_end),
                    project=project_id if project_id else (st.session_state.gcp_project_id or ee_project_id),
                    service_account_json=ee_service_account_json,
                )
            except SystemExit:
                st.error("Earth Engine is not authenticated. Please complete the setup steps in README.md first.")
                st.stop()
            except Exception as e:
                st.error(f"Error: {e}")
                st.stop()

        st.success("Verification complete!")
        st.subheader("📊 Result")
        render_result(report, key_prefix=f"{lat}_{lon}")

        if enable_email and email_config and report["risk_level"] == "HIGH RISK":
            send_email_alert(
                [{"name": f"Lat {lat}, Lon {lon}", "lat": lat, "lon": lon,
                  "before_mean_ndvi": report["before_mean_ndvi"], "after_mean_ndvi": report["after_mean_ndvi"]}],
                email_config,
            )
            st.warning("HIGH RISK detected — an email alert has been sent.")

# ============================== TAB 2: BATCH ==============================
with tab2:
    st.subheader("📤 Upload Projects CSV")
    st.caption(
        "The CSV should have these columns: name, lat, lon, acres, "
        "before_start, before_end, after_start, after_end"
    )

    sample_csv = (
        "name,lat,lon,acres,before_start,before_end,after_start,after_end\n"
        "Kanpur Sample Plot,26.4499,80.3319,2,2019-01-01,2019-12-31,2024-01-01,2024-12-31\n"
    )
    st.download_button(
        "⬇️ Download Sample CSV Template", data=sample_csv,
        file_name="projects_sample.csv", mime="text/csv",
    )

    uploaded_file = st.file_uploader("Upload your CSV file here", type=["csv"])

    with st.expander("⚙️ Advanced (only if Earth Engine asks for a project id)"):
        batch_project_id = st.text_input("Override Project ID for this batch (optional)", value="", key="batch_project")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Preview:")
        st.dataframe(df, use_container_width=True)

        if st.button("🔍 Run Batch Verification", type="primary", use_container_width=True):
            results = []
            high_risk_list = []
            pdf_files = {}

            progress = st.progress(0, text="Starting...")
            for i, row in df.iterrows():
                progress.progress((i + 1) / len(df), text=f"Checking: {row['name']} ...")
                try:
                    report = run_verification(
                        lat=float(row["lat"]), lon=float(row["lon"]), acres=float(row["acres"]),
                        before_start=str(row["before_start"]), before_end=str(row["before_end"]),
                        after_start=str(row["after_start"]), after_end=str(row["after_end"]),
                        project=batch_project_id if batch_project_id else (st.session_state.gcp_project_id or ee_project_id),
                        service_account_json=ee_service_account_json,
                    )
                    report["name"] = row["name"]
                    results.append(report)

                    pdf_bytes = generate_pdf_report(report, project_name=row["name"])
                    safe_name = "".join(c if c.isalnum() else "_" for c in str(row["name"]))
                    pdf_files[f"{safe_name}.pdf"] = pdf_bytes

                    if report["risk_level"] == "HIGH RISK":
                        high_risk_list.append(report)

                except Exception as e:
                    results.append({"name": row["name"], "error": str(e)})

            progress.empty()
            st.success(f"Batch complete! {len(results)} project(s) checked.")

            # Summary table
            summary_rows = []
            for r in results:
                if "error" in r:
                    summary_rows.append({"Name": r["name"], "Risk": f"ERROR: {r['error']}"})
                else:
                    summary_rows.append({
                        "Name": r["name"],
                        "Before NDVI": r["before_mean_ndvi"],
                        "After NDVI": r["after_mean_ndvi"],
                        "% Change": r["percent_change"],
                        "Risk": r["risk_level"],
                    })
            summary_df = pd.DataFrame(summary_rows)
            st.dataframe(summary_df, use_container_width=True)

            # Downloads: summary CSV + zip of all PDFs
            col_x, col_y = st.columns(2)
            with col_x:
                st.download_button(
                    "⬇️ Download Summary CSV", data=summary_df.to_csv(index=False),
                    file_name="batch_summary.csv", mime="text/csv", use_container_width=True,
                )
            with col_y:
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for fname, fbytes in pdf_files.items():
                        zf.writestr(fname, fbytes)
                st.download_button(
                    "⬇️ Download All PDF Reports (zip)", data=zip_buffer.getvalue(),
                    file_name="batch_reports.zip", mime="application/zip", use_container_width=True,
                )

            if high_risk_list:
                st.warning(f"⚠️ {len(high_risk_list)} project(s) came back HIGH RISK.")
                if enable_email and email_config:
                    alert_data = [
                        {"name": r["name"], "lat": r["location"]["lat"], "lon": r["location"]["lon"],
                         "before_mean_ndvi": r["before_mean_ndvi"], "after_mean_ndvi": r["after_mean_ndvi"]}
                        for r in high_risk_list
                    ]
                    send_email_alert(alert_data, email_config)
                    st.info("Email alert sent.")

st.divider()
st.caption(
    "⚠️ This tool only provides a starting signal (based on 10m-resolution Sentinel-2 data). "
    "Legal/official carbon-credit certification still requires an accredited human auditor."
)
