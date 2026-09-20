"""
PDF Report Generator
=====================
Ek single verification report ko clean PDF mein convert karta hai.
Both app.py (single check) aur batch_verify.py (bulk check) isko use karte hain.
"""

from datetime import datetime
from fpdf import FPDF


RISK_COLORS = {
    "LOW RISK": (22, 101, 52),      # green
    "MEDIUM RISK": (133, 77, 14),   # amber
    "HIGH RISK": (153, 27, 27),     # red
    "UNKNOWN": (55, 65, 81),        # gray
}


class ReportPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(20, 83, 45)
        self.cell(0, 10, "Carbon Credit / Afforestation Verification Report", ln=True)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
        self.ln(4)
        self.set_draw_color(180, 180, 180)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(140, 140, 140)
        self.cell(
            0, 10,
            "Auto-generated signal report. Satellite resolution: 10m (Sentinel-2). "
            "Not a substitute for accredited human verification.",
            align="C",
        )


def _row(pdf, label, value):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(55, 8, label, border=0)
    pdf.set_font("Helvetica", "", 11)
    pdf.cell(0, 8, str(value), ln=True)


def generate_pdf_report(report: dict, project_name: str = None) -> bytes:
    """Ek report dict le kar PDF bytes return karta hai (Streamlit download
    button ya file-save dono ke liye use ho sakta hai)."""
    pdf = ReportPDF()
    pdf.add_page()

    if project_name:
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(20, 83, 45)
        pdf.cell(0, 8, f"Project: {project_name}", ln=True)
        pdf.ln(2)

    loc = report.get("location", {})
    _row(pdf, "Latitude:", loc.get("lat"))
    _row(pdf, "Longitude:", loc.get("lon"))
    _row(pdf, "Area (acres):", report.get("area_acres"))
    _row(pdf, "Before period:", " to ".join(report.get("before_period", [])))
    _row(pdf, "After period:", " to ".join(report.get("after_period", [])))
    pdf.ln(4)

    before_ndvi = report.get("before_mean_ndvi")
    after_ndvi = report.get("after_mean_ndvi")
    pct = report.get("percent_change")

    _row(pdf, "Before NDVI:", f"{before_ndvi:.3f}" if before_ndvi is not None else "N/A")
    _row(pdf, "After NDVI:", f"{after_ndvi:.3f}" if after_ndvi is not None else "N/A")
    _row(pdf, "% Change:", f"{pct:.1f}%" if pct is not None else "N/A")
    pdf.ln(4)

    risk = report.get("risk_level", "UNKNOWN")
    color = RISK_COLORS.get(risk, RISK_COLORS["UNKNOWN"])
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(*color)
    pdf.cell(0, 10, f"Risk Level: {risk}", ln=True)
    pdf.ln(2)

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 7, report.get("note", ""))

    return bytes(pdf.output(dest="S"))
