import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from urllib.parse import quote

def show_dashboard_tab():
    """Tab Dashboard"""
    # =================================================================
    # UPLOAD DATA SECTION
    # =================================================================
    st.markdown("### 📂 Upload Data")
    
    # 1. Ambil mode dari session_state (di-set di sidebar)
    mode = st.session_state.get("mode", "Single Data")

    if mode == "Compare Lama vs Baru":
        st.markdown("#### 📂 Upload Semua File (Income & Pesanan, Lama & Baru)")
        uploaded_files = st.file_uploader(
            "Upload 4 file sekaligus (income & pesanan, lama & baru)", 
            type=["xlsx", "xls"], 
            accept_multiple_files=True, 
            key="compare_multi"
        )

        import re
        # Regex pattern
        income_pattern = re.compile(r'income[_-](\d{8,})', re.IGNORECASE)
        pesanan_pattern = re.compile(r'selesai[ _-]pesanan[-_]?([\d-]+)', re.IGNORECASE)

        detected = {
            'income': [],  # (file, tanggal)
            'pesanan': []  # (file, tanggal)
        }
        for file in uploaded_files:
            fname = file.name.lower()
            income_match = income_pattern.search(fname)
            pesanan_match = pesanan_pattern.search(fname)
            if income_match:
                tanggal = income_match.group(1).replace('-', '')
                detected['income'].append((file, tanggal))
            elif pesanan_match:
                tanggal = pesanan_match.group(1).replace('-', '')
                detected['pesanan'].append((file, tanggal))

        # Urutkan berdasarkan tanggal (lama ke baru)
        for key in detected:
            detected[key].sort(key=lambda x: x[1])

        # Assign ke session_state dan tampilkan hasil deteksi
        if len(detected['pesanan']) == 2:
            try:
                df_old_pesanan = pd.read_excel(detected['pesanan'][0][0], header=0, skiprows=[1])
                df_old_pesanan.columns = [str(c).strip() for c in df_old_pesanan.columns]
                st.session_state.old_pesanan_data = df_old_pesanan
                df_new_pesanan = pd.read_excel(detected['pesanan'][1][0], header=0, skiprows=[1])
                df_new_pesanan.columns = [str(c).strip() for c in df_new_pesanan.columns]
                st.session_state.pesanan_data = df_new_pesanan
                st.success(f"✅ Pesanan Lama: {detected['pesanan'][0][0].name}")
                st.success(f"✅ Pesanan Baru: {detected['pesanan'][1][0].name}")
            except Exception as e:
                st.error(f"❌ Gagal memuat file pesanan: {e}")
        if len(detected['income']) == 2:
            try:
                df_old_income = pd.read_excel(detected['income'][0][0], header=0)
                df_old_income.columns = [str(c).strip() for c in df_old_income.columns]
                st.session_state.old_income_data = df_old_income
                df_new_income = pd.read_excel(detected['income'][1][0], header=0)
                df_new_income.columns = [str(c).strip() for c in df_new_income.columns]
                st.session_state.income_data = df_new_income
                st.success(f"✅ Income Lama: {detected['income'][0][0].name}")
                st.success(f"✅ Income Baru: {detected['income'][1][0].name}")
            except Exception as e:
                st.error(f"❌ Gagal memuat file income: {e}")

        # Info jika file kurang
        if uploaded_files and (len(detected['pesanan']) < 2 or len(detected['income']) < 2):
            st.warning("⚠️ Pastikan upload 2 file income & 2 file pesanan dengan nama yang benar!\nContoh: income_20250723xxxx.xlsx, Selesai pesanan-2025-07-23-xx_xx.xlsx")

    else:  # Single Data
        col1, col2 = st.columns(2)
        with col1:
            st.markdown('<div class="upload-section">', unsafe_allow_html=True)
            st.markdown("**📊 Pesanan Selesai**")
            pesanan_file = st.file_uploader(
                "Unggah file Excel dengan pesanan selesai",
                type=['xlsx', 'xls'],
                key="pesanan_single",
                help="File harus berisi data pesanan dengan kolom 'Order Status'"
            )
            if pesanan_file:
                try:
                    df = pd.read_excel(pesanan_file, header=0, skiprows=[1])
                    df.columns = [str(c).strip() for c in df.columns]
                    st.session_state.pesanan_data = df
                    st.markdown(f'<div class="status-success">✅ Pesanan dimuat: {len(df):,} baris</div>', unsafe_allow_html=True)
                    with st.expander("📋 Pratinjau"):
                        st.dataframe(df.head(), use_container_width=True)
                except Exception as e:
                    st.markdown(f'<div class="status-error">❌ Kesalahan memuat file: {str(e)}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="upload-section">', unsafe_allow_html=True)
            st.markdown("**💰 Data Pendapatan**")
            income_file = st.file_uploader(
                "Unggah file Excel dengan data pendapatan",
                type=['xlsx', 'xls'],
                key="income_single",
                help="File harus berisi kolom 'Order/adjustment ID' dan 'Total settlement amount'"
            )
            if income_file:
                try:
                    df = pd.read_excel(income_file, header=0)
                    df.columns = [str(c).strip() for c in df.columns]
                    st.session_state.income_data = df
                    st.markdown(f'<div class="status-success">✅ Pendapatan dimuat: {len(df):,} baris</div>', unsafe_allow_html=True)
                    with st.expander("📋 Pratinjau"):
                        st.dataframe(df.head(), use_container_width=True)
                except Exception as e:
                    st.markdown(f'<div class="status-error">❌ Kesalahan memuat file: {str(e)}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    
    # =================================================================
    # DASHBOARD METRICS SECTION
    # =================================================================
    if st.session_state.summary_data is not None:
        st.markdown("### 📊 Dasbor Kinerja")
        
        # Hitung metrik kunci
        # Gunakan Order/adjustment ID sebagai primary key (sesuai dengan logika baru)
        unique_orders = st.session_state.merged_data.drop_duplicates(subset=['Order/adjustment ID'])
        total_orders = unique_orders['Order/adjustment ID'].nunique()
        total_revenue = unique_orders['Total settlement amount'].sum()
        total_cost = st.session_state.summary_data['Total Cost'].sum()
        total_profit = total_revenue - total_cost
        total_share_60 = total_profit * 0.6
        total_share_40 = total_profit * 0.4
        avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
        profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
        
        # Metrik utama
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                label="💼 Total Pesanan",
                value=f"{total_orders:,}",
                delta=f"AOV: Rp {avg_order_value:,.0f}"
            )
        
        with col2:
            st.metric(
                label="💰 Total Pendapatan",
                value=f"Rp {total_revenue:,.0f}",
                delta=f"Biaya: Rp {total_cost:,.0f}"
            )
        
        with col3:
            st.metric(
                label="📈 Total Profit",
                value=f"Rp {total_profit:,.0f}",
                delta=f"{profit_margin:.1f}% margin"
            )
        
        with col4:
            st.metric(
                label="🤝 Pembagian Bagian",
                value=f"60%: Rp {total_share_60:,.0f}",
                delta=f"40%: Rp {total_share_40:,.0f}"
            )
        
        # AI Summary
        st.markdown("---")
        if st.button("📄 Tampilkan Ringkasan (Copy ke ChatGPT)", type="secondary"):
            if st.session_state.summary_data is not None:
                # Import app dari data_processor
                from data_processor import IncomeApp
                app = IncomeApp()
                summary_text = app.generate_ai_summary(st.session_state.summary_data)
                st.markdown("### 📋 Ringkasan Teks")
                st.code(summary_text, language="text")
            else:
                st.warning("⚠️ Proses data terlebih dahulu.")
        
        # Bagian grafik
        st.markdown("---")
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("**📊 10 Produk Teratas berdasarkan Pendapatan**")
            
            top_revenue = st.session_state.summary_data.nlargest(10, 'Revenue')
            
            fig = px.bar(
                top_revenue,
                x='Revenue',
                y='Product Name',
                orientation='h',
                title="Pendapatan per Produk",
                color='Profit Margin %',
                color_continuous_scale='RdYlGn',
                text='Revenue'
            )
            
            fig.update_layout(
                height=400,
                showlegend=False,
                yaxis={'categoryorder': 'total ascending'}
            )
            
            fig.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        with chart_col2:
            st.markdown('<div class="chart-container">', unsafe_allow_html=True)
            st.markdown("**📈 Distribusi Margin Profit**")
            
            fig = px.histogram(
                st.session_state.summary_data,
                x='Profit Margin %',
                nbins=20,
                title="Distribusi Margin Profit",
                color_discrete_sequence=['#667eea']
            )
            
            fig.add_vline(
                x=st.session_state.summary_data['Profit Margin %'].mean(),
                line_dash="dash",
                line_color="red",
                annotation_text=f"Rata-rata: {st.session_state.summary_data['Profit Margin %'].mean():.1f}%"
            )
            
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Analisis terperinci
        st.markdown("---")
        st.markdown("### 🔍 Analisis Terperinci")
        
        analysis_col1, analysis_col2 = st.columns(2)
        
        with analysis_col1:
            st.markdown("**🏆 Performa Teratas**")
            
            top_profit = st.session_state.summary_data.nlargest(5, 'Profit')[['Product Name', 'Profit', 'Profit Margin %']]
            top_profit['Profit'] = top_profit['Profit'].apply(lambda x: f"Rp {x:,.0f}")
            top_profit['Profit Margin %'] = top_profit['Profit Margin %'].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(top_profit, use_container_width=True, hide_index=True)
        
        with analysis_col2:
            st.markdown("**⚠️ Produk Margin Rendah**")
            
            low_margin = st.session_state.summary_data.nsmallest(5, 'Profit Margin %')[['Product Name', 'Profit', 'Profit Margin %']]
            low_margin['Profit'] = low_margin['Profit'].apply(lambda x: f"Rp {x:,.0f}")
            low_margin['Profit Margin %'] = low_margin['Profit Margin %'].apply(lambda x: f"{x:.1f}%")
            
            st.dataframe(low_margin, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Upload dan proses data Anda terlebih dahulu untuk melihat dashboard")

def show_cost_management_tab():
    """Tab Cost Management"""
    # =================================================================
    # UPLOAD DATA SECTION (jika belum ada data)
    # =================================================================
    if st.session_state.pesanan_data is None or st.session_state.income_data is None:
        st.markdown("### 📂 Upload Data (Diperlukan untuk Manajemen Biaya)")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📊 Pesanan Selesai**")
            pesanan_file = st.file_uploader(
                "Unggah file Excel dengan pesanan selesai",
                type=['xlsx', 'xls'],
                key="pesanan_cost",
                help="File harus berisi data pesanan dengan kolom 'Order Status'"
            )
            if pesanan_file:
                try:
                    df = pd.read_excel(pesanan_file, header=0, skiprows=[1])
                    df.columns = [str(c).strip() for c in df.columns]
                    st.session_state.pesanan_data = df
                    st.success(f"✅ Pesanan dimuat: {len(df):,} baris")
                except Exception as e:
                    st.error(f"❌ Kesalahan memuat file: {str(e)}")

        with col2:
            st.markdown("**💰 Data Pendapatan**")
            income_file = st.file_uploader(
                "Unggah file Excel dengan data pendapatan",
                type=['xlsx', 'xls'],
                key="income_cost",
                help="File harus berisi kolom 'Order/adjustment ID' dan 'Total settlement amount'"
            )
            if income_file:
                try:
                    df = pd.read_excel(income_file, header=0)
                    df.columns = [str(c).strip() for c in df.columns]
                    st.session_state.income_data = df
                    st.success(f"✅ Pendapatan dimuat: {len(df):,} baris")
                except Exception as e:
                    st.error(f"❌ Kesalahan memuat file: {str(e)}")
        
        st.markdown("---")
        st.info("ℹ️ Upload kedua file terlebih dahulu untuk melihat manajemen biaya")
        return

    # =================================================================
    # COST MANAGEMENT SECTION
    # =================================================================
    st.markdown("### 💸 Manajemen Biaya")
    
    # Import app dari data_processor
    from data_processor import IncomeApp
    app = IncomeApp()
    
    # Bilah aksi cepat
    action_col1, action_col2, action_col3 = st.columns(3)
    
    with action_col1:
        uploaded_file = st.file_uploader(
            "📁 Impor Biaya (JSON)",
            type=['json'],
            key="import_cost",
            help="Upload file JSON hasil export sebelumnya",
            label_visibility="collapsed"
        )
        
        if uploaded_file is not None:
            try:
                import json
                imported_data = json.load(uploaded_file)
                if isinstance(imported_data, dict):
                    # Validasi format
                    valid_data = {k: float(v) for k, v in imported_data.items() 
                                if isinstance(v, (int, float)) and v >= 0}
                    
                    # Konfirmasi import
                    if st.button(f"✅ Import {len(valid_data)} produk?", type="primary", key="confirm_import"):
                        st.session_state.cost_data.update(valid_data)
                        app.save_cost_data(st.session_state.cost_data)
                        st.success(f"✅ {len(valid_data)} biaya produk berhasil diimport!")
                        st.rerun()
                else:
                    st.error("❌ Format file tidak valid. Harus berupa key-value JSON.")
                    
            except json.JSONDecodeError:
                st.error("❌ File bukan JSON yang valid")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
    
    with action_col2:
        if st.button("📤 Ekspor Biaya", help="Unduh data biaya saat ini"):
            import json
            from datetime import datetime
            st.download_button(
                label="💾 Unduh JSON",
                data=json.dumps(st.session_state.cost_data, ensure_ascii=False, indent=2),
                file_name=f"product_costs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with action_col3:
        if st.button("🔄 Segarkan Data", help="Muat ulang data biaya dari file"):
            st.session_state.cost_data = app.load_cost_data()
            st.rerun()
    
    st.markdown("---")
    
    # Form manajemen biaya
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("**Tambah/Edit Biaya Produk**")
        
        # Pemilihan produk dengan pencarian
        if st.session_state.pesanan_data is not None:
            products = sorted(st.session_state.pesanan_data['Product Name'].astype(str).unique())
            selected_product = st.selectbox(
                "🔍 Pilih Produk",
                options=products,
                key="product_select",
                help="Cari dan pilih produk dari data pesanan Anda"
            )
        else:
            selected_product = st.text_input(
                "📝 Nama Produk",
                key="product_input",
                help="Masukkan nama produk secara manual"
            )
        
        # Input biaya dengan nilai saat ini
        current_cost = st.session_state.cost_data.get(selected_product, 0.0)
        cost_input = st.number_input(
            "💰 Biaya per Unit",
            min_value=0.0,
            value=current_cost,
            format="%.2f",
            key="cost_input",
            help=f"Biaya saat ini: Rp {current_cost:,.2f}"
        )
        
        # Tombol aksi
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        
        with btn_col1:
            if st.button("💾 Simpan Biaya", type="primary"):
                if selected_product and cost_input >= 0:
                    st.session_state.cost_data[selected_product] = cost_input
                    app.save_cost_data(st.session_state.cost_data)
                    st.success(f"✅ Biaya disimpan untuk {selected_product}")
                    st.rerun()
                else:
                    st.warning("⚠️ Masukkan produk dan biaya yang valid")
        
        with btn_col2:
            if st.button("🗑️ Hapus Biaya", type="secondary"):
                if selected_product in st.session_state.cost_data:
                    del st.session_state.cost_data[selected_product]
                    app.save_cost_data(st.session_state.cost_data)
                    st.success(f"✅ Biaya dihapus untuk {selected_product}")
                    st.rerun()
                else:
                    st.warning("⚠️ Produk tidak ditemukan dalam data biaya")
        
        with btn_col3:
            if st.button("🔄 Bersihkan Formulir"):
                st.rerun()
    
    with col2:
        st.markdown("**📊 Statistik Biaya**")
        
        if st.session_state.cost_data:
            total_products = len(st.session_state.cost_data)
            avg_cost = sum(st.session_state.cost_data.values()) / total_products
            min_cost = min(st.session_state.cost_data.values())
            max_cost = max(st.session_state.cost_data.values())
            
            st.metric("📦 Total Produk", total_products)
            st.metric("💰 Rata-rata Biaya", f"Rp {avg_cost:,.0f}")
            st.metric("📉 Biaya Minimum", f"Rp {min_cost:,.0f}")
            st.metric("📈 Biaya Maksimum", f"Rp {max_cost:,.0f}")
        else:
            st.info("Tidak ada data biaya")
    
    # Tabel data biaya
    st.markdown("---")
    st.markdown("### 📋 Data Biaya Saat Ini")
    
    if st.session_state.cost_data:
        # Cari dan filter
        search_term = st.text_input("🔍 Cari produk", placeholder="Ketik untuk mencari...")
        
        cost_df = pd.DataFrame(
            list(st.session_state.cost_data.items()),
            columns=["Product Name", "Cost per Unit"]
        )
        
        if search_term:
            cost_df = cost_df[cost_df['Product Name'].str.contains(search_term, case=False, na=False)]
        
        cost_df = cost_df.sort_values("Product Name")
        
        # Format untuk tampilan
        cost_display = cost_df.copy()
        cost_display['Cost per Unit'] = cost_display['Cost per Unit'].apply(lambda x: f"Rp {x:,.0f}")
        
        st.dataframe(cost_display, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Tidak ada data biaya. Tambahkan beberapa biaya produk untuk memulai.")

def show_analytics_tab():
    """Tab Analisis Lanjutan"""
    if st.session_state.summary_data is not None:
        st.markdown("### 📊 Analisis Lanjutan")
        
        # Pemilihan grafik
        chart_type = st.selectbox(
            "📈 Pilih Jenis Grafik",
            ["Pendapatan vs Profit (Scatter)", "Analisis Margin Profit", "Matriks Kinerja Produk", "Distribusi Penjualan"]
        )
        
        if chart_type == "Pendapatan vs Profit (Scatter)":
            fig = px.scatter(
                st.session_state.summary_data,
                x='Revenue',
                y='Profit',
                size='TotalQty',
                color='Profit Margin %',
                hover_data=['Product Name'],
                title="Analisis Pendapatan vs Profit",
                color_continuous_scale='RdYlGn',
                labels={'Revenue': 'Pendapatan (Rp)', 'Profit': 'Profit (Rp)'}
            )
            
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "Analisis Margin Profit":
            # Buat subplot
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Distribusi Margin Profit', 'Produk Teratas berdasarkan Margin', 
                              'Pendapatan vs Margin', 'Kuantitas vs Margin'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Histogram
            fig.add_trace(
                go.Histogram(x=st.session_state.summary_data['Profit Margin %'], 
                           name="Distribusi Margin", showlegend=False),
                row=1, col=1
            )
            
            # Produk teratas berdasarkan margin
            top_margin = st.session_state.summary_data.nlargest(10, 'Profit Margin %')
            fig.add_trace(
                go.Bar(x=top_margin['Product Name'], y=top_margin['Profit Margin %'],
                      name="Margin Tertinggi", showlegend=False),
                row=1, col=2
            )
            
            # Scatter pendapatan vs margin
            fig.add_trace(
                go.Scatter(x=st.session_state.summary_data['Revenue'], 
                          y=st.session_state.summary_data['Profit Margin %'],
                          mode='markers', name="Pendapatan vs Margin", showlegend=False),
                row=2, col=1
            )
            
            # Scatter kuantitas vs margin
            fig.add_trace(
                go.Scatter(x=st.session_state.summary_data['TotalQty'], 
                          y=st.session_state.summary_data['Profit Margin %'],
                          mode='markers', name="Kuantitas vs Margin", showlegend=False),
                row=2, col=2
            )
            
            fig.update_layout(height=600, title_text="Analisis Komprehensif Margin Profit")
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "Matriks Kinerja Produk":
            # Buat matriks kinerja dengan perbaikan untuk nilai negatif
            plot_data = st.session_state.summary_data.copy()
            
            # Pastikan nilai size selalu positif (gunakan absolut + offset kecil)
            plot_data['size_value'] = plot_data['Revenue'].abs() + 1
            
            # Buat informasi hover yang lebih informatif
            plot_data['hover_text'] = (
                plot_data['Product Name'] + '<br>' +
                'Revenue: Rp ' + plot_data['Revenue'].apply(lambda x: f"{x:,.0f}") + '<br>' +
                'Profit: Rp ' + plot_data['Profit'].apply(lambda x: f"{x:,.0f}") + '<br>' +
                'Margin: ' + plot_data['Profit Margin %'].apply(lambda x: f"{x:.1f}%")
            )
            
            fig = px.scatter(
                plot_data,
                x='TotalQty',
                y='Profit Margin %',
                size='size_value',  # Gunakan nilai yang sudah diperbaiki
                color='Profit',
                hover_name='Product Name',
                hover_data={
                    'Revenue': ':,.0f',
                    'Profit': ':,.0f',
                    'TotalQty': ':,.0f',
                    'Profit Margin %': ':.1f',
                    'size_value': False  # Sembunyikan kolom size_value dari hover
                },
                title="Matriks Kinerja Produk",
                labels={
                    'TotalQty': 'Total Kuantitas Terjual', 
                    'Profit Margin %': 'Margin Profit (%)',
                    'Profit': 'Profit (Rp)'
                },
                color_continuous_scale='RdYlGn',
                size_max=50  # Batasi ukuran maksimum marker
            )
            
            # Tambahkan garis kuadran
            median_qty = plot_data['TotalQty'].median()
            median_margin = plot_data['Profit Margin %'].median()
            
            fig.add_hline(y=median_margin, line_dash="dash", line_color="red", 
                         annotation_text=f"Margin Median: {median_margin:.1f}%")
            fig.add_vline(x=median_qty, line_dash="dash", line_color="red", 
                         annotation_text=f"Kuantitas Median: {median_qty:.0f}")
            
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
            
            # Analisis kuadran
            st.markdown("**📊 Analisis Kuadran:**")
            quad_col1, quad_col2, quad_col3, quad_col4 = st.columns(4)
            
            # Volume tinggi, margin tinggi (Bintang)
            stars = plot_data[
                (plot_data['TotalQty'] >= median_qty) & 
                (plot_data['Profit Margin %'] >= median_margin)
            ]
            
            # Volume tinggi, margin rendah (Kuda Pekerja)
            workhorses = plot_data[
                (plot_data['TotalQty'] >= median_qty) & 
                (plot_data['Profit Margin %'] < median_margin)
            ]
            
            # Volume rendah, margin tinggi (Ceruk)
            niche = plot_data[
                (plot_data['TotalQty'] < median_qty) & 
                (plot_data['Profit Margin %'] >= median_margin)
            ]
            
            # Volume rendah, margin rendah (Masalah)
            problem = plot_data[
                (plot_data['TotalQty'] < median_qty) & 
                (plot_data['Profit Margin %'] < median_margin)
            ]
            
            with quad_col1:
                st.metric("⭐ Bintang", len(stars), "Vol Tinggi, Margin Tinggi")
                if len(stars) > 0:
                    st.caption(f"Avg Revenue: Rp {stars['Revenue'].mean():,.0f}")
            with quad_col2:
                st.metric("🐎 Kuda Pekerja", len(workhorses), "Vol Tinggi, Margin Rendah")
                if len(workhorses) > 0:
                    st.caption(f"Avg Revenue: Rp {workhorses['Revenue'].mean():,.0f}")
            with quad_col3:
                st.metric("💎 Ceruk", len(niche), "Vol Rendah, Margin Tinggi")
                if len(niche) > 0:
                    st.caption(f"Avg Revenue: Rp {niche['Revenue'].mean():,.0f}")
            with quad_col4:
                st.metric("⚠️ Masalah", len(problem), "Vol Rendah, Margin Rendah")
                if len(problem) > 0:
                    st.caption(f"Avg Revenue: Rp {problem['Revenue'].mean():,.0f}")
            
            # Tambahkan tabel produk untuk setiap kuadran
            st.markdown("---")
            st.markdown("**🔍 Detail Produk per Kuadran:**")
            
            quad_tab1, quad_tab2, quad_tab3, quad_tab4 = st.tabs(["⭐ Bintang", "🐎 Kuda Pekerja", "💎 Ceruk", "⚠️ Masalah"])
            
            with quad_tab1:
                if len(stars) > 0:
                    display_stars = stars[['Product Name', 'TotalQty', 'Revenue', 'Profit', 'Profit Margin %']].copy()
                    display_stars['Revenue'] = display_stars['Revenue'].apply(lambda x: f"Rp {x:,.0f}")
                    display_stars['Profit'] = display_stars['Profit'].apply(lambda x: f"Rp {x:,.0f}")
                    display_stars['Profit Margin %'] = display_stars['Profit Margin %'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(display_stars.sort_values('TotalQty', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada produk dalam kategori ini")
            
            with quad_tab2:
                if len(workhorses) > 0:
                    display_workhorses = workhorses[['Product Name', 'TotalQty', 'Revenue', 'Profit', 'Profit Margin %']].copy()
                    display_workhorses['Revenue'] = display_workhorses['Revenue'].apply(lambda x: f"Rp {x:,.0f}")
                    display_workhorses['Profit'] = display_workhorses['Profit'].apply(lambda x: f"Rp {x:,.0f}")
                    display_workhorses['Profit Margin %'] = display_workhorses['Profit Margin %'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(display_workhorses.sort_values('TotalQty', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada produk dalam kategori ini")
            
            with quad_tab3:
                if len(niche) > 0:
                    display_niche = niche[['Product Name', 'TotalQty', 'Revenue', 'Profit', 'Profit Margin %']].copy()
                    display_niche['Revenue'] = display_niche['Revenue'].apply(lambda x: f"Rp {x:,.0f}")
                    display_niche['Profit'] = display_niche['Profit'].apply(lambda x: f"Rp {x:,.0f}")
                    display_niche['Profit Margin %'] = display_niche['Profit Margin %'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(display_niche.sort_values('Profit Margin %', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada produk dalam kategori ini")
            
            with quad_tab4:
                if len(problem) > 0:
                    display_problem = problem[['Product Name', 'TotalQty', 'Revenue', 'Profit', 'Profit Margin %']].copy()
                    display_problem['Revenue'] = display_problem['Revenue'].apply(lambda x: f"Rp {x:,.0f}")
                    display_problem['Profit'] = display_problem['Profit'].apply(lambda x: f"Rp {x:,.0f}")
                    display_problem['Profit Margin %'] = display_problem['Profit Margin %'].apply(lambda x: f"{x:.1f}%")
                    st.dataframe(display_problem.sort_values('Profit Margin %', ascending=False), use_container_width=True, hide_index=True)
                else:
                    st.info("Tidak ada produk dalam kategori ini")
        
        elif chart_type == "Distribusi Penjualan":
            # Buat analisis distribusi
            fig = make_subplots(
                rows=2, cols=2,
                subplot_titles=('Distribusi Pendapatan', 'Distribusi Profit', 
                              'Distribusi Kuantitas', 'Pendapatan Kumulatif'),
                specs=[[{"secondary_y": False}, {"secondary_y": False}],
                       [{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # Distribusi pendapatan
            fig.add_trace(
                go.Box(y=st.session_state.summary_data['Revenue'], 
                      name="Pendapatan", showlegend=False),
                row=1, col=1
            )
            
            # Distribusi profit
            fig.add_trace(
                go.Box(y=st.session_state.summary_data['Profit'], 
                      name="Profit", showlegend=False),
                row=1, col=2
            )
            
            # Distribusi kuantitas
            fig.add_trace(
                go.Box(y=st.session_state.summary_data['TotalQty'], 
                      name="Kuantitas", showlegend=False),
                row=2, col=1
            )
            
            # Pendapatan kumulatif (Pareto)
            sorted_data = st.session_state.summary_data.sort_values('Revenue', ascending=False)
            sorted_data['Cumulative Revenue'] = sorted_data['Revenue'].cumsum()
            sorted_data['Cumulative %'] = (sorted_data['Cumulative Revenue'] / sorted_data['Revenue'].sum()) * 100
            
            fig.add_trace(
                go.Scatter(x=list(range(1, len(sorted_data) + 1)), 
                          y=sorted_data['Cumulative %'],
                          mode='lines+markers', name="Persentase Pendapatan Kumulatif", showlegend=False),
                row=2, col=2
            )
            
            fig.update_layout(height=600, title_text="Analisis Distribusi Penjualan")
            st.plotly_chart(fig, use_container_width=True)
        
        # Wawasan tambahan
        st.markdown("---")
        if st.button("💬 Ringkas & Lanjut ke ChatGPT", type="primary"):
            if st.session_state.summary_data is not None:
                # --- ringkas data ---
                df = st.session_state.summary_data
                total_sku   = len(df)
                untung      = len(df[df['Profit'] > 0])
                hi_margin   = len(df[df['Profit Margin %'] > 20])
                top20_pct   = (df.nlargest(int(total_sku*0.2), 'Revenue')['Revenue'].sum() /
                               df['Revenue'].sum() * 100)
                low_margin  = len(df[df['Profit Margin %'] < 10])
                hi_vol_low  = len(df[(df['TotalQty'] >= df['TotalQty'].median()) &
                                     (df['Profit Margin %'] < 15)])

                prompt = f"""
                Kamu adalah Chief Data Scientist e-commerce. Buat laporan strategis 360° dari data berikut:
                                
                📊 Ringkasan Data:
                - Total SKU        : {total_sku}
                - Produk Untung    : {untung}
                - Margin >20 %     : {hi_margin}
                - 20 % Top SKU     : {top20_pct:.1f}% pendapatan
                - SKU margin <10 % : {low_margin}
                - SKU volume-tinggi-margin-rendah : {hi_vol_low}

                💬 Prompt ChatGPT:
                Buat:
                1. Executive summary 3 kalimat.
                2. 3 SKU prioritas optimize.
                3. 2 pricing strategy SKU margin rendah.
                4. Forecast 30 hari jika strategi 50 % rollout.
                
                """

                # encode URL-safe
                chatgpt_url = f"https://chat.openai.com/?q={quote(prompt)}"
                st.markdown(
                    f'<a href="{chatgpt_url}" target="_blank" rel="noopener noreferrer">'
                    '📲 Buka ChatGPT (tab baru)</a>',
                    unsafe_allow_html=True
                )
                st.text_area("📋 Copy prompt:", value=prompt, height=250)
            else:
                st.warning("⚠️ Proses data terlebih dahulu.")
        
        st.markdown("---")
        st.markdown("### 🔍 Wawasan Utama")
        
        insight_col1, insight_col2 = st.columns(2)
        
        with insight_col1:
            st.markdown("**📈 Wawasan Kinerja**")
            
            # Hitung wawasan
            total_products = len(st.session_state.summary_data)
            profitable_products = len(st.session_state.summary_data[st.session_state.summary_data['Profit'] > 0])
            high_margin_products = len(st.session_state.summary_data[st.session_state.summary_data['Profit Margin %'] > 20])
            
            st.write(f"• **{profitable_products}/{total_products}** produk menghasilkan profit")
            st.write(f"• **{high_margin_products}** produk memiliki margin >20%")
            st.write(f"• **Produk 20% teratas** menghasilkan **{(st.session_state.summary_data.nlargest(int(total_products*0.2), 'Revenue')['Revenue'].sum() / st.session_state.summary_data['Revenue'].sum() * 100):.1f}%** pendapatan")
        
        with insight_col2:
            st.markdown("**💡 Rekomendasi**")
            
            # Rekomendasi utama
            low_margin = st.session_state.summary_data[st.session_state.summary_data['Profit Margin %'] < 10]
            if not low_margin.empty:
                st.write(f"• Tinjau penetapan harga untuk **{len(low_margin)}** produk margin rendah")
            
            high_volume_low_margin = st.session_state.summary_data[
                (st.session_state.summary_data['TotalQty'] >= st.session_state.summary_data['TotalQty'].median()) & 
                (st.session_state.summary_data['Profit Margin %'] < 15)
            ]
            if not high_volume_low_margin.empty:
                st.write(f"• Optimalkan biaya untuk **{len(high_volume_low_margin)}** produk volume tinggi")
            
            st.write("• Fokuskan pemasaran pada produk margin tinggi")
            st.write("• Pertimbangkan menghentikan item yang secara konsisten berkinerja rendah")
    
    else:
        st.info("ℹ️ Silakan proses data Anda terlebih dahulu untuk melihat analisis lanjutan")

def show_detail_data_tab():
    """Tab Detail Data"""
    # Check if data is available
    if st.session_state.summary_data is None:
        st.info("🚀 **Mulai Analisis Data Anda** \n\nSilakan unggah dan proses data Anda terlebih dahulu untuk melihat analisis lengkap.")
        st.stop()

    # =================================================================
    # 1. DATA OVERVIEW SECTION
    # =================================================================
    st.subheader("📅 Ringkasan Periode Data")
    
    merged = st.session_state.merged_data
    date_cols = [
        'Order created time(UTC)', 'Order settled time(UTC)',
        'Order creation time', 'Order creation date', 'Order Date'
    ]
    date_col = next((c for c in date_cols if c in merged.columns), None)

    col1, col2 = st.columns([1, 1])
    
    with col1:
        if date_col:
            try:
                start = pd.to_datetime(merged[date_col]).min().strftime('%d %b %Y')
                end = pd.to_datetime(merged[date_col]).max().strftime('%d %b %Y')
                st.success(f"📆 **Periode Data:** {start} — {end}")
            except Exception:
                st.warning("⚠️ Periode data tidak dapat ditentukan")
        else:
            st.warning("⚠️ Kolom tanggal tidak ditemukan")

    with col2:
        # Order duplicates info - gunakan Order/adjustment ID
        freq = merged['Order/adjustment ID'].value_counts()
        dup_ids = freq[freq > 1]
        st.metric("🔍 Order ID Duplikat", len(dup_ids))

    if len(dup_ids) > 0:
        with st.expander("📋 Lihat Detail Order ID Duplikat"):
            st.write("**Order ID yang terdeteksi duplikat:**")
            st.code(", ".join(map(str, dup_ids.index.tolist()[:10])) + ("..." if len(dup_ids) > 10 else ""))

    st.divider()
    
    # =================================================================
    # 2. FINANCIAL OVERVIEW
    # =================================================================
    st.subheader("💰 Ringkasan Keuangan")
    
    income = st.session_state.income_data
    if income is not None and not income.empty:
        # Gunakan data income langsung (yang lebih akurat)
        # Filter income yang tidak refund
        clean_income = income[income['Customer refund'] >= 0]
        
        penghasilan_kotor = clean_income['Total revenue'].sum()
        penghasilan_bersih = clean_income['Total settlement amount'].sum()
        total_fees = clean_income['Total fees'].sum()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="💵 Penghasilan Kotor",
                value=f"Rp {penghasilan_kotor:,.0f}",
                help="Total pendapatan sebelum dipotong fee"
            )
            
        with col2:
            st.metric(
                label="💰 Penghasilan Bersih (Non-Refund)",
                value=f"Rp {penghasilan_bersih:,.0f}",
                delta=f"-Rp {total_fees:,.0f}",
                delta_color="inverse",
                help="Pendapatan setelah dipotong fee platform (hanya order tidak refund)"
            )
            
        with col3:
            fee_percentage = (total_fees / penghasilan_kotor * 100) if penghasilan_kotor > 0 else 0
            st.metric(
                label="📊 Persentase Fee",
                value=f"{fee_percentage:.2f}%",
                help="Persentase fee dari total penghasilan kotor"
            )
    else:
        st.info("ℹ️ Data penghasilan belum tersedia. Pastikan file income sudah diupload.")

    # Informasi tambahan tentang perbedaan revenue
    if st.session_state.summary_data is not None:
        st.info("""
        📊 **Catatan:** 
        - **Penghasilan Bersih** di atas = Total settlement amount dari income.xlsx (data yang akurat)
        - **Grand Total Revenue** di bawah = Revenue dari hasil merge income + pesanan (untuk analisis produk)
        - Data income.xlsx diprioritaskan karena pesanan.xlsx ada duplikat pesanan lama
        """)

    st.divider()

    # =================================================================
    # 3. PRODUCT FILTER & ANALYSIS
    # =================================================================
    st.subheader("🔍 Filter & Analisis Produk")

    # --- Info Grand Total (selalu tampil) ---------------------------
    grand_total_rev = st.session_state.summary_data['Revenue'].sum()
    grand_total_pro = st.session_state.summary_data['Profit'].sum()

    col_grand1, col_grand2 = st.columns(2)
    with col_grand1:
        st.metric("💵 Grand Total Revenue", f"Rp {grand_total_rev:,.0f}",
                help="Revenue dari order selesai yang tidak refund (konsisten dengan analisis produk)")
    with col_grand2:
        st.metric("💰 Grand Total Profit", f"Rp {grand_total_pro:,.0f}")

    st.markdown("---")

    # --- Filter (default 0 supaya langsung grand total) -------------
    with st.container():
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            min_rev = st.number_input("💵 Pendapatan Minimum", min_value=0, value=0, step=10000, format="%d")
        with col2:
            min_pro = st.number_input("💰 Profit Minimum", value=0, step=5000, format="%d")
        with col3:
            min_mar = st.number_input("📈 Margin Minimum (%)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
        with col4:
            sort_by = st.selectbox("📊 Urutkan berdasarkan",
                                ["Revenue", "Profit", "Profit Margin %", "Quantity"])

    # --- Terapkan filter --------------------------------------------
    filtered = st.session_state.summary_data[
        (st.session_state.summary_data['Revenue'] >= min_rev) &
        (st.session_state.summary_data['Profit'] >= min_pro) &
        (st.session_state.summary_data['Profit Margin %'] >= min_mar)
    ].sort_values(sort_by, ascending=False)

    # --- Ringkasan filter saat ini ----------------------------------
    col_sum1, col_sum2, col_sum3 = st.columns(3)
    with col_sum1:
        st.metric("📦 Produk Terfilter", len(filtered))
    with col_sum2:
        st.metric("💵 Sub-Total Revenue", f"Rp {filtered['Revenue'].sum():,.0f}")
    with col_sum3:
        st.metric("💰 Sub-Total Profit", f"Rp {filtered['Profit'].sum():,.0f}")

    # --- Tabel terformat --------------------------------------------
    if not filtered.empty:
        display = filtered.copy()
        for c in ['Revenue', 'Total Cost', 'Profit', 'Share 60%', 'Share 40%']:
            if c in display.columns:
                display[c] = display[c].apply(lambda x: f"Rp {x:,.0f}")
        display['Profit Margin %'] = display['Profit Margin %'].apply(lambda x: f"{x:.1f}%")

        st.markdown("#### 📋 Data Produk Terfilter")
        st.dataframe(display, use_container_width=True, hide_index=True)
    else:
        st.warning("🔍 Tidak ada produk yang memenuhi kriteria.")

    st.divider()

    # =================================================================
    # 4. REFUND & AFFILIATE ANALYSIS
    # =================================================================
    if st.session_state.income_data is not None:
        income = st.session_state.income_data

        # Refund Analysis
        st.subheader("💸 Analisis Refund")
        
        refund_df = income[income['Customer refund'] < 0]
        refunded_ids = set(refund_df['Order/adjustment ID'].unique())
        total_refund = refund_df['Customer refund'].sum()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔄 Total Order Refund", refund_df['Order/adjustment ID'].nunique())
        with col2:
            st.metric("💸 Total Nilai Refund", f"Rp {abs(total_refund):,.0f}")
        with col3:
            refund_rate = (len(refunded_ids) / income['Order/adjustment ID'].nunique() * 100) if len(income) > 0 else 0
            st.metric("📊 Tingkat Refund", f"{refund_rate:.2f}%")

        if not refund_df.empty:
            with st.expander("📋 Detail Order yang Di-refund"):
                refund_display = refund_df[['Order/adjustment ID', 'Customer refund']].drop_duplicates()
                refund_display['Customer refund'] = refund_display['Customer refund'].apply(lambda x: f"Rp {abs(x):,.0f}")
                refund_display = refund_display.sort_values('Order/adjustment ID')
                st.dataframe(refund_display, use_container_width=True, hide_index=True)

        st.divider()

        # Affiliate vs Store Analysis
        st.subheader("🤝 Analisis Affiliate vs Toko")
        
        base = income[~income['Order/adjustment ID'].isin(refunded_ids)].copy()
        aff = base[base['Affiliate commission'] < 0]
        tok = base[base['Affiliate commission'] == 0]

        def calc_metrics(df):
            rev = df['Total settlement amount'].sum()
            fees = df['Total fees'].sum()
            pct = (fees / rev * 100) if rev > 0 else 0
            return len(df), fees, pct, rev

        aff_cnt, aff_fee, aff_pct, aff_rev = calc_metrics(aff)
        tok_cnt, tok_fee, tok_pct, tok_rev = calc_metrics(tok)

        # Create comparison tables
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🤝 Order via Affiliate**")
            st.metric("Jumlah Order", f"{aff_cnt} pesanan")
            st.metric("Total Revenue", f"Rp {aff_rev:,.0f}")
            st.metric("Total Fee (TikTok + Affiliate)", f"Rp {aff_fee:,.0f}")
            st.metric("Rata-rata Fee", f"{aff_pct:.2f}%")

        with col2:
            st.markdown("**🏪 Order Toko Langsung**")
            st.metric("Jumlah Order", f"{tok_cnt} pesanan")
            st.metric("Total Revenue", f"Rp {tok_rev:,.0f}")
            st.metric("Total Fee (TikTok saja)", f"Rp {tok_fee:,.0f}")
            st.metric("Rata-rata Fee", f"{tok_pct:.2f}%")

        st.divider()

        # Commission Breakdown
        st.subheader("💳 Breakdown Komisi & Fee")
        
        all_cols = ['Dynamic Commission', 'Affiliate commission', 'TikTok Shop commission fee']
        available = [c for c in all_cols if c in base.columns]

        if available:
            cols = st.columns(len(available) + 1)
            
            for i, col in enumerate(available):
                total = abs(base[col].sum())
                with cols[i]:
                    st.metric(
                        label=col.replace('commission', 'komisi').replace('fee', 'fee'),
                        value=f"Rp {total:,.0f}"
                    )
            
            # Total fees
            total_fee_all = base['Total fees'].sum()
            with cols[-1]:
                st.metric("💰 Total Fee Keseluruhan", f"Rp {total_fee_all:,.0f}")
        else:
            st.info("ℹ️ Data breakdown komisi tidak tersedia")

        st.divider()

        # Order Source Table
        st.subheader("📊 Detail Sumber Order & Fee")
        
        cols_show = ['Order/adjustment ID', 'Total revenue', 'Total settlement amount', 'Total fees']
        commission_cols = ['Dynamic Commission', 'Affiliate commission', 'TikTok Shop commission fee']
        cols_show.extend([c for c in commission_cols if c in base.columns])

        # Prepare display data
        aff_display = aff[cols_show].copy() if not aff.empty else pd.DataFrame()
        tok_display = tok[cols_show].copy() if not tok.empty else pd.DataFrame()
        
        if not aff_display.empty:
            aff_display['Sumber'] = '🤝 Affiliate'
        if not tok_display.empty:
            tok_display['Sumber'] = '🏪 Toko'

        if not aff_display.empty or not tok_display.empty:
            df_orders = pd.concat([aff_display, tok_display], ignore_index=True)
            
            # Format currency columns
            currency_cols = [c for c in df_orders.columns if c in ['Total settlement amount', 'Total fees', 'Total revenue', 'Dynamic Commission', 'Affiliate commission', 'TikTok Shop commission fee']]
            for c in currency_cols:
                df_orders[c] = df_orders[c].apply(lambda x: f"Rp {abs(x):,.0f}")

            # Add search functionality
            search_term = st.text_input("🔍 Cari Order ID:", placeholder="Masukkan Order ID untuk pencarian...")
            if search_term:
                df_orders = df_orders[df_orders['Order/adjustment ID'].astype(str).str.contains(search_term, case=False, na=False)]
            
            st.dataframe(df_orders, use_container_width=True, hide_index=True)
        else:
            st.info("ℹ️ Tidak ada data order yang tersedia untuk ditampilkan")

    # Footer
    st.divider()
    st.markdown("📊 **Dashboard Analytics TikTok Shop** | Dibuat untuk membantu analisis bisnis Anda")

def show_compare_data_tab():
    """Tab Compare Data"""
    if st.session_state.get("mode") == "Compare Lama vs Baru":
        st.markdown("### 🔍 Perbandingan Lama vs Baru")

        # Cek apakah data lama tersedia
        if "old_summary" not in st.session_state or "summary_data" not in st.session_state:
            st.info("ℹ️ Upload & proses kedua periode terlebih dahulu.")
            st.stop()

        old = st.session_state.old_summary
        new = st.session_state.summary_data

        # --- METRIK PERBANDINGAN UTAMA ---
        st.markdown("#### 📊 Metrik Perbandingan")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            old_rev = old['Revenue'].sum()
            new_rev = new['Revenue'].sum()
            delta_rev = new_rev - old_rev
            pct_rev = (delta_rev / old_rev * 100) if old_rev > 0 else 0
            st.metric("💰 Revenue", f"Rp {new_rev:,.0f}", 
                     f"{pct_rev:+.1f}%", delta_color="normal" if delta_rev >= 0 else "inverse")
        
        with col2:
            old_pro = old['Profit'].sum()
            new_pro = new['Profit'].sum()
            delta_pro = new_pro - old_pro
            pct_pro = (delta_pro / old_pro * 100) if old_pro > 0 else 0
            st.metric("📈 Profit", f"Rp {new_pro:,.0f}", 
                     f"{pct_pro:+.1f}%", delta_color="normal" if delta_pro >= 0 else "inverse")
        
        with col3:
            old_qty = old['TotalQty'].sum()
            new_qty = new['TotalQty'].sum()
            delta_qty = new_qty - old_qty
            pct_qty = (delta_qty / old_qty * 100) if old_qty > 0 else 0
            st.metric("📦 Quantity", f"{new_qty:,}", 
                     f"{pct_qty:+.1f}%", delta_color="normal" if delta_qty >= 0 else "inverse")
        
        with col4:
            old_margin = old['Profit Margin %'].mean()
            new_margin = new['Profit Margin %'].mean()
            delta_margin = new_margin - old_margin
            st.metric("📊 Avg Margin", f"{new_margin:.1f}%", 
                     f"{delta_margin:+.1f}%", delta_color="normal" if delta_margin >= 0 else "inverse")

        # --- CHART PERBANDINGAN ---
        st.markdown("#### 📈 Grafik Perbandingan")
        
        compare_df = pd.DataFrame({
            "Periode": ["Lama", "Baru"],
            "Revenue": [old_rev, new_rev],
            "Profit": [old_pro, new_pro],
            "Quantity": [old_qty, new_qty]
        })

        fig = px.bar(
            compare_df,
            x="Periode",
            y=["Revenue", "Profit"],
            barmode="group",
            title="Perbandingan Revenue & Profit",
            color_discrete_sequence=['#667eea', '#764ba2']
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)

        # --- ANALISIS PRODUK PER PRODUK ---
        st.markdown("#### 🔍 Analisis Produk per Produk")
        
        # Gabungkan data untuk analisis
        old_products = old[['Product Name', 'Revenue', 'Profit', 'TotalQty', 'Profit Margin %']].copy()
        old_products['Periode'] = 'Lama'
        
        new_products = new[['Product Name', 'Revenue', 'Profit', 'TotalQty', 'Profit Margin %']].copy()
        new_products['Periode'] = 'Baru'
        
        # Merge untuk produk yang ada di kedua periode
        common_products = pd.merge(
            old_products, new_products, 
            on='Product Name', 
            suffixes=('_Lama', '_Baru')
        )
        
        if not common_products.empty:
            # Hitung perubahan
            common_products['Δ Revenue'] = common_products['Revenue_Baru'] - common_products['Revenue_Lama']
            common_products['Δ Profit'] = common_products['Profit_Baru'] - common_products['Profit_Lama']
            common_products['Δ Quantity'] = common_products['TotalQty_Baru'] - common_products['TotalQty_Lama']
            common_products['Δ Margin'] = common_products['Profit Margin %_Baru'] - common_products['Profit Margin %_Lama']
            
            # Filter produk dengan perubahan signifikan
            significant_changes = common_products[
                (abs(common_products['Δ Revenue']) > 100000) |  # Perubahan > 100k
                (abs(common_products['Δ Profit']) > 50000) |    # Perubahan > 50k
                (abs(common_products['Δ Margin']) > 5)          # Perubahan margin > 5%
            ].sort_values('Δ Revenue', ascending=False)
            
            if not significant_changes.empty:
                st.markdown("**📊 Produk dengan Perubahan Signifikan:**")
                
                display_changes = significant_changes[['Product Name', 'Δ Revenue', 'Δ Profit', 'Δ Quantity', 'Δ Margin']].copy()
                display_changes['Δ Revenue'] = display_changes['Δ Revenue'].apply(lambda x: f"Rp {x:+,.0f}")
                display_changes['Δ Profit'] = display_changes['Δ Profit'].apply(lambda x: f"Rp {x:+,.0f}")
                display_changes['Δ Quantity'] = display_changes['Δ Quantity'].apply(lambda x: f"{x:+,.0f}")
                display_changes['Δ Margin'] = display_changes['Δ Margin'].apply(lambda x: f"{x:+.1f}%")
                
                st.dataframe(display_changes, use_container_width=True, hide_index=True)
            else:
                st.info("ℹ️ Tidak ada produk dengan perubahan signifikan")
            
            # Produk baru dan hilang
            old_product_names = set(old['Product Name'])
            new_product_names = set(new['Product Name'])
            
            new_products_only = new_product_names - old_product_names
            old_products_only = old_product_names - new_product_names
            
            col_new, col_old = st.columns(2)
            
            with col_new:
                if new_products_only:
                    st.markdown("**🆕 Produk Baru:**")
                    new_only_data = new[new['Product Name'].isin(new_products_only)][['Product Name', 'Revenue', 'Profit']]
                    new_only_data['Revenue'] = new_only_data['Revenue'].apply(lambda x: f"Rp {x:,.0f}")
                    new_only_data['Profit'] = new_only_data['Profit'].apply(lambda x: f"Rp {x:,.0f}")
                    st.dataframe(new_only_data, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ Tidak ada produk baru")
            
            with col_old:
                if old_products_only:
                    st.markdown("**❌ Produk yang Hilang:**")
                    old_only_data = old[old['Product Name'].isin(old_products_only)][['Product Name', 'Revenue', 'Profit']]
                    old_only_data['Revenue'] = old_only_data['Revenue'].apply(lambda x: f"Rp {x:,.0f}")
                    old_only_data['Profit'] = old_only_data['Profit'].apply(lambda x: f"Rp {x:,.0f}")
                    st.dataframe(old_only_data, use_container_width=True, hide_index=True)
                else:
                    st.info("ℹ️ Tidak ada produk yang hilang")
        else:
            st.warning("⚠️ Tidak ada produk yang sama di kedua periode")

        # --- REKOMENDASI STRATEGIS ---
        st.markdown("#### 💡 Rekomendasi Strategis")
        
        # Hitung insight
        revenue_growth = (delta_rev / old_rev * 100) if old_rev > 0 else 0
        profit_growth = (delta_pro / old_pro * 100) if old_pro > 0 else 0
        
        insight_col1, insight_col2 = st.columns(2)
        
        with insight_col1:
            st.markdown("**📈 Tren Kinerja:**")
            if revenue_growth > 0:
                st.success(f"✅ Revenue tumbuh {revenue_growth:.1f}%")
            else:
                st.error(f"❌ Revenue turun {abs(revenue_growth):.1f}%")
            
            if profit_growth > 0:
                st.success(f"✅ Profit tumbuh {profit_growth:.1f}%")
            else:
                st.error(f"❌ Profit turun {abs(profit_growth):.1f}%")
            
            if delta_margin > 0:
                st.success(f"✅ Margin rata-rata naik {delta_margin:.1f}%")
            else:
                st.warning(f"⚠️ Margin rata-rata turun {abs(delta_margin):.1f}%")
        
        with insight_col2:
            st.markdown("**🎯 Rekomendasi:**")
            if revenue_growth < 0:
                st.write("• Tinjau strategi pricing dan marketing")
            if profit_growth < revenue_growth:
                st.write("• Optimalkan biaya operasional")
            if len(new_products_only) > len(old_products_only):
                st.write("• Fokus pada produk baru yang perform")
            if len(significant_changes) > 0:
                st.write("• Analisis produk dengan perubahan signifikan")

    else:
        st.info("Pilih mode 'Compare Lama vs Baru' di sidebar untuk melihat tab ini.") 