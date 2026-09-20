"""
Carbon Credit / Afforestation Verifier
========================================
Ye tool kisi bhi location (lat, lon) ka "before" aur "after" satellite image
nikal kar vegetation (NDVI) change calculate karta hai, aur ek simple
risk score deta hai — taaki pata chale ki claimed plantation/afforestation
genuine hai ya nahi.

Data Source: Sentinel-2 (free, via Google Earth Engine)

Setup (ek baar karna hai):
1. https://code.earthengine.google.com/register par jaake FREE Earth Engine
   account banao (Google account se sign in karke "Unpaid/Noncommercial" use
   case choose karo — students/individuals ke liye free hai)
2. Terminal mein: pip install earthengine-api geemap
3. Terminal mein: earthengine authenticate   (browser khulega, login karo)
4. Fir ye script chalao.

Usage:
    python carbon_verify.py --lat 26.4499 --lon 80.3319 --acres 2 \
        --before-start 2019-01-01 --before-end 2019-12-31 \
        --after-start 2024-01-01 --after-end 2024-12-31

Agar dates na do, to default: "before" = 5 saal pehle ka poora saal,
"after" = pichhla poora saal.
"""

import argparse
import datetime
import json
import sys

try:
    import ee
except ImportError:
    print("ERROR: 'earthengine-api' install nahi hai.")
    print("   Chalao: pip install earthengine-api geemap")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Earth Engine Initialization
# ---------------------------------------------------------------------------
def init_earth_engine(project_id: str = None, service_account_json: str = None):
    """Earth Engine ko initialize karta hai.

    Do tareeke:
    1. Local use (aapka laptop): pehli baar `earthengine authenticate`
       terminal se chalao, fir ye function seedha kaam karega.
    2. Hosted/server use (jaise Streamlit Cloud): service_account_json do
       (ek Google Cloud service account ki JSON key, string ya dict form
       mein) — isse koi interactive login nahi chahiye, server khud-ba-khud
       authenticate ho jata hai. README mein "Hosting" section dekho.
    """
    try:
        if service_account_json:
            key_dict = (
                json.loads(service_account_json)
                if isinstance(service_account_json, str)
                else service_account_json
            )
            credentials = ee.ServiceAccountCredentials(
                key_dict["client_email"], key_data=json.dumps(key_dict)
            )
            ee.Initialize(credentials, project=project_id or key_dict.get("project_id"))
        elif project_id:
            ee.Initialize(project=project_id)
        else:
            ee.Initialize()
    except Exception as e:
        print("Earth Engine initialize nahi ho paya.")
        print("  Local use: pip install earthengine-api  →  earthengine authenticate")
        print("  Hosted use: service_account_json parameter do (README ka 'Hosting' section dekho)")
        print(f"\nOriginal error: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Geometry Helper — acres se ek chhota square/circle area banata hai
# ---------------------------------------------------------------------------
def geometry_from_point(lat: float, lon: float, acres: float) -> "ee.Geometry":
    """Diye gaye center point ke around, itne acres ka circle banata hai."""
    # 1 acre = 4046.86 sq meters. Circle area = pi * r^2
    area_sq_m = acres * 4046.86
    radius_m = (area_sq_m / 3.14159) ** 0.5
    point = ee.Geometry.Point([lon, lat])
    return point.buffer(radius_m)


# ---------------------------------------------------------------------------
# Cloud masking + NDVI calculation for Sentinel-2
# ---------------------------------------------------------------------------
def mask_clouds(image):
    """Sentinel-2 SR image mein se cloud/shadow pixels hata deta hai."""
    scl = image.select("SCL")
    # SCL classes: 3 = cloud shadow, 8/9 = cloud medium/high prob, 10 = thin cirrus
    mask = (
        scl.neq(3).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10))
    )
    return image.updateMask(mask)


def add_ndvi(image):
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("NDVI")
    return image.addBands(ndvi)


def get_mean_ndvi(geometry, start_date: str, end_date: str):
    """Diye gaye geometry aur date-range ke liye mean NDVI nikalta hai
    (Sentinel-2 ka median composite banaake, cloud-free)."""
    collection = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(geometry)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 40))
        .map(mask_clouds)
        .map(add_ndvi)
    )

    count = collection.size().getInfo()
    if count == 0:
        return None, 0

    composite = collection.median()
    ndvi_image = composite.select("NDVI")

    stats = ndvi_image.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=geometry,
        scale=10,
        maxPixels=1e9,
    ).getInfo()

    return stats.get("NDVI"), count


# ---------------------------------------------------------------------------
# Risk scoring logic
# ---------------------------------------------------------------------------
def compute_risk(before_ndvi: float, after_ndvi: float):
    """Simple rule-based risk scoring.
    NDVI range roughly: <0.2 = bare soil/no vegetation, 0.2-0.4 = sparse,
    0.4-0.6 = moderate, >0.6 = dense healthy vegetation."""

    if before_ndvi is None or after_ndvi is None:
        return "UNKNOWN", "Kaafi cloud-free images nahi mile is area/date-range ke liye."

    change = after_ndvi - before_ndvi
    pct_change = (change / max(before_ndvi, 0.01)) * 100

    if change <= 0.02:
        risk = "HIGH RISK"
        note = (
            "Vegetation mein koi meaningful badhaav nahi dikha. Agar yaha "
            "plantation/afforestation claim kiya gaya tha, to ye claim "
            "verify nahi ho raha satellite data se."
        )
    elif change < 0.1:
        risk = "MEDIUM RISK"
        note = (
            "Thoda sa vegetation increase dikha hai, lekin bada plantation "
            "claim hai to ye kaafi kam lagta hai. Manual verification "
            "recommended hai."
        )
    else:
        risk = "LOW RISK"
        note = (
            "Vegetation cover mein significant increase dikha hai — ye "
            "claim ke consistent lagta hai. Fir bhi final certification "
            "ke liye ground verification zaroori hai."
        )

    return risk, note, pct_change


def run_verification(lat, lon, acres, before_start, before_end,
                      after_start, after_end, project=None, service_account_json=None):
    """Streamlit UI (aur kisi bhi doosre Python code) se import karke seedha
    call karne ke liye ek clean wrapper function — CLI args ki zaroorat nahi."""
    init_earth_engine(project, service_account_json)
    geometry = geometry_from_point(lat, lon, acres)

    before_ndvi, before_count = get_mean_ndvi(geometry, before_start, before_end)
    after_ndvi, after_count = get_mean_ndvi(geometry, after_start, after_end)

    result = compute_risk(before_ndvi, after_ndvi)
    if len(result) == 3:
        risk, note, pct_change = result
    else:
        risk, note = result
        pct_change = None

    return {
        "location": {"lat": lat, "lon": lon},
        "area_acres": acres,
        "before_period": [before_start, before_end],
        "after_period": [after_start, after_end],
        "before_mean_ndvi": before_ndvi,
        "before_image_count": before_count,
        "after_mean_ndvi": after_ndvi,
        "after_image_count": after_count,
        "percent_change": pct_change,
        "risk_level": risk,
        "note": note,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Satellite-based afforestation/carbon-credit claim verifier"
    )
    parser.add_argument("--lat", type=float, required=True, help="Latitude")
    parser.add_argument("--lon", type=float, required=True, help="Longitude")
    parser.add_argument("--acres", type=float, required=True, help="Area in acres")
    parser.add_argument("--before-start", type=str, default=None)
    parser.add_argument("--before-end", type=str, default=None)
    parser.add_argument("--after-start", type=str, default=None)
    parser.add_argument("--after-end", type=str, default=None)
    parser.add_argument(
        "--project", type=str, default=None,
        help="Google Cloud project id (agar Earth Engine ko iski zaroorat pade)"
    )
    parser.add_argument("--output", type=str, default="report.json")
    args = parser.parse_args()

    today = datetime.date.today()
    if not args.after_start:
        args.after_start = f"{today.year - 1}-01-01"
    if not args.after_end:
        args.after_end = f"{today.year - 1}-12-31"
    if not args.before_start:
        args.before_start = f"{today.year - 6}-01-01"
    if not args.before_end:
        args.before_end = f"{today.year - 6}-12-31"

    print("Earth Engine initialize ho raha hai...")
    init_earth_engine(args.project)

    print(f"\nLocation: ({args.lat}, {args.lon}) | Area: {args.acres} acres")
    geometry = geometry_from_point(args.lat, args.lon, args.acres)

    print(f"'Before' period fetch ho raha hai: {args.before_start} to {args.before_end} ...")
    before_ndvi, before_count = get_mean_ndvi(geometry, args.before_start, args.before_end)
    print(f"  -> Mean NDVI: {before_ndvi}  (images used: {before_count})")

    print(f"'After' period fetch ho raha hai: {args.after_start} to {args.after_end} ...")
    after_ndvi, after_count = get_mean_ndvi(geometry, args.after_start, args.after_end)
    print(f"  -> Mean NDVI: {after_ndvi}  (images used: {after_count})")

    result = compute_risk(before_ndvi, after_ndvi)
    if len(result) == 3:
        risk, note, pct_change = result
    else:
        risk, note = result
        pct_change = None

    report = {
        "location": {"lat": args.lat, "lon": args.lon},
        "area_acres": args.acres,
        "before_period": [args.before_start, args.before_end],
        "after_period": [args.after_start, args.after_end],
        "before_mean_ndvi": before_ndvi,
        "after_mean_ndvi": after_ndvi,
        "percent_change": pct_change,
        "risk_level": risk,
        "note": note,
    }

    print("\n================ REPORT ================")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    print("=========================================")

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\nReport save ho gayi: {args.output}")


if __name__ == "__main__":
    main()
