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
    page_title="VISONS - Visibility of Outlet Prediction System",
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
st.markdown('<p class="sub-title">Visibility of Outlet Prediction System</p>', unsafe_allow_html=True)

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
        repo_owner = "mochfaqih"  # Menyesuaikan kodinganmu
        repo_name = "pertamina-lubricants"  
        path_di_repo = f"saved_images/{filename}"  # Folder tujuan di GitHub
        
        # 3. Siapkan URL API GitHub dan Konversi gambar ke Base64
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path_di_repo}"
        base64_content = base64.b64encode(image_bytes).decode('utf-8')
        
        payload = {
            "message": f"Upload foto analisis: {filename} via Streamlit App",
            "content": base64_content,
            "branch": "main" 
        }
        
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        # 4. Eksekusi pengiriman (Auto-Commit & Push) langsung ke Repositori
        response = requests.put(url, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            data = response.json()
            raw_url = data['content']['download_url']
            return raw_url
        else:
            st.error(f"GitHub API Error: {response.status_code} - {response.text}")
            return "Gagal Upload Gambar"
            
    except Exception as e:
        st.error(f"Gagal memproses penyimpanan GitHub: {str(e)}")
        return "Gagal Upload Gambar"
    
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
st.markdown("### Step 1: Informasi & Verifikasi Outlet")
col_select, col_map = st.columns([1, 1.2])

with col_select:
    list_territory = sorted(df_outlet["Cluster Name"].dropna().unique())
    selected_territory = st.selectbox("Pilih Territory / Cluster", list_territory)
    
    df_filtered = df_outlet[df_outlet["Cluster Name"] == selected_territory]
    
    list_outlet = sorted(df_filtered["Customer Name"].dropna().unique())
    selected_outlet_name = st.selectbox(
        "Pilih Nama Bengkel / Toko", 
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
st.markdown("### Step 2: Display Image Analyzer")

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
    st.session_state.original_image = image
    image_placeholder = st.empty()
    
    if not st.session_state.prediction_done:
        image_placeholder.image(image, caption="Foto Berhasil Ditangkap - Siap Dianalisis", use_container_width=True)
    else:
        image_placeholder.image(st.session_state.predicted_image, caption="Hasil Plotting Analisis Brand & Objek", use_container_width=True)

    col_btn1, col_btn2 = st.columns([4, 1])
    with col_btn1:
        execute_predict = st.button("Mulai Prediksi", type="primary", use_container_width=True)
    with col_btn2:
        reset_click = st.button("Reset Gambar", use_container_width=True)
        if reset_click:
            st.session_state.prediction_done = False
            st.session_state.predicted_image = None
            st.session_state.detected_boxes = None
            st.session_state.last_uploaded_file_name = None
            st.rerun()

    if execute_predict:
        with st.spinner("Model VISONS sedang memproses struktur rak display..."):
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
        st.markdown("### Step 3: Performance Evaluation")
        st.markdown(f"**Total Keseluruhan Botol Terdeteksi:** `{total_botol}` botol")
        
        if total_botol > 0:
            class_names = model.names
            
            # Inisialisasi hitungan awal untuk semua list brand sesuai kolom Excel
            target_brands = [
                "PERTAMINA", "SHELL", "AHM", "MOTUL", "CASTROL", 
                "FEDERAL", "TOP 1", "DELTALUBE", "YAMALUBE", "BM 1", "REPSOL"
            ]
            
            counts = {b: 0 for b in target_brands}
            counts["OTHERS"] = 0
            
            # Penampung untuk menghitung average confidence score
            conf_scores = []
            
            for box in boxes:
                cls_id = int(box.cls[0])
                name = class_names[cls_id].upper().strip()
                
                # Ambil nilai confidence score dari deteksi YOLO (0.0 - 1.0)
                conf_val = float(box.conf[0])
                conf_scores.append(conf_val)
                
                if name in counts:
                    counts[name] += 1
                else:
                    counts["OTHERS"] += 1
            
            # --- Perhitungan Average Confidence Level ---
            if len(conf_scores) > 0:
                avg_conf = (sum(conf_scores) / len(conf_scores)) * 100
                avg_confidence_str = f"{avg_conf:.2f}%"
            else:
                avg_confidence_str = "0.00%"
                
            # Tarik data frame untuk visualisasi chart bawaan kodemu
            df_counts = pd.DataFrame([{"Brand Oli": k, "Jumlah (Botol)": v} for k, v in counts.items() if v > 0])
            if not df_counts.empty:
                df_counts["Share of Shelf (%)"] = ((df_counts["Jumlah (Botol)"] / total_botol) * 100).round(2)
            
            # [Bagian kode Render Grafik tab_grafik & tab_tabel bawaan kodemu tetap berjalan normal di sini]
            tab_grafik, tab_tabel = st.tabs(["Grafik Share of Shelf (SoS)", "Tabel Data Rincian"])
            with tab_grafik:
                if not df_counts.empty:
                    fig = px.bar(df_counts, x="Brand Oli", y="Share of Shelf (%)", color="Brand Oli",
                                 text=df_counts["Share of Shelf (%)"].apply(lambda x: f"{x}%"),
                                 title=f"Analisis Share of Shelf (SoS) - {selected_outlet_name}")
                    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color="white", showlegend=False)
                    st.plotly_chart(fig, use_container_width=True)
            with tab_tabel:
                if not df_counts.empty:
                    st.dataframe(df_counts, use_container_width=True, hide_index=True)

            st.markdown("---")
            
# ==================================================================
            # TOMBOL OPERASIONAL CLOUD: SUBMIT METADATA BERURUTAN (A - AI)
            # ==================================================================
            if st.button("Submit Final Data ke Cloud", use_container_width=True):
                with st.spinner("Sedang memproses pengiriman metadata brand dan penyimpanan ganda foto ke GitHub..."):
                    
                    # --- TAHAP 1: PENYIAPAN WAKTU & NAMA FILE (KONVERSI KE WIB) ---
                    from datetime import datetime, timedelta
                    
                    # Server cloud biasanya UTC, kita tambah 7 jam untuk mendapatkan WIB
                    waktu_wib = datetime.utcnow() + timedelta(hours=7)
                    
                    # Format untuk nama file gambar (tanpa karakter ilegal seperti titik dua atau spasi)
                    timestamp_file = waktu_wib.strftime("%Y%m%d_%H%M%S")
                    suffix_name = selected_outlet_name.replace(' ', '_')
                    
                    nama_file_actual = f"ACTUAL_{timestamp_file}_{suffix_name}.jpg"
                    nama_file_predicted = f"PREDICTED_{timestamp_file}_{suffix_name}.jpg"
                    
                    # Format teks rapi untuk kolom A di Google Sheets (Contoh: 2026-06-11 10:45:23 WIB)
                    waktu_audit_sheets_str = waktu_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
                    
                    # 2. Eksekusi Upload Dua Kali menggunakan def pilihanmu
                    link_actual_pic = upload_to_google_drive(st.session_state.original_image, nama_file_actual)
                    link_predicted_pic = upload_to_google_drive(st.session_state.predicted_image, nama_file_predicted)
                    
                    # 3. Penyusunan Baris Data Berurutan Sesuai Kolom Excel (A - AI)
                    row_data_audit = [
                        waktu_audit_sheets_str,                               # A: Date (Sekarang lengkap dengan Jam, Menit, Detik WIB)
                        selected_territory,                                   # B: Territory
                        selected_outlet_name,                                 # C: Outlet Name
                        int(outlet_details['Customer ID']),                  # D: Outlet ID
                        float(outlet_details['Longitude']),                   # E: Long
                        float(outlet_details['Latitude']),                    # F: Lat
                        "Bengkel" if "bengkel" in selected_outlet_name.lower() else "Toko", # G: Outlet Type
                        
                        total_botol,                                          # H: All Brand (Btl)
                        
                        # Pasangan berurutan: Jumlah Botol & % SoS untuk masing-masing Brand
                        counts["PERTAMINA"], f"{(counts['PERTAMINA']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%", # I-J
                        counts["SHELL"], f"{(counts['SHELL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",         # K-L
                        counts["AHM"], f"{(counts['AHM']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",             # M-N
                        counts["MOTUL"], f"{(counts['MOTUL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",         # O-P
                        counts["CASTROL"], f"{(counts['CASTROL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",     # Q-R
                        counts["FEDERAL"], f"{(counts['FEDERAL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",     # S-T
                        counts["TOP 1"], f"{(counts['TOP 1']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",         # U-V
                        counts["DELTALUBE"], f"{(counts['DELTALUBE']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%", # W-X
                        counts["YAMALUBE"], f"{(counts['YAMALUBE']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",   # Y-Z
                        counts["BM 1"], f"{(counts['BM 1']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",           # AA-AB
                        counts["REPSOL"], f"{(counts['REPSOL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",       # AC-AD
                        counts["OTHERS"], f"{(counts['OTHERS']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",       # AE-AF
                        
                        avg_confidence_str,                                   # AG: Avg Confidence Pred (%)
                        link_actual_pic,                                      # AH: Link Original Pic
                        link_predicted_pic                                    # AI: Link Predicted Pic
                    ]
                    
                    # 4. Tembak baris data rapi ke Google Sheets lewat def yang sudah kamu punya
                    sukses_simpan_sheet = append_to_google_sheets(row_data_audit)
                    
                    if sukses_simpan_sheet and "Gagal" not in link_actual_pic and "Gagal" not in link_predicted_pic:
                        st.success("Sempurna! Ekstraksi data berurutan per-brand dan penyimpanan ganda foto berhasil!")
                        st.balloons()
                        
                        st.session_state.prediction_done = False
                        st.session_state.last_uploaded_file_name = None
                    else:
                        st.error("Sinkronisasi gagal. Pastikan pengaturan token rahasia GitHub & Google Sheets milikmu valid.")
        else:
            st.warning("Analisis Selesai: Tidak ada objek botol oli yang berhasil diidentifikasi oleh model.")
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

st.markdown('<p class="footer-text">Credit | 39010378 | 2026</p>', unsafe_allow_html=True)