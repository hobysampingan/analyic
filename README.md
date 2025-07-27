# 📊 Analisis Pendapatan & Pesanan - TikTok Shop

Aplikasi Streamlit untuk analisis komprehensif data penjualan TikTok Shop dengan fitur manajemen biaya, analisis affiliate, dan laporan Excel profesional.

## 🚀 Fitur Utama

### 📈 **Analisis Data**
- Dashboard metrik real-time
- Analisis produk per SKU
- Perbandingan periode (Lama vs Baru)
- Analisis affiliate vs toko langsung
- Breakdown komisi & fee detail

### 💰 **Manajemen Biaya**
- Input dan edit biaya produk
- Import/export data biaya
- Integrasi dengan Google Sheets
- Cache lokal untuk performa

### 📊 **Laporan Excel Profesional**
- Ringkasan penjualan & profit
- Analisis affiliate vs toko
- Breakdown komisi & fee
- Detail sumber order & fee
- Penjualan harian
- Produk teratas

### 🔄 **Mode Analisis**
- **Single Data**: Analisis satu periode
- **Compare Lama vs Baru**: Perbandingan dua periode

## 🛠️ Instalasi & Setup

### 1. **Clone Repository**
```bash
git clone https://github.com/username/incomedata.git
cd incomedata
```

### 2. **Setup Virtual Environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 4. **Setup Google Sheets (Opsional)**
Untuk fitur manajemen biaya dengan Google Sheets:

1. Buat Google Service Account
2. Download credentials JSON
3. Buat file `.streamlit/secrets.toml`:
```toml
[google_credentials]
type = "service_account"
project_id = "your-project-id"
private_key_id = "your-private-key-id"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "your-service-account@your-project.iam.gserviceaccount.com"
client_id = "your-client-id"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account%40your-project.iam.gserviceaccount.com"
```

### 5. **Jalankan Aplikasi**
```bash
streamlit run main_app.py
```

## 📁 Struktur File

```
incomedata/
├── main_app.py              # Entry point aplikasi
├── data_processor.py        # Logic pemrosesan data
├── tabs.py                  # UI components untuk tabs
├── ui_components.py         # Reusable UI components
├── config.py               # Konfigurasi aplikasi
├── requirements.txt        # Dependencies
├── README.md              # Dokumentasi
├── .gitignore             # Git ignore rules
└── .streamlit/
    └── secrets.toml       # Secrets (tidak diupload ke GitHub)
```

## 📊 Cara Penggunaan

### 1. **Upload Data**
- Upload file Excel pesanan selesai
- Upload file Excel data pendapatan
- Pilih mode analisis (Single/Compare)

### 2. **Proses Data**
- Klik "Proses Data" di sidebar
- Tunggu hingga data selesai diproses

### 3. **Analisis**
- Dashboard: Metrik utama dan grafik
- Detail Data: Analisis lengkap per produk
- Cost Management: Kelola biaya produk
- Analytics: Grafik interaktif
- Compare Data: Perbandingan periode

### 4. **Export Laporan**
- Klik "Ekspor Laporan" di sidebar
- Download file Excel dengan analisis lengkap

## 🔧 Konfigurasi

### **Google Sheets Integration**
- Edit `SHEET_ID` di `data_processor.py`
- Pastikan service account memiliki akses

### **Cache Settings**
- Cache biaya disimpan di `cost_data_cache.json`
- Auto-refresh setiap 1 jam
- Bisa di-reset manual di UI

## 🚨 Troubleshooting

### **Error: "No module named 'streamlit'"**
```bash
pip install streamlit
```

### **Error: Google Sheets Access**
- Periksa credentials di `.streamlit/secrets.toml`
- Pastikan service account memiliki permission

### **Error: File Upload**
- Pastikan format file Excel (.xlsx/.xls)
- Periksa struktur kolom sesuai template

## 📝 Format Data yang Diperlukan

### **File Pesanan (pesanan.xlsx)**
- Kolom wajib: `Order Status`, `Order ID`, `Quantity`, `Seller SKU`, `Product Name`
- Format: Excel dengan header di baris pertama

### **File Pendapatan (income.xlsx)**
- Kolom wajib: `Order/adjustment ID`, `Total settlement amount`
- Format: Excel dengan header di baris pertama

## 🤝 Kontribusi

1. Fork repository
2. Buat feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push ke branch (`git push origin feature/AmazingFeature`)
5. Buat Pull Request

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

## 📞 Support

Jika ada pertanyaan atau masalah:
- Buat issue di GitHub
- Email: your-email@example.com

---

**Dibuat dengan ❤️ untuk analisis bisnis TikTok Shop** 