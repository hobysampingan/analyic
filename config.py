import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# Konfigurasi halaman Streamlit
PAGE_CONFIG = {
    "page_title": "📊 Analisis Pendapatan & Pesanan",
    "page_icon": "💰",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# Konfigurasi Google Sheets
GOOGLE_SHEETS_CONFIG = {
    "SCOPES": ["https://www.googleapis.com/auth/spreadsheets"],
    "SHEET_ID": "1FEiXnSrMaaxjPLVTNMWQd4U2ZaNPJXCm-yjlFt5HfL8",
    "SHEET_NAME": "Sheet1"
}

# CSS kustom
CUSTOM_CSS = """
<style>
    .main-header {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        text-align: center;
        color: white;
    }
    
    .metric-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    
    .status-success {
        background: #d4edda;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        border-left: 4px solid #28a745;
    }
    
    .status-warning {
        background: #fff3cd;
        color: #856404;
        padding: 0.75rem;
        border-radius: 5px;
        border-left: 4px solid #ffc107;
    }
    
    .status-error {
        background: #f8d7da;
        color: #721c24;
        padding: 0.75rem;
        border-radius: 5px;
        border-left: 4px solid #dc3545;
    }
    
    .sidebar .stSelectbox > div > div {
        background-color: #f8f9fa;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
    }
    
    .upload-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 8px;
        border: 2px dashed #dee2e6;
        margin-bottom: 1rem;
    }
    
    .chart-container {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
    }
</style>
"""

# Konfigurasi kolom yang diperlukan
REQUIRED_COLUMNS = {
    "pesanan": ['Order Status', 'Order ID', 'Quantity', 'Seller SKU', 'Product Name', 'Variation'],
    "income": ['Order/adjustment ID', 'Total settlement amount']
}

# Konfigurasi cache
CACHE_CONFIG = {
    "file_name": "cost_data_cache.json",
    "expiry_hours": 1
}

def get_google_credentials():
    """Mendapatkan kredensial Google Sheets"""
    try:
        service_account_info = st.secrets["google_credentials"]
        creds = Credentials.from_service_account_info(
            service_account_info, 
            scopes=GOOGLE_SHEETS_CONFIG["SCOPES"]
        )
        gc = gspread.authorize(creds)
        return gc
    except Exception as e:
        st.error(f"Gagal menginisialisasi Google Sheets: {str(e)}")
        return None 