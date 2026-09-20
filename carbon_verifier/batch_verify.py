"""
Batch Verifier — Multiple Projects Ek Saath Check Karna
=========================================================
Ek CSV file (projects.csv) padhta hai jisme kai projects/locations ki list
hoti hai, har ek ko verify karta hai, results ek combined CSV + PDF mein
save karta hai, aur agar koi HIGH RISK mile to email alert bhejta hai
(agar email config diya ho).

Isi script ko cron (Linux/Mac) ya Task Scheduler (Windows) se daily/weekly
automatically chalaya ja sakta hai — "Step 1" (scheduled run) aur "Step 5"
(alerting) isi tarah implement hote hain. Dekho README.md ka "Scheduling"
section.

Usage:
    python batch_verify.py --input projects_sample.csv --output results

    (optional email alerts ke liye alert_config.json banao — README dekho)
"""

import argparse
import csv
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

from carbon_verify import run_verification
from report_utils import generate_pdf_report


def load_projects(csv_path: str):
    projects = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            projects.append(row)
    return projects


def send_email_alert(high_risk_projects: list, config: dict):
    """SMTP ke through simple email alert bhejta hai. Gmail use kar rahe ho
    to 'App Password' banana padega (README mein steps hain)."""
    if not high_risk_projects:
        return

    body_lines = ["⚠️ Carbon Credit Verifier — HIGH RISK Alert\n"]
    for p in high_risk_projects:
        body_lines.append(
            f"- {p['name']} (lat={p['lat']}, lon={p['lon']}): "
            f"before NDVI={p['before_mean_ndvi']}, after NDVI={p['after_mean_ndvi']}"
        )
    body = "\n".join(body_lines)

    msg = MIMEMultipart()
    msg["From"] = config["sender_email"]
    msg["To"] = config["receiver_email"]
    msg["Subject"] = f"[ALERT] {len(high_risk_projects)} HIGH RISK carbon project(s) found"
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(config.get("smtp_server", "smtp.gmail.com"), config.get("smtp_port", 587))
        server.starttls()
        server.login(config["sender_email"], config["sender_password"])
        server.sendmail(config["sender_email"], config["receiver_email"], msg.as_string())
        server.quit()
        print(f"Email alert bhej diya {config['receiver_email']} ko.")
    except Exception as e:
        print(f"Email bhejne mein error aaya: {e}")


def main():
    parser = argparse.ArgumentParser(description="Batch verify multiple carbon projects from a CSV")
    parser.add_argument("--input", type=str, default="projects_sample.csv", help="Input CSV path")
    parser.add_argument("--output", type=str, default="results", help="Output folder name")
    parser.add_argument("--project", type=str, default=None, help="Google Cloud project id (agar zaroorat pade)")
    parser.add_argument("--alert-config", type=str, default="alert_config.json", help="Email alert config file")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    projects = load_projects(args.input)
    print(f"{len(projects)} projects mile CSV mein. Verification shuru ho raha hai...\n")

    results = []
    high_risk_list = []

    for p in projects:
        name = p.get("name", "Unnamed")
        print(f"-> Checking: {name} ...")
        try:
            report = run_verification(
                lat=float(p["lat"]),
                lon=float(p["lon"]),
                acres=float(p["acres"]),
                before_start=p["before_start"],
                before_end=p["before_end"],
                after_start=p["after_start"],
                after_end=p["after_end"],
                project=args.project,
            )
            report["name"] = name
            results.append(report)

            # Individual PDF save karo
            pdf_bytes = generate_pdf_report(report, project_name=name)
            safe_name = "".join(c if c.isalnum() else "_" for c in name)
            pdf_path = os.path.join(args.output, f"{safe_name}.pdf")
            with open(pdf_path, "wb") as f:
                f.write(pdf_bytes)

            print(f"   Risk: {report['risk_level']}  |  PDF: {pdf_path}")

            if report["risk_level"] == "HIGH RISK":
                high_risk_list.append(report)

        except Exception as e:
            print(f"   ERROR: {e}")
            results.append({"name": name, "error": str(e)})

    # Combined summary CSV
    summary_path = os.path.join(args.output, "summary.csv")
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["name", "lat", "lon", "acres", "before_ndvi", "after_ndvi", "percent_change", "risk_level"])
        for r in results:
            if "error" in r:
                writer.writerow([r["name"], "", "", "", "", "", "", f"ERROR: {r['error']}"])
            else:
                writer.writerow([
                    r["name"], r["location"]["lat"], r["location"]["lon"], r["area_acres"],
                    r["before_mean_ndvi"], r["after_mean_ndvi"], r["percent_change"], r["risk_level"],
                ])

    # Combined summary JSON (poora detail)
    with open(os.path.join(args.output, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\nDone. Summary: {summary_path}")
    print(f"HIGH RISK projects found: {len(high_risk_list)}")

    # Email alert agar config file mile
    if os.path.exists(args.alert_config) and high_risk_list:
        with open(args.alert_config, "r", encoding="utf-8") as f:
            config = json.load(f)
        alert_data = [
            {
                "name": r["name"], "lat": r["location"]["lat"], "lon": r["location"]["lon"],
                "before_mean_ndvi": r["before_mean_ndvi"], "after_mean_ndvi": r["after_mean_ndvi"],
            }
            for r in high_risk_list
        ]
        send_email_alert(alert_data, config)
    elif high_risk_list:
        print(f"({args.alert_config} nahi mila, isliye email alert skip ho gaya)")


if __name__ == "__main__":
    main()
