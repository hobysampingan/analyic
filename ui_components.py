import streamlit as st
import pandas as pd
from config import CUSTOM_CSS

def show_header():
    """Menampilkan header aplikasi"""
    st.markdown("""
    <div class="main-header">
        <h1>📊 Analisis Pendapatan & Pesanan</h1>
        <p>Intelijen bisnis komprehensif untuk operasi e-commerce Anda</p>
    </div>
    """, unsafe_allow_html=True)

def show_sidebar_status():
    """Menampilkan status data di sidebar"""
    st.markdown("### 🎛️ Panel Kontrol")
    
    # Status data
    st.markdown("**📊 Status Data:**")
    pesanan_status = "✅ Dimuat" if st.session_state.pesanan_data is not None else "❌ Tidak dimuat"
    income_status = "✅ Dimuat" if st.session_state.income_data is not None else "❌ Tidak dimuat"
    processed_status = "✅ Diproses" if st.session_state.summary_data is not None else "❌ Tidak diproses"
    
    st.write(f"Pesanan: {pesanan_status}")
    st.write(f"Pendapatan: {income_status}")
    st.write(f"Analisis: {processed_status}")
    
    st.markdown("---")
    
    # Mode analisis
    st.session_state.mode = st.sidebar.radio(
        "🔄 Mode Analisis",
        ["Single Data", "Compare Lama vs Baru"],
        help="Pilih 'Compare' untuk upload 4 file"
    )
    
    st.markdown("---")

def show_data_upload_section():
    """Upload adaptif: Single vs Compare (4 file)"""
    mode = st.session_state.get("mode", "Single Data")

    if mode == "Compare Lama vs Baru":
        st.markdown("### 📂 Upload Data Lama (Checkpoint)")
        old_pesanan = st.file_uploader("📄 Pesanan Selesai Lama", type=["xlsx", "xls"], key="old_pesanan")
        old_income  = st.file_uploader("💰 Income Lama",          type=["xlsx", "xls"], key="old_income")

        st.markdown("### 📂 Upload Data Baru (Fresh)")
        new_pesanan = st.file_uploader("📄 Pesanan Selesai Baru", type=["xlsx", "xls"], key="new_pesanan")
        new_income  = st.file_uploader("💰 Income Baru",          type=["xlsx", "xls"], key="new_income")

        # Load & simpan ke session_state
        for key, file in {
            "old_pesanan_data": old_pesanan,
            "old_income_data":  old_income,
            "pesanan_data":     new_pesanan,
            "income_data":      new_income
        }.items():
            if file is not None:
                try:
                    if "pesanan" in key:
                        df = pd.read_excel(file, header=0, skiprows=[1])
                    else:
                        df = pd.read_excel(file, header=0)
                    df.columns = [str(c).strip() for c in df.columns]
                    st.session_state[key] = df
                    st.success(f"✅ {key.replace('_',' ').title()} : {len(df)} baris")
                except Exception as e:
                    st.error(f"❌ {key}: {e}")

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

def show_metrics_dashboard():
    """Dasbor metrik yang ditingkatkan"""
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

def show_cost_management():
    """Antarmuka manajemen biaya yang ditingkatkan"""
    st.markdown("### 💸 Manajemen Biaya")
    
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
                    # app.save_cost_data(st.session_state.cost_data)
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
            st.download_button(
                label="💾 Unduh JSON",
                data=json.dumps(st.session_state.cost_data, ensure_ascii=False, indent=2),
                file_name=f"product_costs_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json"
            )
    
    with action_col3:
        if st.button("🔄 Segarkan Data", help="Muat ulang data biaya dari file"):
            # st.session_state.cost_data = app.load_cost_data()
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
                    # app.save_cost_data(st.session_state.cost_data)
                    st.success(f"✅ Biaya disimpan untuk {selected_product}")
                    st.rerun()
                else:
                    st.warning("⚠️ Masukkan produk dan biaya yang valid")
        
        with btn_col2:
            if st.button("🗑️ Hapus Biaya", type="secondary"):
                if selected_product in st.session_state.cost_data:
                    del st.session_state.cost_data[selected_product]
                    # app.save_cost_data(st.session_state.cost_data)
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