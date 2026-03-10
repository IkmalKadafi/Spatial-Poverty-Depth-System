import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict
import folium
from branca.colormap import LinearColormap
import streamlit.components.v1 as components
import plotly.express as px
from streamlit_option_menu import option_menu

from backend.services import data_service, stats_service, model_service, geo_service

st.set_page_config(
    page_title="Poverty Depth Index Spatial Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header { font-size: 2.5rem; font-weight: bold; color: #1f77b4; margin-bottom: 0.5rem; }
    .sub-header { font-size: 1.2rem; color: #666; margin-bottom: 2rem; }
    .metric-card { background-color: #f0f2f6; padding: 1rem; border-radius: 0.5rem; text-align: center; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    page = option_menu(
        menu_title="Menu Navigasi",
        options=["Homepage", "Import & Exploration", "Prediction", "Simulation"],
        icons=["house", "cloud-upload", "graph-up-arrow", "sliders"],
        menu_icon="cast",
        default_index=0,
        styles={
            "container": {"padding": "0!important", "background-color": "#f0f2f6"},
            "icon": {"color": "#ff8c00", "font-size": "18px"},
            "nav-link": {"font-size": "16px", "text-align": "left", "margin": "0px", "color": "#262730", "--hover-color": "#d0d2d6"},
            "nav-link-selected": {"background-color": "#1f77b4", "color": "#ffffff"},
        },
    )
    st.divider()
    st.caption("© 2026 • Poverty Depth Index Spatial Analysis")


# ── PAGE: HOMEPAGE ────────────────────────────────────────────────────────────

if page == "Homepage":
    st.markdown('<div class="main-header">Poverty Depth Index Spatial Analysis</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Sistem Analitik Spasial untuk Provinsi Jawa Tengah</div>', unsafe_allow_html=True)
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        st.info("### Langkah 1: Import Data")
        st.write("""
        Mulailah dengan mengupload data Indeks Kedalaman Kemiskinan.

        **Fitur:**
        - Upload file CSV/Excel.
        - Eksplorasi Data Tabular.
        - Statistik Deskriptif Otomatis.
        - Visualisasi Awal (Peta & Grafik).
        """)
    with col2:
        st.success("### Langkah 2: Pemodelan")
        st.write("""
        Lakukan pemodelan menggunakan model yang tersedia.

        **Model Tersedia:**
        - Global Logistic Regression.
        - Geographically Weighted Logistic Regression (GWLR).
        - GWLR-Semiparametric.
        """)

    st.write("")
    with st.expander("Tentang Aplikasi Ini", expanded=True):
        st.write("""
        Aplikasi ini dikembangkan untuk mempermudah analisis spasial terkait kemiskinan di Jawa Tengah.
        Menggabungkan analisis statistik deskriptif dan pemodelan prediktif spasial untuk memberikan wawasan yang lebih mendalam.

        **Dikembangkan oleh:** Ikmal Thariq Kadafi
        """)


# ── PAGE: IMPORT & EXPLORATION ────────────────────────────────────────────────

elif page == "Import & Exploration":
    st.markdown('<div class="main-header">Import & Eksplorasi Data</div>', unsafe_allow_html=True)

    with st.sidebar:
        st.header("Import Data")
        uploaded_file = st.file_uploader(
            "Upload CSV atau Excel file",
            type=['csv', 'xlsx', 'xls'],
            help="Format: CSV, Excel (.xlsx, .xls) | Max: 200MB",
        )
        if uploaded_file is not None:
            try:
                temp_path = Path("backend/data/uploads") / uploaded_file.name
                temp_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path.write_bytes(uploaded_file.getbuffer())

                df = data_service.load_file(temp_path)
                st.session_state['data'] = df
                st.session_state['file_name'] = uploaded_file.name

                merge_stats = data_service.get_merge_statistics()
                st.success("✅ File uploaded successfully!")
                st.info(f"{len(df)} rows × {len(df.columns)} columns")
                if merge_stats:
                    st.info(f"Geodata merge: {merge_stats.get('matched_regions', 0)}/{merge_stats.get('total_geodata_regions', 0)} regions ({merge_stats.get('match_rate', 0)}%)")
            except Exception as e:
                st.error(f"❌ Error loading file: {e}")

        st.divider()
        selected_variable = None
        if 'data' in st.session_state:
            st.header("Filter Variabel")
            numeric_cols = data_service.get_numeric_columns()
            if numeric_cols:
                selected_variable = st.selectbox("Pilih Variabel:", options=numeric_cols, key='selected_variable')
            else:
                st.warning("No numeric columns found")
        else:
            st.info("Upload a file to start")

    if 'data' in st.session_state:
        df = st.session_state['data']

        st.header("Data Table Viewer")
        st.dataframe(df, use_container_width=True, height=400)

        if selected_variable:
            st.header("Statistik Deskriptif")
            try:
                stats = stats_service.get_statistics(selected_variable)
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Mean", f"{stats['mean']:.2f}")
                c2.metric("Median", f"{stats['median']:.2f}")
                c3.metric("Min", f"{stats['min']:.2f}")
                c4.metric("Max", f"{stats['max']:.2f}")
                c5.metric("Std Dev", f"{stats['std']:.2f}")
            except Exception as e:
                st.error(f"Error calculating statistics: {e}")

            st.header("Visualisasi Data")
            col_map, col_chart = st.columns([2, 1])

            with col_map:
                st.subheader("Choropleth Map - Persebaran Regional")
                try:
                    merged_gdf = data_service.get_merged_geodata()
                    if merged_gdf is not None and selected_variable in merged_gdf.columns:
                        gdf_vals = merged_gdf[merged_gdf[selected_variable].notna()].copy()
                        if len(gdf_vals) > 0:
                            bounds = gdf_vals.total_bounds
                            center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
                            m = folium.Map(location=center, zoom_start=8, tiles='OpenStreetMap')
                            colormap = LinearColormap(
                                colors=['#440154', '#2a788e', '#22a884', '#7ad151', '#fde724'],
                                vmin=float(gdf_vals[selected_variable].min()),
                                vmax=float(gdf_vals[selected_variable].max()),
                                caption=selected_variable,
                            )
                            folium.GeoJson(
                                gdf_vals,
                                style_function=lambda f: {
                                    'fillColor': colormap(f['properties'][selected_variable]) if f['properties'].get(selected_variable) else '#cccccc',
                                    'color': 'white', 'weight': 1, 'fillOpacity': 0.7,
                                },
                                tooltip=folium.GeoJsonTooltip(
                                    fields=['NAMOBJ', selected_variable],
                                    aliases=['Wilayah:', f'{selected_variable}:'],
                                    localize=True,
                                ),
                            ).add_to(m)
                            colormap.add_to(m)
                            m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
                            components.html(m._repr_html_(), height=500, scrolling=True)
                        else:
                            st.warning(f"No data available for variable '{selected_variable}'")
                    else:
                        st.warning("Geodata not available or variable not found")
                except Exception as e:
                    st.error(f"Error creating map: {e}")

            with col_chart:
                st.subheader("Top 10 Wilayah")
                try:
                    chart_data = stats_service.get_chart_data(selected_variable, top_n=10)
                    chart_df = pd.DataFrame({'Wilayah': chart_data['regions'], selected_variable: chart_data['values']})
                    fig = px.bar(
                        chart_df, y='Wilayah', x=selected_variable, orientation='h',
                        title=f'Top 10 Wilayah - {selected_variable}',
                        labels={'Wilayah': 'Kabupaten/Kota', selected_variable: selected_variable},
                        color=selected_variable, color_continuous_scale='Viridis',
                    )
                    fig.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Error creating chart: {e}")
    else:
        st.info("Silakan upload file CSV atau Excel di menu sidebar untuk memulai.")


# ── PAGE: PREDICTION ──────────────────────────────────────────────────────────

elif page == "Prediction":
    st.title("Pemodelan")

    with st.sidebar:
        st.divider()
        st.header("Konfigurasi Model")
        selected_model = st.selectbox("Pilih Model:", model_service.get_available_models())
        st.write("")
        run_button = st.button("Run Prediction", type="primary", use_container_width=True)

    if 'data' not in st.session_state:
        st.warning("⚠️ Silakan import data terlebih dahulu di halaman 'Import & Exploration'.")
    else:
        df = st.session_state['data']

        if run_button:
            with st.spinner(f"Menjalankan dengan {selected_model}..."):
                try:
                    predictions, probabilities = model_service.predict(df, selected_model)
                    st.session_state.update({'predictions': predictions, 'probabilities': probabilities, 'last_model': selected_model})
                    st.success("✅ Pemodelan selesai!")
                except Exception as e:
                    st.error(f"❌ Terjadi kesalahan saat pemodelan: {e}")

        if 'predictions' in st.session_state:
            preds = st.session_state['predictions']
            probs = st.session_state['probabilities']

            st.subheader("Hasil Pemodelan")
            st.info(f"Rata-rata Probabilitas: {probs.mean():.4f}")

            # ── Parameter Estimation Table ────────────────────────────────
            st.markdown("#### Tabel Pendugaan Parameter Model")

            filename = model_service.model_mapping.get(selected_model, selected_model)
            is_gwlr = filename == "gwlr_model.pkl"
            is_mgwlr = filename == "mgwlr_model.pkl"

            selected_region = None
            if is_gwlr or is_mgwlr:
                regions = model_service.get_region_order()
                if regions:
                    selected_region = st.selectbox(
                        "Pilih Kabupaten/Kota:",
                        options=regions,
                        key='param_region_select',
                    )
                    if is_mgwlr:
                        st.caption("ℹ️ Variabel global (Intercept, UMK, Industri, TPT) tidak berubah antar wilayah. Variabel lokal (DepRatio, RumahLayak, Sanitasi) mengikuti wilayah yang dipilih.")
                    else:
                        st.caption("ℹ️ Semua koefisien bersifat lokal dan mengikuti wilayah yang dipilih.")

            try:
                param_df = model_service.get_param_table(selected_model, region_name=selected_region)
                param_df_display = param_df.copy()
                for col in ['Koefisien', 'Standard Error', 'p-value']:
                    if col in param_df_display.columns:
                        param_df_display[col] = param_df_display[col].apply(
                            lambda x: f"{x:.6f}" if x is not None and not (isinstance(x, float) and x != x) else "—"
                        )
                st.dataframe(param_df_display, hide_index=True, use_container_width=True)
            except Exception as e:
                st.error(f"Gagal memuat tabel parameter: {e}")

            st.divider()

            col_map, col_metrics = st.columns([2, 1])

            def _make_folium_map(geojson, bounds, colormap, variable):
                center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
                m = folium.Map(location=center, zoom_start=8, tiles='OpenStreetMap')
                folium.GeoJson(
                    geojson,
                    style_function=lambda f: {
                        'fillColor': colormap(f['properties'][variable]) if f['properties'].get(variable) is not None else '#cccccc',
                        'color': 'white', 'weight': 1, 'fillOpacity': 0.7,
                    },
                    tooltip=folium.GeoJsonTooltip(fields=['NAMOBJ', variable], aliases=['Wilayah:', f'{variable}:'], localize=True),
                ).add_to(m)
                colormap.add_to(m)
                m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
                return m

            with col_map:
                # Robust region column detection with multiple fallback strategies
                region_col = data_service.region_column
                if not region_col:
                    _candidates = ['kabupaten_kota', 'kabupaten/kota', 'region', 'wilayah',
                                   'daerah', 'kota', 'kabupaten', 'namobj', 'nama']
                    region_col = next(
                        (c for c in df.columns if c.lower() in _candidates),
                        None
                    )
                if not region_col:
                    # Last resort: first object/string column
                    region_col = next(
                        (c for c in df.columns if df[c].dtype == object),
                        None
                    )

                if region_col:
                    df_viz = df.copy()
                    df_viz['Pred_Class_Logit'] = preds
                    df_viz['Pred_Prob_Logit'] = probs

                    try:
                        bounds = geo_service.get_geodata_info()['bounds']

                        st.markdown("### Peta Sebaran Kelas Prediksi")
                        with st.spinner("Membuat Peta Prediksi..."):
                            cdata = geo_service.create_choropleth_data(df_viz, 'Pred_Class_Logit', region_col)
                            cm_class = LinearColormap(colors=['#2c7bb6', '#d7191c'], vmin=0, vmax=1, caption='Pred_Class_Logit (0 vs 1)')
                            m1 = _make_folium_map(cdata['geojson'], bounds, cm_class, 'Pred_Class_Logit')
                            components.html(m1._repr_html_(), height=500)

                        st.write("")
                        st.markdown("### Peta Sebaran Probabilitas")
                        with st.spinner("Membuat Peta Probabilitas..."):
                            cdata_prob = geo_service.create_choropleth_data(df_viz, 'Pred_Prob_Logit', region_col)
                            cm_prob = LinearColormap(colors=['#ffffcc', '#a1dab4', '#41b6c4', '#2c7fb8', '#253494'], vmin=0, vmax=1, caption='Pred_Prob_Logit (Probabilitas)')
                            m2 = _make_folium_map(cdata_prob['geojson'], bounds, cm_prob, 'Pred_Prob_Logit')
                            components.html(m2._repr_html_(), height=500)
                    except Exception as e:
                        st.error(f"Gagal menampilkan peta: {e}")
                else:
                    st.warning("Tidak dapat mendeteksi kolom wilayah untuk peta.")


            with col_metrics:
                st.markdown("### Evaluasi Model")
                ground_truth_col = next((c for c in ['p1_encoded', 'P1_encoded'] if c in df.columns), None)
                if ground_truth_col:
                    try:
                        metrics = model_service.calculate_metrics(df[ground_truth_col], preds)
                        metrics_df = pd.DataFrame([{'Model': selected_model, **metrics}]).round(4)
                        st.dataframe(metrics_df, hide_index=True, use_container_width=True)
                    except Exception as e:
                        st.error(f"Gagal menghitung metrik: {e}")
                else:
                    st.warning("⚠️ Kolom `p1_encoded` tidak ditemukan. Evaluasi tidak tersedia.")

                st.divider()
                st.markdown("### Tabel Hasil Prediksi")
                region_col = data_service.region_column or 'Region'
                result_df = pd.DataFrame({'Pred Prob Logit': probs, 'Pred Class Logit': preds})

                detected_col = data_service.region_column
                if not detected_col:
                    candidates = ['kabupaten_kota', 'Kabupaten/Kota', 'region', 'wilayah', 'daerah']
                    detected_col = next((c for c in df.columns if c.lower() in [x.lower() for x in candidates]), None)

                if detected_col and detected_col in df.columns:
                    result_df.insert(0, 'Kabupaten/Kota', df[detected_col])
                elif df.index.dtype in ('object', 'string'):
                    result_df.insert(0, 'Kabupaten/Kota', df.index)
                else:
                    result_df.insert(0, 'Index', df.index)

                st.dataframe(result_df, use_container_width=True, height=500)

            st.divider()

            # Recommendations
            with st.container():
                st.markdown("### Rekomendasi Kebijakan")
                rec_df = pd.DataFrame({'Region': result_df[result_df.columns[0]], 'Class': result_df['Pred Class Logit']})
                total_regions = len(rec_df)
                class_1_count = (rec_df['Class'] == 1).sum()
                class_0_count = (rec_df['Class'] == 0).sum()
                class_1_pct = class_1_count / total_regions * 100 if total_regions > 0 else 0

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Wilayah", total_regions)
                c2.metric("Kelas 1 (Tinggi)", class_1_count, delta=f"{class_1_pct:.1f}%", delta_color="inverse")
                c3.metric("Kelas 0 (Rendah)", class_0_count, delta=f"{100 - class_1_pct:.1f}%" if total_regions > 0 else "0%", delta_color="normal")
                if class_1_count > class_0_count:
                    c4.metric("Status", "Perlu Perhatian", delta="Mayoritas Tinggi", delta_color="inverse")
                else:
                    c4.metric("Status", "Cukup Baik", delta="Mayoritas Rendah", delta_color="normal")

                st.write("")
                class_1_regions = rec_df[rec_df['Class'] == 1]['Region'].tolist()
                class_0_regions = rec_df[rec_df['Class'] == 0]['Region'].tolist()

                def _show_regions(regions):
                    cols = st.columns(5)
                    for i, r in enumerate(regions):
                        cols[i % 5].markdown(f"• {r}")

                with st.expander(f"Daerah Prioritas Tinggi ({class_1_count})", expanded=True):
                    if class_1_count > 0:
                        st.markdown("**Daftar Daerah:**")
                        _show_regions(class_1_regions)
                        st.markdown("---")
                        st.markdown("""#### Rekomendasi Intervensi
**1. Bantuan Sosial Intensif**
- Tingkatkan cakupan bansos dan validasi data penerima.
- Prioritaskan keluarga rentan dengan dependency ratio tinggi.

**2. Akses Layanan Dasar**
- Perbaiki infrastruktur rumah tidak layak huni (RTLH).
- Tingkatkan akses sanitasi dan air bersih.

**3. Ekonomi Lokal**
- Pelatihan kerja berbasis kompetensi lokal.
- Fasilitasi akses modal dan pasar untuk UMKM.""")
                    else:
                        st.success("✅ Tidak ada!")

                with st.expander(f"Daerah Status Baik ({class_0_count})", expanded=True):
                    if class_0_count > 0:
                        st.markdown("**Daftar Daerah:**")
                        _show_regions(class_0_regions)
                        st.markdown("---")
                        st.markdown("""#### Rekomendasi Pemeliharaan
**1. Pertahankan Program**
- Lanjutkan program efektif dan dokumentasikan praktik baik.

**2. Pencegahan**
- Monitor indikator dini untuk mencegah penurunan status.
- Siapkan jaring pengaman sosial adaptif.

**3. Peningkatan**
- Tingkatkan kualitas layanan publik digital.
- Dorong inovasi dan investasi hijau.""")
                    else:
                        st.warning("⚠️ Perlu perhatian!")

                with st.expander("Rekomendasi Umum", expanded=True):
                    st.markdown("""#### Monitoring & Evaluasi
**1. Update Data Berkala**: Lakukan pengumpulan data minimal 6 bulan sekali.
**2. Evaluasi Program**: Ukur dampak program terhadap indikator kemiskinan secara rutin.
**3. Kolaborasi**: Sinergi program antara pemerintah provinsi, kabupaten, dan desa.
**4. Analisis Spasial**: Manfaatkan peta kerawanan untuk targeting program yang lebih presisi.""")



# ── PAGE: SIMULATION ──────────────────────────────────────────────────────────

elif page == "Simulation":
    st.markdown('<div class="main-header">Simulation Process</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Simulasi prediksi fleksibel dengan parameter yang dapat dikonfigurasi</div>', unsafe_allow_html=True)
    st.divider()

    # ── Sidebar controls (shared across tabs) ─────────────────────────────────
    with st.sidebar:
        st.divider()
        st.header("Konfigurasi Simulasi")

        sim_model = st.selectbox(
            "Pilih Model:",
            model_service.get_available_models(),
            key='sim_model',
        )

        sim_filename = model_service.model_mapping.get(sim_model, sim_model)
        is_spatial   = sim_filename in ("gwlr_model.pkl", "mgwlr_model.pkl")

        sim_region = None
        if is_spatial:
            regions_list = model_service.get_region_order()
            sim_region   = st.selectbox("Pilih Wilayah:", regions_list, key='sim_region')
            if sim_filename == "mgwlr_model.pkl":
                st.caption("ℹ️ Koefisien lokal mengikuti wilayah yang dipilih.")
            else:
                st.caption("ℹ️ Semua koefisien bersifat lokal.")

        sim_threshold = st.slider(
            "Threshold Klasifikasi",
            min_value=0.0, max_value=1.0, value=0.5, step=0.01,
            help="Probabilitas ≥ threshold = Kelas 1 (Tinggi)",
            key='sim_threshold',
        )

    # ── Variable input sliders (used in Tab 1 & Tab 3) ────────────────────────
    VAR_CONFIG = {
        'DepRatio':   {"label": "Dependency Ratio (%)",         "min": 0.0,   "max": 100.0, "default": 45.0,   "step": 0.1,    "format": "%.1f"},
        'UMK':        {"label": "UMK (Rp)",                    "min": 1000000.0, "max": 5000000.0, "default": 2000000.0, "step": 50000.0, "format": "%.0f"},
        'Industri':   {"label": "Jumlah Industri (unit)",           "min": 0.0,   "max": 5000.0, "default": 500.0, "step": 10.0,   "format": "%.0f"},
        'TPT':        {"label": "Tingkat Pengangguran Terbuka (%)", "min": 0.0, "max": 20.0, "default": 5.0,   "step": 0.1,   "format": "%.1f"},
        'RumahLayak': {"label": "Rumah Layak Huni (%)",          "min": 0.0,   "max": 100.0, "default": 75.0,   "step": 0.1,   "format": "%.1f"},
        'Sanitasi':   {"label": "Sanitasi Layak (%)",            "min": 0.0,   "max": 100.0, "default": 75.0,   "step": 0.1,   "format": "%.1f"},
    }

    # ── TABS ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "Single Region What-If",
        "Bulk Prediction",
        "Model Comparison",
    ])

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 – Single Region What-If
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        st.markdown("### Simulasi What-If — Satu Wilayah")
        st.info(
            "Ubah nilai variabel X di bawah ini, lalu klik **Jalankan Simulasi**. "
            "Data akan distandardisasi otomatis sebelum dimasukkan ke model."
        )

        # Input sliders
        with st.form(key='sim_form_single'):
            st.markdown("#### Input Nilai Variabel (Skala Asli)")
            col_a, col_b = st.columns(2)
            input_vals: Dict[str, float] = {}

            var_items = list(VAR_CONFIG.items())
            for i, (var, cfg) in enumerate(var_items):
                target_col = col_a if i % 2 == 0 else col_b
                with target_col:
                    input_vals[var] = st.slider(
                        cfg["label"],
                        min_value=float(cfg["min"]),
                        max_value=float(cfg["max"]),
                        value=float(cfg["default"]),
                        step=float(cfg["step"]),
                        format=cfg["format"],
                        key=f'single_{var}',
                    )

            run_single = st.form_submit_button("Jalankan Simulasi", type="primary", use_container_width=True)

        if run_single:
            try:
                result = model_service.simulate_single_prediction(
                    input_values=input_vals,
                    model_name=sim_model,
                    region_name=sim_region,
                    threshold=sim_threshold,
                )
                st.session_state['sim_result_single'] = result
                st.session_state['sim_input_single']  = dict(input_vals)
            except Exception as e:
                st.error(f"❌ Simulasi gagal: {e}")

        if 'sim_result_single' in st.session_state:
            res   = st.session_state['sim_result_single']
            prob  = res['probability']
            pred  = res['pred_class']
            label = res['label']
            std_v = res['standardized_values']

            st.divider()
            st.markdown("### Hasil Simulasi")

            # Probability gauge using progress bar + metric
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                st.metric("Probabilitas Kemiskinan", f"{prob:.4f}")
                st.progress(prob)
            with c2:
                emoji = "🔴" if pred == 1 else "🟢"
                st.metric("Prediksi Kelas", f"{emoji} {label}")
            with c3:
                st.metric("Threshold Digunakan", f"{sim_threshold:.2f}")
                if is_spatial:
                    st.metric("Wilayah", sim_region or "—")

            # Standardized values table
            with st.expander("Nilai Setelah Standardisasi (yang masuk ke model)", expanded=False):
                std_df = pd.DataFrame.from_dict(
                    std_v, orient='index', columns=['Nilai Terstandarisasi']
                ).rename_axis('Variabel').reset_index()
                raw_s  = st.session_state['sim_input_single']
                std_df.insert(1, 'Nilai Asli', [raw_s.get(v, '-') for v in std_df['Variabel']])
                st.dataframe(std_df, hide_index=True, use_container_width=True)

            # Interpretation card
            st.divider()
            if pred == 1:
                st.error(
                    f"⚠️ **Interpretasi:** Berdasarkan nilai variabel yang diinput, wilayah ini "
                    f"diprediksi memiliki **Indeks Kedalaman Kemiskinan TINGGI** "
                    f"(probabilitas: {prob:.2%}) menggunakan model **{sim_model}**."
                )
            else:
                st.success(
                    f"✅ **Interpretasi:** Berdasarkan nilai variabel yang diinput, wilayah ini "
                    f"diprediksi memiliki **Indeks Kedalaman Kemiskinan RENDAH** "
                    f"(probabilitas: {prob:.2%}) menggunakan model **{sim_model}**."
                )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 – Bulk Prediction
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        st.markdown("### Bulk Prediction — Semua Wilayah")

        if 'data' not in st.session_state:
            st.warning("⚠️ Silakan import data terlebih dahulu di halaman **Import & Exploration**.")
        else:
            df_bulk = st.session_state['data']
            st.info(
                f"Dataset aktif: **{st.session_state.get('file_name', 'data')}** "
                f"({len(df_bulk)} baris × {len(df_bulk.columns)} kolom).  \n"
                "Data akan distandardisasi otomatis menggunakan scaler dari model."
            )

            run_bulk = st.button("Jalankan Bulk Prediction", type="primary", key='run_bulk')

            if run_bulk:
                with st.spinner(f"Menjalankan {sim_model} pada seluruh data..."):
                    try:
                        preds_b, probs_b = model_service.predict(df_bulk, sim_model)
                        # Apply custom threshold
                        preds_b = (probs_b >= sim_threshold).astype(int)
                        st.session_state['bulk_preds'] = preds_b
                        st.session_state['bulk_probs'] = probs_b
                        st.session_state['bulk_model'] = sim_model
                        st.success("✅ Prediksi selesai!")
                    except Exception as e:
                        st.error(f"❌ Prediksi gagal: {e}")

            if 'bulk_preds' in st.session_state:
                preds_b = st.session_state['bulk_preds']
                probs_b = st.session_state['bulk_probs']

                region_col_b = data_service.region_column
                result_bulk  = pd.DataFrame({'Probabilitas': probs_b.round(4), 'Kelas Prediksi': preds_b})
                if region_col_b and region_col_b in df_bulk.columns:
                    result_bulk.insert(0, 'Kabupaten/Kota', df_bulk[region_col_b].values)

                # Summary metrics
                c1, c2, c3, c4 = st.columns(4)
                n_tot  = len(preds_b)
                n_cls1 = int((preds_b == 1).sum())
                n_cls0 = int((preds_b == 0).sum())
                c1.metric("Total Wilayah", n_tot)
                c2.metric("Kelas 1 (Tinggi)", n_cls1, delta=f"{n_cls1/n_tot*100:.1f}%", delta_color="inverse")
                c3.metric("Kelas 0 (Rendah)", n_cls0, delta=f"{n_cls0/n_tot*100:.1f}%", delta_color="normal")
                c4.metric("Threshold", f"{sim_threshold:.2f}")

                st.divider()
                col_tbl, col_chart = st.columns([1, 1])

                with col_tbl:
                    st.markdown("#### Tabel Hasil")
                    def _highlight_class(row):
                        return ['background-color: #ffd6d6' if row['Kelas Prediksi'] == 1
                                else 'background-color: #d6ffd6'] * len(row)
                    st.dataframe(
                        result_bulk.style.apply(_highlight_class, axis=1),
                        hide_index=True, use_container_width=True, height=500,
                    )

                with col_chart:
                    st.markdown("#### Top 10 Probabilitas Tertinggi")
                    if 'Kabupaten/Kota' in result_bulk.columns:
                        top10 = result_bulk.nlargest(10, 'Probabilitas')
                        fig_bulk = px.bar(
                            top10, y='Kabupaten/Kota', x='Probabilitas', orientation='h',
                            color='Probabilitas', color_continuous_scale='Reds',
                            title='Top 10 Wilayah – Probabilitas Kemiskinan',
                        )
                        fig_bulk.update_layout(height=500, showlegend=False, yaxis={'categoryorder': 'total ascending'})
                        fig_bulk.add_vline(x=sim_threshold, line_dash='dash', line_color='black',
                                           annotation_text=f"Threshold={sim_threshold:.2f}")
                        st.plotly_chart(fig_bulk, use_container_width=True)

                    # Choropleth map if geodata available
                    try:
                        df_map = df_bulk.copy()
                        df_map['Prob_Simulasi'] = probs_b.values
                        if region_col_b:
                            bounds    = geo_service.get_geodata_info()['bounds']
                            cdata_sim = geo_service.create_choropleth_data(df_map, 'Prob_Simulasi', region_col_b)
                            cm_sim    = LinearColormap(
                                colors=['#ffffcc', '#fd8d3c', '#bd0026'],
                                vmin=0, vmax=1, caption='Probabilitas Kemiskinan',
                            )
                            center_b = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
                            m_bulk   = folium.Map(location=center_b, zoom_start=8, tiles='OpenStreetMap')
                            folium.GeoJson(
                                cdata_sim['geojson'],
                                style_function=lambda f: {
                                    'fillColor': cm_sim(f['properties']['Prob_Simulasi'])
                                                 if f['properties'].get('Prob_Simulasi') is not None else '#cccccc',
                                    'color': 'white', 'weight': 1, 'fillOpacity': 0.75,
                                },
                                tooltip=folium.GeoJsonTooltip(
                                    fields=['NAMOBJ', 'Prob_Simulasi'],
                                    aliases=['Wilayah:', 'Probabilitas:'],
                                    localize=True,
                                ),
                            ).add_to(m_bulk)
                            cm_sim.add_to(m_bulk)
                            m_bulk.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
                            st.markdown("#### Peta Probabilitas Kemiskinan")
                            components.html(m_bulk._repr_html_(), height=450)
                    except Exception:
                        pass  # Map is optional; skip silently

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 – Model Comparison
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        st.markdown("### Perbandingan Antar Model")
        st.info(
            "Input nilai variabel X yang sama akan dijalankan pada **ketiga model** sekaligus. "
            "Data akan distandardisasi sesuai scaler masing-masing model."
        )

        with st.form(key='sim_form_compare'):
            st.markdown("#### Input Nilai Variabel (Skala Asli)")

            # Region selector for spatial models
            regions_cmp = model_service.get_region_order()
            cmp_region  = st.selectbox(
                "Pilih Wilayah (untuk GWLR & MGWLR):",
                regions_cmp, key='cmp_region',
            )

            col_c, col_d = st.columns(2)
            cmp_vals: Dict[str, float] = {}
            var_items_cmp = list(VAR_CONFIG.items())
            for i, (var, cfg) in enumerate(var_items_cmp):
                target_col = col_c if i % 2 == 0 else col_d
                with target_col:
                    cmp_vals[var] = st.slider(
                        cfg["label"],
                        min_value=float(cfg["min"]),
                        max_value=float(cfg["max"]),
                        value=float(cfg["default"]),
                        step=float(cfg["step"]),
                        format=cfg["format"],
                        key=f'cmp_{var}',
                    )

            run_cmp = st.form_submit_button("Bandingkan Semua Model", type="primary", use_container_width=True)

        if run_cmp:
            cmp_results = []
            all_models  = model_service.get_available_models()
            with st.spinner("Menjalankan simulasi pada ketiga model..."):
                for mname in all_models:
                    mfile = model_service.model_mapping.get(mname, mname)
                    use_region = cmp_region if mfile in ("gwlr_model.pkl", "mgwlr_model.pkl") else None
                    try:
                        r = model_service.simulate_single_prediction(
                            input_values=cmp_vals,
                            model_name=mname,
                            region_name=use_region,
                            threshold=sim_threshold,
                        )
                        cmp_results.append({
                            'Model':        mname,
                            'Probabilitas': round(r['probability'], 4),
                            'Kelas':        r['pred_class'],
                            'Label':        r['label'],
                            'Wilayah Ref':  use_region or '—',
                        })
                    except Exception as e:
                        cmp_results.append({
                            'Model':        mname,
                            'Probabilitas': None,
                            'Kelas':        None,
                            'Label':        f'Error: {e}',
                            'Wilayah Ref':  use_region or '—',
                        })
            st.session_state['cmp_results'] = cmp_results

        if 'cmp_results' in st.session_state:
            cmp_res = st.session_state['cmp_results']
            cmp_df  = pd.DataFrame(cmp_res)

            st.divider()
            st.markdown("### Hasil Perbandingan")
            st.markdown(f"**Threshold:** `{sim_threshold:.2f}` | **Wilayah (GWLR/MGWLR):** `{cmp_region}`")

            def _highlight_cmp(row):
                if row['Kelas'] == 1:
                    return ['background-color: #ffd6d6'] * len(row)
                elif row['Kelas'] == 0:
                    return ['background-color: #d6ffd6'] * len(row)
                return [''] * len(row)

            st.dataframe(
                cmp_df[['Model', 'Probabilitas', 'Kelas', 'Label', 'Wilayah Ref']]
                     .style.apply(_highlight_cmp, axis=1),
                hide_index=True, use_container_width=True,
            )

            # Bar chart comparison
            valid_cmp = cmp_df.dropna(subset=['Probabilitas'])
            if not valid_cmp.empty:
                fig_cmp = px.bar(
                    valid_cmp, x='Model', y='Probabilitas',
                    color='Probabilitas', color_continuous_scale='RdYlGn_r',
                    title='Perbandingan Probabilitas Antar Model',
                    text='Probabilitas',
                )
                fig_cmp.update_traces(texttemplate='%{text:.4f}', textposition='outside')
                fig_cmp.add_hline(y=sim_threshold, line_dash='dash', line_color='black',
                                  annotation_text=f"Threshold = {sim_threshold:.2f}")
                fig_cmp.update_layout(height=400, xaxis_title='Model', yaxis_title='Probabilitas', yaxis_range=[0, 1.1])
                st.plotly_chart(fig_cmp, use_container_width=True)

            # Agreement analysis
            valid_classes = cmp_df['Kelas'].dropna()
            if len(valid_classes) > 1:
                st.divider()
                n_agree = int((valid_classes == valid_classes.iloc[0]).sum())
                if n_agree == len(valid_classes):
                    st.success(f"✅ **Konsensus:** Semua model sepakat — **{cmp_df.iloc[0]['Label']}**")
                else:
                    st.warning(
                        f"⚠️ **Tidak Konsensus:** Model berbeda pendapat. "
                        f"{n_agree}/{len(valid_classes)} model memprediksi kelas yang sama."
                    )


st.divider()
st.caption("© 2026 Sistem Analitik Data | Poverty Depth Index Spatial Analysis")
