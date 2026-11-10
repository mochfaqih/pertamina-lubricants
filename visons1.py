import streamlit as st
import pandas as pd
from ultralytics import YOLO
from PIL import Image
import io
import plotly.express as px
from datetime import datetime
import os
# Library Tambahan untuk Integrasi Google Cloud
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import requests
import base64
# ============================================================================== 
# 1. KONFIGURASI HALAMAN & THEME SLATE GRAY PERFECT GLASSMORPHISM
# ============================================================================== 
st.set_page_config(
    page_title="VISONS - Visibility of Outlet Prediction System",
    layout="wide"
)

BACKGROUND_URL = "https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=1920&auto=format&fit=crop"
st.markdown(f"""
    <style>
    header[data-testid="stHeader"], .stAppHeader {{
        background-color: rgba(0, 0, 0, 0) !important;
        background: transparent !important;
    }}
    .stApp {{
        background-image: url("{BACKGROUND_URL}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        filter: grayscale(30%);
    }}
    div[data-testid="stVerticalBlock"] > div .element-container,
    .stSelectbox, .stFileUploader, div[data-baseweb="select"], .metric-box {{
        background: rgba(45, 50, 60, 0.45) !important;
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important;
        border-radius: 12px !important;
        padding: 10px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    }}
    h1, h2, h3, p, span, label, .stMarkdown {{
        color: #FFFFFF !important;
    }}
    .main-title {{
        font-size:32px !important;
        font-weight: 800;
        color: #FFFFFF !important;
        margin-bottom: 0px;
        letter-spacing: 1.5px;
    }}
    .sub-title {{
        font-size:16px !important;
        color: #CCCCCC !important;
        margin-bottom: 35px;
        font-weight: 500;
    }}
    .metric-box {{
        padding: 15px !important;
        border-left: 5px solid #E60000 !important;
        background: rgba(230, 0, 0, 0.05) !important;
    }}
    .footer-text {{
        text-align: center;
        color: rgba(255, 255, 255, 0.5) !important;
        font-size: 13px;
        margin-top: 15px;
    }}
    </style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">PERTAMINA LUBRICANTS — VISIONS</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Visibility of Outlet Prediction System</p>', unsafe_allow_html=True)

# ============================================================================== 
# INTERFACES FUNGSI GOOGLE CLOUD STORAGE & SPREADSHEET
# ============================================================================== 
def get_google_credentials():
    creds_dict = dict(st.secrets["google_creds"])
    raw_key = creds_dict["private_key"].strip()
    raw_key = raw_key.strip("'\"")
    if "\\n" in raw_key:
        raw_key = raw_key.replace("\\n", "\n")
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    if header in raw_key and footer in raw_key:
        core_body = raw_key.replace(header, "").replace(footer, "").strip()
        core_body = "".join(core_body.split())
        raw_key = f"{header}\n{core_body}\n{footer}"
    creds_dict["private_key"] = raw_key
