import streamlit as st
import pandas as pd
from ultralytics import YOLO
from PIL import Image
import io
import plotly.express as px
from datetime import datetime, timedelta, timezone
import os
import re
import hashlib
import base64
import requests
import gspread
from google.oauth2.service_account import Credentials

# ============================================================================
# 1. HALAMAN & TAMPILAN ORIGINAL
# ============================================================================
st.set_page_config(page_title="VISONS - Visibility of Outlet Prediction System", layout="wide")
BACKGROUND_URL = "https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=1920&auto=format&fit=crop"
st.markdown(f"""
<style>
header[data-testid="stHeader"], .stAppHeader {{background: transparent !important;}}
.stApp {{background-image:url('{BACKGROUND_URL}');background-size:cover;background-position:center;background-attachment:fixed;filter:grayscale(30%);}}
div[data-testid="stVerticalBlock"] > div .element-container,
.stSelectbox,.stFileUploader,div[data-baseweb="select"],.metric-box {{
 background:rgba(45,50,60,.45)!important;backdrop-filter:blur(16px)!important;
 -webkit-backdrop-filter:blur(16px)!important;border:1px solid rgba(255,255,255,.12)!important;
 border-radius:12px!important;padding:10px;box-shadow:0 4px 30px rgba(0,0,0,.2);
}}
h1,h2,h3,p,span,label,.stMarkdown{{color:#FFF!important;}}
.main-title{{font-size:32px!important;font-weight:800;color:#FFF!important;margin-bottom:0;letter-spacing:1.5px;}}
.sub-title{{font-size:16px!important;color:#CCC!important;margin-bottom:35px;font-weight:500;}}
.metric-box{{padding:15px!important;border-left:5px solid #E60000!important;background:rgba(230,0,0,.05)!important;}}
.footer-text{{text-align:center;color:rgba(255,255,255,.5)!important;font-size:13px;margin-top:15px;}}
</style>
""", unsafe_allow_html=True)
st.markdown('<p class="main-title">PERTAMINA LUBRICANTS — VISIONS</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Visibility of Outlet Prediction System</p>', unsafe_allow_html=True)

# ============================================================================
# 2. GOOGLE SHEETS / GITHUB (SECRETS LAMA TIDAK PERLU DIUBAH)
# ============================================================================
BRANDS = ["PERTAMINA", "SHELL", "AHM", "MOTUL", "CASTROL", "FEDERAL", "TOP 1", "DELTALUBE", "YAMALUBE", "BM 1", "REPSOL", "OTHERS"]
COLUMNS = ["Date", "Territory", "Outlet Name", "Outlet ID", "Long (°)", "Lat (°)", "Outlet Type", "All Brand (Btl)"]
for _brand in BRANDS:
    COLUMNS += [f"{_brand} (Btl)", f"{_brand} (%)"]
COLUMNS += ["Avg Confidence Pred (%)", "Link Original Pic", "Link Predicted Pic"]
assert len(COLUMNS) == 35


def get_google_credentials():
    creds_dict = dict(st.secrets["google_creds"])
    raw_key = creds_dict["private_key"].strip().strip("'\"")
    if "\\n" in raw_key:
        raw_key = raw_key.replace("\\n", "\n")
    header, footer = "-----BEGIN PRIVATE KEY-----", "-----END PRIVATE KEY-----"
    if header in raw_key and footer in raw_key:
        core = "".join(raw_key.replace(header, "").replace(footer, "").split())
        raw_key = f"{header}\n{core}\n{footer}"
    creds_dict["private_key"] = raw_key
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)


def get_sheet():
    client = gspread.authorize(get_google_credentials())
    return client.open_by_key(st.secrets["google_sheets"]["spreadsheet_id"]).sheet1


def append_to_google_sheets(row_data):
    try:
        get_sheet().append_row(row_data, value_input_option="RAW")
        return True
    except Exception as exc:
        st.error(f"Gagal menyimpan Google Sheets: {exc}")
        return False


def append_batch_rows(rows):
    get_sheet().append_rows(rows, value_input_option="RAW")


def upload_to_google_drive(image_pil, filename, *args, **kwargs):
    """Kompatibel dengan nama fungsi lama; sebenarnya upload ke GitHub."""
    buf = io.BytesIO()
    image_pil.convert("RGB").save(buf, "JPEG", quality=85, optimize=True)
    owner, repo, branch = "mochfaqih", "pertamina-lubricants", "main"
    path = f"saved_images/{filename}"
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
    headers = {
        "Authorization": f"Bearer {st.secrets['github']['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    # Jika nama path identik sudah ada, manfaatkan file lama supaya tidak membuat commit duplikat.
