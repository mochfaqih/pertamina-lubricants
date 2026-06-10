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
# ... (Sisa kode ke bawah semuanya biarkan tetap sama seperti yang kamu miliki)
# ==============================================================================
# 1. KONFIGURASI HALAMAN & THEME SLATE GRAY PERFECT GLASSMORPHISM
# ==============================================================================
st.set_page_config(
    page_title="Pertamina Lubricants - AI Promo Audit",
    layout="wide"
)

# Background abstrak gradasi abu-abu gelap (slate gray) yang bersih dan netral
BACKGROUND_URL = "https://images.unsplash.com/photo-1557683316-973673baf926?q=80&w=1920&auto=format&fit=crop"

st.markdown(f"""
    <style>
    /* 1. Paksa ribbon/header bawaan Streamlit di bagian paling atas menjadi gelap/transparan */
    header[data-testid="stHeader"], .stAppHeader {{
        background-color: rgba(0, 0, 0, 0) !important;
        background: transparent !important;
    }}
    
    /* 2. Pasang background abstrak abu-abu ke seluruh web */
    .stApp {{
        background-image: url("{BACKGROUND_URL}");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        filter: grayscale(30%);
    }}
    
    /* 3. Efek kaca baru: Lebih terang, menyatu dengan abu-abu background (Seamless Glassmorphism) */
    div[data-testid="stVerticalBlock"] > div .element-container,
    .stSelectbox, .stFileUploader, div[data-baseweb="select"], .metric-box {{
        background: rgba(45, 50, 60, 0.45) !important; /* Warna abu-abu arang transparan yang menyatu dengan latar */
        backdrop-filter: blur(16px) !important;
        -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid rgba(255, 255, 255, 0.12) !important; /* Garis tepi putih tipis elegan */
        border-radius: 12px !important;
        padding: 10px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2); /* Shadow halus agar boks terlihat berdimensi */
    }}
    
    /* 4. Pengaturan warna teks utama agar kontras di atas warna gelap */
    h1, h2, h3, p, span, label, .stMarkdown {{
        color: #FFFFFF !important;
    }}
    
    /* 5. Kostumisasi teks judul utama bergaya modern corporate dashboard */
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
    
    /* 6. Modifikasi Metric Box agar bersinar neon merah tipis khas Pertamina */
    .metric-box {{ 
        padding: 15px !important; 
        border-left: 5px solid #E60000 !important;
        background: rgba(230, 0, 0, 0.05) !important;
    }}
    
    /* 7. Membuat teks footer berada di tengah bawah */
    .footer-text {{ 
        text-align: center; 
        color: rgba(255, 255, 255, 0.5) !important; 
        font-size: 13px; 
        margin-top: 15px; 
    }}
    </style>
""", unsafe_allow_html=True)

# Judul atas bersih dan minimalis tanpa logo
st.markdown('<p class="main-title">PERTAMINA LUBRICANTS — VISIONS</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Display Image Analyzer & Performance Evaluation</p>', unsafe_allow_html=True)

# ==============================================================================
# INTERFACES FUNGSI GOOGLE CLOUD STORAGE & SPREADSHEET
# ==============================================================================
def get_google_credentials():
    creds_dict = dict(st.secrets["google_creds"])
    
    # Ambil kunci mentah dari Streamlit Secrets
    raw_key = creds_dict["private_key"].strip()
    
    # Bersihkan jika ada tanda kutip luar yang tidak sengaja membungkus string
    raw_key = raw_key.strip("'\"")
    
    # Jika kunci diinput dengan spasi atau literal "\n", rapikan kembali
    if "\\n" in raw_key:
        raw_key = raw_key.replace("\\n", "\n")
        
    # Pastikan teks pembuka dan penutup kunci rahasia berada di barisnya sendiri secara bersih
    header = "-----BEGIN PRIVATE KEY-----"
    footer = "-----END PRIVATE KEY-----"
    
    if header in raw_key and footer in raw_key:
        # Ekstrak isi inti badan kunci rahasia di antara header dan footer
        core_body = raw_key.replace(header, "").replace(footer, "").strip()
        # Bersihkan spasi atau karakter baris baru liar di dalam badan kunci
        core_body = "".join(core_body.split())
        
        # Susun ulang secara rapi ke dalam format PEM standar dengan baris baru (\n) yang bersih
        raw_key = f"{header}\n{core_body}\n{footer}"
        
    creds_dict["private_key"] = raw_key
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    return Credentials.from_service_account_info(creds_dict, scopes=scopes)

# Tambahkan 'folder_id' sebagai argumen ketiga di dalam kurung fungsi ini
def upload_to_google_drive(image_pil, filename, *args, **kwargs):
    try:
        # 1. Konversi gambar PIL ke byte biner memori (.jpg)
        img_byte_arr = io.BytesIO()
        image_pil.save(img_byte_arr, format='JPEG')
        img_byte_arr.seek(0)
        image_bytes = img_byte_arr.getvalue()
        
        # 2. Ambil kredensial GitHub dari Streamlit Secrets
        github_token = st.secrets["github"]["token"]
        repo_owner = "mochfaqih"  # Username GitHub kamu
        repo_name = "pertamina-lubricants"  # Nama repositori kamu
        path_di_repo = f"saved_images/{filename}"  # Folder tujuan di GitHub
        
        # 3. Siapkan URL API GitHub dan Konversi gambar ke Base64 (Syarat GitHub API)
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path_di_repo}"
        base64_content = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            "message": f"Upload foto analisis: {filename} via Streamlit App",
            "content": base64_content,
            "branch": "main" # Pastikan nama branch utama kamu adalah main
        }
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 4. Eksekusi pengiriman (Auto-Commit & Push) langsung ke Repositori
        response = requests.put(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            # Jika sukses, GitHub akan membalas dengan info file, kita ambil download_url publiknya
            data = response.json()
            raw_url = data['content']['download_url']
            return raw_url
        else:
            st.error(f"GitHub API Error: {response.status_code} - {response.text}")
            return "Gagal Upload ke GitHub"
            
    except Exception as e:
        st.error(f"Gagal memproses penyimpanan GitHub: {str(e)}")
        return "Gagal Upload ke GitHub"
    
def append_to_google_sheets(row_data):
    try:
        creds = get_google_credentials()
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["google_sheets"]["spreadsheet_id"]).sheet1
        sheet.append_row(row_data)
        return True
    except Exception as e:
        st.error(f"Gagal menyimpan data ke Google Sheets: {str(e)}")
        return False

# ==============================================================================
# 2. LOAD DATA OUTLET LANGSUNG DARI FILE EXCEL (.XLSX) LOKAL
# ==============================================================================
@st.cache_data
def load_data_excel():
    try:
        df = pd.read_excel("data_outlet.xlsx", engine="openpyxl")
        df.columns = df.columns.str.strip()
        required_cols = ["Cluster Name", "Customer Name", "Customer ID", "Address", "Latitude", "Longitude"]
        return df[required_cols]
    except Exception as e:
        st.error(f"File 'data_outlet.xlsx' tidak ditemukan di folder proyek")
        st.stop()

df_outlet = load_data_excel()

# ==============================================================================
# 3. LOAD MODEL AI (best.pt)
# ==============================================================================
@st.cache_resource
def load_yolo_model():
    return YOLO("best.pt")

try:
    model = load_yolo_model()
except:
    st.error("Model 'best.pt' tidak ditemukan di direktori lokal.")
    st.stop()

# ==============================================================================
# 4. INITIALIZE SESSION STATE
# ==============================================================================
if "prediction_done" not in st.session_state:
    st.session_state.prediction_done = False
if "predicted_image" not in st.session_state:
    st.session_state.predicted_image = None
if "detected_boxes" not in st.session_state:
    st.session_state.detected_boxes = None
if "last_uploaded_file_name" not in st.session_state:
    st.session_state.last_uploaded_file_name = None

# ==============================================================================
# 5. STEP 1: IDENTIFIKASI OUTLET
# ==============================================================================
st.markdown("### ⚙️ Step 1: Identifikasi & Verifikasi Outlet")
col_select, col_map = st.columns([1, 1.2])

with col_select:
    list_territory = sorted(df_outlet["Cluster Name"].dropna().unique())
    selected_territory = st.selectbox("Pilih Territory / Cluster", list_territory)
    
    df_filtered = df_outlet[df_outlet["Cluster Name"] == selected_territory]
    
    list_outlet = sorted(df_filtered["Customer Name"].dropna().unique())
    selected_outlet_name = st.selectbox(
        "Pilih Nama Outlet / Toko", 
        list_outlet,
        index=0,
        placeholder="Ketik nama bengkel..."
    )
    
    outlet_details = df_filtered[df_filtered["Customer Name"] == selected_outlet_name].iloc[0]
    
    st.markdown("<div class='metric-box'>", unsafe_allow_html=True)
    st.markdown(f"**Customer ID :** `{int(outlet_details['Customer ID'])}`")
    st.markdown(f"**Alamat Terdaftar :** \n*{outlet_details['Address']}*")
    st.markdown("</div>", unsafe_allow_html=True)

with col_map:
    try:
        lat = float(outlet_details['Latitude'])
        lon = float(outlet_details['Longitude'])
        map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        st.map(map_data, zoom=14, use_container_width=True)
    except:
        st.warning("Koordinat GPS untuk outlet ini tidak valid atau kosong di master data.")

# ==============================================================================
# 6. STEP 2: DISPLAY IMAGE ANALYZER
# ==============================================================================
st.markdown("---")
st.markdown("### 📸 Step 2: Display Image Analyzer")

uploaded_file = st.file_uploader(
    "Ambil Foto Rak Display (Gunakan Kamera HP atau Upload dari Galeri)", 
    type=["jpg", "jpeg", "png"]
)

if uploaded_file is not None:
    if st.session_state.last_uploaded_file_name != uploaded_file.name:
        st.session_state.prediction_done = False
        st.session_state.predicted_image = None
        st.session_state.detected_boxes = None
        st.session_state.last_uploaded_file_name = uploaded_file.name

    image = Image.open(uploaded_file)
    image_placeholder = st.empty()
    
    if not st.session_state.prediction_done:
        image_placeholder.image(image, caption="Foto Berhasil Ditangkap - Siap Dianalisis", use_container_width=True)
    else:
        image_placeholder.image(st.session_state.predicted_image, caption="Hasil Plotting Analisis Brand & Objek AI", use_container_width=True)

    col_btn1, col_btn2 = st.columns([4, 1])
    with col_btn1:
        execute_predict = st.button("Jalankan Analisis AI Promo", type="primary", use_container_width=True)
    with col_btn2:
        reset_click = st.button("Reset Gambar", use_container_width=True)
        if reset_click:
            st.session_state.prediction_done = False
            st.session_state.predicted_image = None
            st.session_state.detected_boxes = None
            st.session_state.last_uploaded_file_name = None
            st.rerun()

    if execute_predict:
        with st.spinner("Model YOLOv8 sedang memproses struktur rak display..."):
            results = model.predict(image, conf=0.25)
            
            res_plotted = results[0].plot()
            st.session_state.predicted_image = Image.fromarray(res_plotted)
            st.session_state.detected_boxes = results[0].boxes
            st.session_state.prediction_done = True
            
            image_placeholder.image(st.session_state.predicted_image, caption="Hasil Plotting Analisis Brand & Objek AI", use_container_width=True)

    # ==============================================================================
    # 7. STEP 3: PERFORMANCE EVALUATION (GRAFIK, TABEL, & SUBMIT CLOUD)
    # ==============================================================================
    if st.session_state.prediction_done and st.session_state.detected_boxes is not None:
        boxes = st.session_state.detected_boxes
        total_botol = len(boxes)
        
        st.markdown("---")
        st.markdown("### 📊 Step 3: Performance Evaluation")
        st.markdown(f"**Total Keseluruhan Botol Terdeteksi:** `{total_botol}` botol")
        
        if total_botol > 0:
            class_names = model.names
            counts = {}
            for box in boxes:
                cls_id = int(box.cls[0])
                name = class_names[cls_id]
                counts[name] = counts.get(name, 0) + 1
            
            df_counts = pd.DataFrame(list(counts.items()), columns=["Brand Oli", "Jumlah (Botol)"])
            df_counts["Brand Oli"] = df_counts["Brand Oli"].str.upper()
            
            df_counts["Share of Shelf (%)"] = (df_counts["Jumlah (Botol)"] / total_botol) * 100
            df_counts["Share of Shelf (%)"] = df_counts["Share of Shelf (%)"].round(2)
            
            # Membuat string ringkasan sebaris untuk kolom deskripsi di Google Sheets
            summary_list = [f"{row['Brand Oli']}: {row['Jumlah (Botol)']} btl ({row['Share of Shelf (%)']}% )" for _, row in df_counts.iterrows()]
            rincian_analisis_str = ", ".join(summary_list)
            
            tab_grafik, tab_tabel = st.tabs(["Grafik Share of Shelf (SoS)", "Tabel Data Rincian"])
            
            with tab_grafik:
                fig = px.bar(
                    df_counts, 
                    x="Brand Oli", 
                    y="Share of Shelf (%)",
                    color="Brand Oli",
                    text=df_counts["Share of Shelf (%)"].apply(lambda x: f"{x}%"),
                    title=f"Analisis Share of Shelf (SoS) - {selected_outlet_name}",
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                    labels={"Share of Shelf (%)": "Persentase SoS (%)"}
                )
                fig.update_traces(textposition='outside', textfont_color='white')
                fig.update_layout(
                    showlegend=False, 
                    height=400, 
                    yaxis_range=[0, 110],
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color="white"
                )
                fig.update_xaxes(showgrid=False)
                fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
                st.plotly_chart(fig, use_container_width=True)
                
            with tab_tabel:
                df_tabel_tampil = df_counts.copy()
                df_tabel_tampil["Share of Shelf (%)"] = df_tabel_tampil["Share of Shelf (%)"].apply(lambda x: f"{x}%")
                st.dataframe(df_tabel_tampil, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            
            # TOMBOL OPERASIONAL CLOUD: SUBMIT GANDA (DRIVE & SPREADSHEETS)
            if st.button("🚀 Submit Final Data Audit ke Cloud", use_container_width=True):
                with st.spinner("Sedang memproses penyimpanan ganda ke Google Cloud Storage..."):
                    
                    # 1. Kirim file citra plotting AI ke Google Drive Folder
                    waktu_sekarang = datetime.now().strftime("%Y%m%d_%H%M%S")
                    nama_file_drive = f"AUDIT_{waktu_sekarang}_{selected_outlet_name.replace(' ', '_')}.jpg"
                    # KODE BARU YANG BENAR (Tambahkan st.secrets["google_drive"]["folder_id"])
                    # UBAH BAGIAN INI DI SEKITAR BARIS 396
                    link_foto_drive = upload_to_google_drive(st.session_state.predicted_image, nama_file_drive)
                    
                    # 2. Susun baris record data dan kirim ke baris terbawah Google Sheets
                    waktu_audit_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    baris_data_audit = [
                        waktu_audit_str,
                        selected_territory,
                        selected_outlet_name,
                        int(outlet_details['Customer ID']),
                        total_botol,
                        rincian_analisis_str,
                        link_foto_drive
                    ]
                    
                    sukses_simpan_sheet = append_to_google_sheets(baris_data_audit)
                    
                    if sukses_simpan_sheet and link_foto_drive != "Gagal Upload Gambar":
                        st.success(f"🔥 Sempurna! Data numerik berhasil tersimpan di Google Sheets dan dokumentasi visual aman di Google Drive!")
                        st.balloons()
                        
                        # Set balik state agar form siap menerima tugas analisis berikutnya
                        st.session_state.prediction_done = False
                        st.session_state.last_uploaded_file_name = None
                    else:
                        st.error("Sinkronisasi gagal. Periksa kembali jaringan atau otorisasi service account Anda.")
        else:
            st.warning("Analisis Selesai: Tidak ada botol oli yang berhasil diidentifikasi.")
else:
    st.session_state.prediction_done = False
    st.session_state.predicted_image = None
    st.session_state.detected_boxes = None
    st.session_state.last_uploaded_file_name = None
    st.info("Menunggu input gambar dari tim lapangan untuk memulai kalkulasi model.")

# ==============================================================================
# 8. FOOTER: LOGO LOKAL DI PALING BAWAH (TENGAH)
# ==============================================================================
st.markdown("---")
col_f1, col_f2, col_f3 = st.columns([2, 1, 2])
with col_f2:
    try:
        local_logo = Image.open("logo_ptpl.png")
        st.image(local_logo, use_container_width=True)
    except:
        pass

st.markdown('<p class="footer-text">Copyright | 39010378 | 2026</p>', unsafe_allow_html=True)