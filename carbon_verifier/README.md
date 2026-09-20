# Carbon Credit / Afforestation Satellite Verifier

Ye tool kisi bhi jagah (aapka gaon/area, ya koi bhi carbon-credit project ka
location) ka satellite data se check karta hai ki wahan **vegetation/green
cover** waqt ke saath badha hai ya nahi — jisse pata chalta hai ki koi
plantation/afforestation claim genuine hai ya nahi.

**Data source**: Sentinel-2 satellite (free, Google Earth Engine ke through)

**Sab kuch ek hi UI se chalta hai — koi alag terminal command yaad nahi rakhni.**

---

## Setup (Ek Baar Karna Hai — 10 minute)

### Step 1: Python installed hona chahiye
Check karo terminal mein:
```
python3 --version
```
Agar nahi hai, to https://www.python.org/downloads/ se install karo.

### Step 2: Free Google Earth Engine Account Banao
1. https://code.earthengine.google.com/register par jaao
2. Apne Google account se sign in karo
3. "Unpaid usage" / "Academia & Research" / "Individual, non-commercial"
   option choose karo — ye **free** hai
4. Approval turant ya kuch ghanto mein mil jata hai

### Step 3: Required Packages Install Karo
Is folder ke andar terminal khol kar (ye ek hi baar karna hai):
```
pip install -r requirements.txt
```

### Step 4: Earth Engine Authenticate Karo (sirf ek baar)
```
earthengine authenticate
```
Ye browser khol dega — apne Google account se login karo jisse Earth Engine
register kiya tha. Login ke baad ek code milega, use terminal mein paste karo.

---

## Ab Bas Ye Ek Command Chalao (Har Baar)

```
streamlit run app.py
```

Browser mein UI khul jayegi (forest-background wala page). Isi ek jagah se
sab kuch hota hai:

### 🔍 Tab 1 — Single Location Check
1. Lat/Lon aur area (acres) daalo
2. Before period (plantation se pehle) aur after period (abhi) ke dates daalo
3. "Verify Now" dabao
4. Result, risk badge (LOW/MEDIUM/HIGH), aur **PDF download button** turant
   mil jayega

**Apna location coordinate kaise nikalein**: Google Maps kholo → apni jagah
par right-click karo → jo number aata hai (jaise `26.4499, 80.3319`) wahi
latitude, longitude hai.

### 📋 Tab 2 — Batch Check (Kai Projects Ek Saath)
1. Yahi UI mein "Sample CSV Template Download Karo" button se format samjho
2. Apni CSV excel/notepad mein banao (columns: name, lat, lon, acres,
   before_start, before_end, after_start, after_end)
3. Wahi CSV UI mein upload karo — preview dikhega
4. "Run Batch Verification" dabao
5. Sabka result table mein dikhega, aur waha se hi:
   - **Summary CSV** download karo
   - **Saari PDFs ek zip file** mein download karo

### 📧 Email Alerts (Ye Bhi UI Ke Andar Hi Hai)
Left sidebar mein "Email Alert Settings" hai:
1. Checkbox on karo "High risk milne par email bhejo"
2. Apna Gmail address, App Password, aur receiver email waha type karo
3. Gmail App Password kaise banayein: Google Account → Security → 2-Step
   Verification on karo → App Passwords → naya password generate karo (ye
   16-character wala password hota hai, normal Gmail password nahi)

Ab jab bhi (single ya batch) check mein koi **HIGH RISK** mile, email
automatically chala jayega — koi file edit ya alag script chalane ki
zaroorat nahi.

---

## Output Kya Milta Hai

- **Before NDVI / After NDVI**: Vegetation index — jitna zyada, utna healthy
  green cover
- **% Change**
- **Risk Level**: LOW / MEDIUM / HIGH RISK (color-coded badge)
- Ek short explanation note
- Downloadable **PDF report**
- (Batch mode mein) Summary CSV + saari PDFs ka zip

---

## Important Limitations (Honestly)

- **Resolution 10 meter/pixel hai** — matlab individual chhote trees nahi
  dikhenge, sirf overall area ka green-cover trend dikhega. 1-2 acre jaisi
  chhoti zameen ke liye result approximate hoga, bade areas (10+ acre) ke
  liye zyada reliable hoga.
- **Cloud cover** waali jagah/season mein kabhi accurate images nahi milti —
  agar "images used: 0" dikhe to date range ya location badal kar try karo.
- Ye tool sirf ek **starting signal/flag** deta hai — final/legal
  verification ke liye accredited human auditor hi zaroori hoga (Verra/Gold
  Standard jaise bodies ke rules ke hisaab se).
- NDVI kabhi-kabhi genuine reasons se bhi kam-zyada dikh sakta hai (jaise
  seasonal drought) — isliye "HIGH RISK" ka matlab "confirmed fraud" nahi,
  balki "further investigation zaroori hai."
- Email alerts sirf tabhi bhejenge jab app.py chal raha ho aur aapne check
  chalaya ho — ye background mein khud-ba-khud (bina aapke chalaye) nahi
  chalta. Agar automatic scheduled runs chahiye (daily/weekly bina UI khole),
  wo alag se OS-level scheduling (cron/Task Scheduler) maangega — abhi ke
  version mein ye शामिल nahi hai, sab kuch manual UI se hi trigger hota hai.

---

## Files Ka Matlab

- `app.py` — Poori UI (yahi chalana hai: `streamlit run app.py`)
- `carbon_verify.py` — Core logic (satellite fetch, NDVI, risk scoring)
- `report_utils.py` — PDF report banane ka code
- `batch_verify.py` — Batch logic + email function (app.py isko internally use karta hai)
- `requirements.txt` — Zaroori Python packages ki list

---

## 🌐 Hosting Karna (Taaki Koi Bhi Link Se Test Kar Sake)

Local `earthengine authenticate` sirf aapke laptop par kaam karta hai —
hosted server par interactive login nahi ho sakta. Isliye hosting ke liye
ek **Service Account** banana padega (ek baar ka setup), jisse server khud
authenticate ho jayega.

### Step 1: Google Cloud Service Account Banao
1. https://console.cloud.google.com/ par jaao (wahi Google account jisse
   Earth Engine register kiya tha)
2. Upar wahi project select karo jo Earth Engine registration ke time bana
   tha (ya naya banao)
3. Left menu → "IAM & Admin" → "Service Accounts" → "Create Service Account"
4. Naam do (jaise `carbon-verifier-bot`), "Create and Continue"
5. Role mein "Earth Engine Resource Viewer" ya "Editor" select karo, "Done"
6. Bani hui service account par click karo → "Keys" tab → "Add Key" →
   "Create new key" → **JSON** select karo → Download ho jayegi

7. Ab https://code.earthengine.google.com/register par (agar pehle se register
   nahi hai) isी service account ke email (jo JSON file ke andar
   `client_email` field mein hai) ko bhi Earth Engine access dena hoga:
   - https://signup.earthengine.google.com/#!/service_accounts par jaake
     apni service account email register karo

### Step 2: Code GitHub Par Daalo
1. GitHub par ek naya (private ya public) repository banao
2. Is folder ka pura content usme push karo (`.streamlit/secrets.toml` aur
   `alert_config.json` push MAT karna — `.gitignore` already ye handle
   karta hai)

### Step 3: Streamlit Community Cloud Par Deploy Karo
1. https://share.streamlit.io par jaao, GitHub account se login karo
2. "New app" → apna repository select karo → main file: `app.py`
3. "Deploy" dabao (2-3 minute lagega)

### Step 4: Secrets Add Karo (Yahi Sabse Important Step Hai)
1. Deployed app ke "Settings" (⚙️) → "Secrets" mein jaao
2. `.streamlit/secrets_example.toml` file kholo, us format mein apni
   **poori JSON key ka content** (jo Step 1 mein download hui thi) ek
   single-line string ke roop mein paste karo:
   ```
   EE_SERVICE_ACCOUNT_JSON = '''{"type": "service_account", "project_id": "...", ...}'''
   EE_PROJECT_ID = "your-project-id"
   ```
3. Save karo — app automatically restart ho jayega

Ab jo bhi is link ko kholega, wo bina kisi authenticate step ke seedha
tool use kar sakega — sirf UI dikhegi, koi setup nahi karna padega unko.

### Hosting Ke Baad Kya Dhyan Rakhein
- **Free Earth Engine tier ki daily quota hoti hai** — agar bahut log ek
  saath test karenge, kabhi rate-limit lag sakta hai (thodi der baad phir
  try karo)
- **Public link** kisi ke saath bhi share ho sakta hai — agar sirf kuch log
  test karein chahte ho, private GitHub repo + Streamlit app ko "private"
  rakho (Streamlit Cloud settings mein option hota hai)
- Email alerts wala sidebar ab bhi waisa hi hai — har tester apna khud ka
  email/password daal sakta hai, wo kisi ke saath share nahi hota
