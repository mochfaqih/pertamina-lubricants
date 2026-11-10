
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
            target_brands = [
                "PERTAMINA", "SHELL", "AHM", "MOTUL", "CASTROL",
                "FEDERAL", "TOP 1", "DELTALUBE", "YAMALUBE", "BM 1", "REPSOL"
            ]
            counts = {b: 0 for b in target_brands}
            counts["OTHERS"] = 0
            conf_scores = []
            for box in boxes:
                cls_id = int(box.cls[0])
                name = class_names[cls_id].upper().strip()
                conf_val = float(box.conf[0])
                conf_scores.append(conf_val)
                if name in counts:
                    counts[name] += 1
                else:
                    counts["OTHERS"] += 1
            if len(conf_scores) > 0:
                avg_conf = (sum(conf_scores) / len(conf_scores)) * 100
                avg_confidence_str = f"{avg_conf:.2f}%"
            else:
                avg_confidence_str = "0.00%"
            df_counts = pd.DataFrame([{"Brand Oli": k, "Jumlah (Botol)": v} for k, v in counts.items() if v > 0])
            if not df_counts.empty:
                df_counts["Share of Shelf (%)"] = ((df_counts["Jumlah (Botol)"] / total_botol) * 100).round(2)

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
                    from datetime import datetime, timedelta
                    waktu_wib = datetime.utcnow() + timedelta(hours=7)
                    timestamp_file = waktu_wib.strftime("%Y%m%d_%H%M%S")
                    suffix_name = selected_outlet_name.replace(' ', '_')
                    nama_file_actual = f"ACTUAL_{timestamp_file}_{suffix_name}.jpg"
                    nama_file_predicted = f"PREDICTED_{timestamp_file}_{suffix_name}.jpg"
                    waktu_audit_sheets_str = waktu_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
                    link_actual_pic = upload_to_google_drive(st.session_state.original_image, nama_file_actual)
                    link_predicted_pic = upload_to_google_drive(st.session_state.predicted_image, nama_file_predicted)
                    row_data_audit = [
                        waktu_audit_sheets_str,
                        selected_territory,
                        selected_outlet_name,
                        int(outlet_details['Customer ID']),
                        float(outlet_details['Longitude']),
                        float(outlet_details['Latitude']),
                        "Bengkel" if "bengkel" in selected_outlet_name.lower() else "Toko",
                        total_botol,
                        counts["PERTAMINA"], f"{(counts['PERTAMINA']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["SHELL"], f"{(counts['SHELL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["AHM"], f"{(counts['AHM']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["MOTUL"], f"{(counts['MOTUL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["CASTROL"], f"{(counts['CASTROL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["FEDERAL"], f"{(counts['FEDERAL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["TOP 1"], f"{(counts['TOP 1']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["DELTALUBE"], f"{(counts['DELTALUBE']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["YAMALUBE"], f"{(counts['YAMALUBE']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["BM 1"], f"{(counts['BM 1']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["REPSOL"], f"{(counts['REPSOL']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        counts["OTHERS"], f"{(counts['OTHERS']/total_botol)*100:.2f}%" if total_botol > 0 else "0.00%",
                        avg_confidence_str,
                        link_actual_pic,
                        link_predicted_pic
                    ]
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
# 8. FITUR BARU SAJA: BATCH UPLOAD (KODE SINGLE DI ATAS TETAP DIPERTAHANKAN)
# ============================================================================== 
import hashlib
import re
from datetime import timedelta

BATCH_BRANDS = [
    "PERTAMINA", "SHELL", "AHM", "MOTUL", "CASTROL", "FEDERAL",
    "TOP 1", "DELTALUBE", "YAMALUBE", "BM 1", "REPSOL", "OTHERS"
]
