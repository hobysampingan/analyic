import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta

# Import modul-modul yang sudah dibuat
from config import PAGE_CONFIG, CUSTOM_CSS, get_google_credentials
from data_processor import IncomeApp
from ui_components import show_header, show_sidebar_status, show_data_upload_section, show_metrics_dashboard, show_cost_management
from tabs import show_dashboard_tab, show_cost_management_tab, show_analytics_tab, show_detail_data_tab, show_compare_data_tab

def initialize_session_state():
    """Inisialisasi state sesi"""
    if 'cost_data' not in st.session_state:
        st.session_state.cost_data = {}
    if 'pesanan_data' not in st.session_state:
        st.session_state.pesanan_data = None
    if 'income_data' not in st.session_state:
        st.session_state.income_data = None
    if 'merged_data' not in st.session_state:
        st.session_state.merged_data = None
    if 'summary_data' not in st.session_state:
        st.session_state.summary_data = None
    if 'mode' not in st.session_state:
        st.session_state.mode = "Single Data"

def process_data_logic():
    """Logika untuk memproses data sesuai mode"""
    app = IncomeApp()
    
    # Update cost_data dari app
    st.session_state.cost_data = app.cost_data
    
    if st.session_state.get("mode") == "Compare Lama vs Baru":
        # 1. Data lama (checkpoint) – hanya dipakai di tab Compare
        if ("old_pesanan_data" in st.session_state and "old_income_data" in st.session_state and
            st.session_state.old_pesanan_data is not None and st.session_state.old_income_data is not None):
            st.session_state.old_merged, st.session_state.old_summary = app.process_data(
                st.session_state.old_pesanan_data,
                st.session_state.old_income_data,
                st.session_state.cost_data
            )
        # 2. Data baru (fresh) – dipakai semua tab utama
        if ("pesanan_data" in st.session_state and "income_data" in st.session_state and
            st.session_state.pesanan_data is not None and st.session_state.income_data is not None):
            st.session_state.merged_data, st.session_state.summary_data = app.process_data(
                st.session_state.pesanan_data,
                st.session_state.income_data,
                st.session_state.cost_data
            )
    else:  # Single Data
        if ("pesanan_data" in st.session_state and "income_data" in st.session_state and
            st.session_state.pesanan_data is not None and st.session_state.income_data is not None):
            st.session_state.merged_data, st.session_state.summary_data = app.process_data(
                st.session_state.pesanan_data,
                st.session_state.income_data,
                st.session_state.cost_data
            )
    
    return app

def show_sidebar_actions(app):
    """Menampilkan aksi di sidebar"""
    st.markdown("---")
    
    # Aksi cepat
    st.markdown("**⚡ Aksi Cepat:**")

    if st.sidebar.button("🔄 Proses Data", type="primary", use_container_width=True):
        if st.session_state.get("mode") == "Compare Lama vs Baru":
            # Proses data lama (checkpoint)
            if ("old_pesanan_data" in st.session_state and "old_income_data" in st.session_state and
                st.session_state.old_pesanan_data is not None and st.session_state.old_income_data is not None):
                st.session_state.old_merged, st.session_state.old_summary = app.process_data(
                    st.session_state.old_pesanan_data,
                    st.session_state.old_income_data,
                    st.session_state.cost_data
                )
            
            # Proses data baru (fresh) - ini yang dipakai untuk semua UI
            if ("pesanan_data" in st.session_state and "income_data" in st.session_state and
                st.session_state.pesanan_data is not None and st.session_state.income_data is not None):
                st.session_state.merged_data, st.session_state.summary_data = app.process_data(
                    st.session_state.pesanan_data,
                    st.session_state.income_data,
                    st.session_state.cost_data
                )
                st.success("✅ Data lama dan baru diproses!")
                st.rerun()
            else:
                st.warning("⚠️ Upload data baru terlebih dahulu")
        else:
            # Proses data tunggal
            if (st.session_state.pesanan_data is not None and st.session_state.income_data is not None and
                not st.session_state.pesanan_data.empty and not st.session_state.income_data.empty):
                with st.spinner("Memproses data..."):
                    merged, summary = app.process_data(
                        st.session_state.pesanan_data, 
                        st.session_state.income_data, 
                        st.session_state.cost_data
                    )
                    
                    if merged is not None:
                        st.session_state.merged_data = merged
                        st.session_state.summary_data = summary
                        st.success("✅ Data diproses!")
                        st.rerun()
                    else:
                        st.error("❌ Tidak ditemukan data yang cocok")
            else:
                st.warning("⚠️ Unggah kedua file terlebih dahulu")

    if st.session_state.summary_data is not None:
        if st.button("📥 Ekspor Laporan", use_container_width=True):
            try:
                excel_data = app.create_excel_report(
                    st.session_state.merged_data,
                    st.session_state.summary_data,
                    st.session_state.cost_data
                )
                
                st.download_button(
                    label="💾 Unduh Excel",
                    data=excel_data,
                    file_name=f"income_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Kesalahan: {str(e)}")

    # Cache info
    if os.path.exists("cost_data_cache.json"):
        try:
            with open("cost_data_cache.json", 'r') as f:
                cache_data = json.load(f)
                cache_age = (datetime.now() - datetime.fromisoformat(cache_data['timestamp']))
                st.caption(f"📊 Cache: {cache_age.seconds//60} menit lalu")
        except:
            pass
    
    st.markdown("---")
    
    # Statistik cepat biaya
    if st.session_state.cost_data:
        st.markdown("**💰 Data Biaya:**")
        st.write(f"Produk: {len(st.session_state.cost_data)}")
        avg_cost = sum(st.session_state.cost_data.values()) / len(st.session_state.cost_data)
        st.write(f"Biaya Rata-rata: Rp {avg_cost:,.0f}")

def main():
    """Fungsi utama aplikasi"""
    # Konfigurasi halaman
    st.set_page_config(**PAGE_CONFIG)
    
    # CSS kustom
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    
    # Inisialisasi session state
    initialize_session_state()
    
    # Header
    show_header()
    
    # Inisialisasi aplikasi
    app = process_data_logic()
    
    # Sidebar
    with st.sidebar:
        show_sidebar_status()
        show_sidebar_actions(app)
    
    # Tab konten utama
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Dasbor", 
        "💸 Manajemen Biaya", 
        "📈 Analisis", 
        "📋 Detail Data",
        "🔄 Compare Data",
        "🧠 Analisis Lengkap"
    ])
    
    with tab1:
        show_dashboard_tab()
    
    with tab2:
        show_cost_management_tab()
    
    with tab3:
        show_analytics_tab()

    with tab4:
        show_detail_data_tab()

    with tab5:
        show_compare_data_tab()
    
    with tab6:
        from full_analysis_tab import show_full_analysis_tab
        show_full_analysis_tab()

if __name__ == "__main__":
    main() 