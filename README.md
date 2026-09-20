<div align="center">

# 🌳 Carbon Credit Verifier

**Satellite-based fraud detection for carbon-credit and afforestation claims.**

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-UI-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Earth Engine](https://img.shields.io/badge/Data-Google%20Earth%20Engine-34A853?logo=googleearth&logoColor=white)](https://earthengine.google.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

*Verify whether a plantation or carbon-offset project is genuine by comparing satellite-derived vegetation data (NDVI) from before and after its claimed period — powered by free Sentinel-2 imagery.*

[Features](#-features) • [How It Works](#%EF%B8%8F-how-it-works) • [Quick Start](#-quick-start) • [Hosting](#%EF%B8%8F-hosting) • [Limitations](#%EF%B8%8F-limitations) • [Roadmap](#%EF%B8%8F-roadmap)

</div>

---

## 🚩 The Problem

Carbon credits are supposed to represent real, verified CO₂ reduction — but verification is hard and expensive. Multiple international investigations have found that a significant share of registered carbon-offset projects don't deliver the emissions reduction they claim. Manual, human-only verification doesn't scale to the size of today's carbon markets.

**Carbon Credit Verifier** provides a fast, low-cost, automated first-pass signal — so human auditors can focus their limited time on the projects that genuinely need a closer look.

## ✨ Features

| | |
|---|---|
| 🔍 **Single Location Check** | Enter coordinates + area, get an instant vegetation-change report |
| 📋 **Batch Mode** | Upload a CSV of multiple projects, verify them all in one run |
| 📄 **PDF Reports** | Clean, shareable reports generated for every check |
| 📧 **Email Alerts** | Automatic notification when a project comes back HIGH RISK |
| 🖥️ **Single UI, No CLI** | Everything runs from one Streamlit app |
| ☁️ **Hostable** | Deploy free on Streamlit Community Cloud via a service account — no per-user login needed |

## ⚙️ How It Works

```
Location + Dates  →  Satellite Fetch  →  NDVI Calculation  →  Risk Score  →  Report / Alert
   (lat, lon)         (Sentinel-2,          (before vs           (LOW /         (PDF + email)
                       Earth Engine)          after)              MEDIUM /
                                                                   HIGH)
```

1. Takes a location (lat/lon) and area size
2. Pulls Sentinel-2 satellite imagery for a "before" and "after" date range (free, ~10m resolution, cloud-masked)
3. Calculates **NDVI** — a standard vegetation-health index — for both periods
4. Compares the change and assigns a risk score
5. Generates a report and optionally sends an email alert if risk is high

## 🛠️ Tech Stack

- **Python** — core logic
- **Google Earth Engine** — free satellite data access & processing
- **Streamlit** — web UI
- **fpdf2** — PDF report generation
- **pandas** — CSV / batch handling

## 📦 Project Structure

```
carbon_verifier/
├── app.py                        # Streamlit UI (run this)
├── carbon_verify.py               # Core satellite + NDVI + risk logic
├── batch_verify.py                # Batch processing + email alerts
├── report_utils.py                # PDF report generator
├── requirements.txt
├── projects_sample.csv            # Sample batch input format
├── alert_config_sample.json       # Email alert config template
├── SETUP.md                       # Full setup & deployment guide
└── .streamlit/
    └── secrets_example.toml       # Template for hosted deployment secrets
```

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- A free [Google Earth Engine](https://code.earthengine.google.com/register) account

### Install

```bash
git clone https://github.com/your-username/carbon-verifier.git
cd carbon-verifier
pip install -r requirements.txt
earthengine authenticate
```

### Run

```bash
streamlit run app.py
```

Open the local URL Streamlit gives you. Everything — single check, batch check, PDF downloads, email settings — happens from that one page.

> 📖 First-time Earth Engine setup? See the full walkthrough in [`SETUP.md`](SETUP.md).

## ☁️ Hosting

This app can be hosted for free on [Streamlit Community Cloud](https://share.streamlit.io) so others can test it without any local setup. Hosted environments use a **Google Cloud Service Account** instead of interactive login:

1. Create a Google Cloud project and enable the Earth Engine API
2. Create a Service Account, register it for Earth Engine access, download its JSON key
3. Push this repo to GitHub (`.gitignore` already excludes secrets)
4. Deploy on Streamlit Community Cloud, pointing to `app.py`
5. In the app's **Secrets** settings, add:
   ```toml
   EE_SERVICE_ACCOUNT_JSON = '''{ ...your full JSON key... }'''
   EE_PROJECT_ID = "your-project-id"
   ```

Full details, including how to create and register the service account, are in [`SETUP.md`](SETUP.md#4-service-account-setup-required-for-hosting).

## 📊 Example Output

```json
{
  "location": {"lat": 26.4499, "lon": 80.3319},
  "area_acres": 2,
  "before_mean_ndvi": 0.18,
  "after_mean_ndvi": 0.52,
  "percent_change": 188.9,
  "risk_level": "LOW RISK",
  "note": "Vegetation cover shows a significant increase — consistent with the claim."
}
```

## ⚠️ Limitations

- Sentinel-2 resolution is **10m/pixel** — individual small trees aren't visible; results are more reliable for larger plots (10+ acres)
- Cloud cover can reduce data availability for some date ranges/locations
- NDVI changes can have natural causes (seasonal drought, etc.) — a `HIGH RISK` flag means *"needs investigation,"* not *"confirmed fraud"*
- This tool provides a **screening signal only** — it does not replace accredited human verification required by bodies like Verra or Gold Standard

## 🗺️ Roadmap

- [ ] Visual before/after satellite image comparison in the UI
- [ ] Scheduled automatic re-checks (cron/Task Scheduler integration guide)
- [ ] Support for higher-resolution paid imagery (Planet Labs) for small plots
- [ ] Multi-language UI support
- [ ] Interactive map view for batch results

## 🤝 Contributing

Issues and pull requests are welcome. If you spot a bug or have an idea for improving detection accuracy, feel free to open an issue.

## 📄 License

MIT License — free to use, modify, and distribute.

## 🙏 Acknowledgements

- [Google Earth Engine](https://earthengine.google.com/) for free satellite data access
- [Sentinel-2](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) (ESA/Copernicus) imagery

---

<div align="center">

Built to make carbon-market verification a little more transparent. 🌍

</div>
