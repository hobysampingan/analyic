import pandas as pd
import json
import os
from datetime import datetime, timedelta
import io
import streamlit as st
from config import GOOGLE_SHEETS_CONFIG, REQUIRED_COLUMNS, CACHE_CONFIG, get_google_credentials

class IncomeApp:
    """Class utama untuk memproses data pendapatan dan pesanan"""
    
    def __init__(self):
        self.CACHE_FILE = CACHE_CONFIG["file_name"]
        self.gc = get_google_credentials()
        self.cost_data = self.load_cost_data()
    
    def load_cost_data(self):
        """Load cost data dengan strategi cache"""
        # 1. Coba load dari local cache (max 1 jam)
        if os.path.exists(self.CACHE_FILE):
            try:
                with open(self.CACHE_FILE, 'r') as f:
                    cached = json.load(f)
                    # Cek expired (1 jam)
                    if datetime.fromisoformat(cached['timestamp']) > datetime.now() - timedelta(hours=CACHE_CONFIG["expiry_hours"]):
                        return cached['data']
            except Exception:
                pass
        
        # 2. Kalau cache ga ada/expired → ambil dari Google
        if self.gc:
            try:
                sheet = self.gc.open_by_key(GOOGLE_SHEETS_CONFIG["SHEET_ID"]).worksheet(GOOGLE_SHEETS_CONFIG["SHEET_NAME"])
                records = sheet.get_all_records()
                cost_data = {row["product_name"]: float(row["cost_per_unit"]) for row in records}
                
                # 3. Simpan ke cache
                with open(self.CACHE_FILE, 'w') as f:
                    json.dump({
                        'data': cost_data,
                        'timestamp': datetime.now().isoformat()
                    }, f)
                
                return cost_data
                
            except Exception as e:
                st.error(f"Gagal load dari Google: {str(e)}")
                return {}
        else:
            return {}

    def save_cost_data(self, cost_dict):
        """Simpan ke Google + update cache lokal"""
        if self.gc:
            try:
                # Save ke Google
                sheet = self.gc.open_by_key(GOOGLE_SHEETS_CONFIG["SHEET_ID"]).worksheet(GOOGLE_SHEETS_CONFIG["SHEET_NAME"])
                sheet.clear()
                sheet.update(values=[["product_name", "cost_per_unit"]], range_name="A1")
                rows = [[k, v] for k, v in cost_dict.items()]
                sheet.update(values=rows, range_name="A2")
                
                # Update cache lokal
                with open(self.CACHE_FILE, 'w') as f:
                    json.dump({
                        'data': cost_dict,
                        'timestamp': datetime.now().isoformat()
                    }, f)
            except Exception as e:
                st.error(f"Gagal menyimpan ke Google: {str(e)}")
    
    def get_product_cost(self, product_name, cost_data):
        """Mendapatkan biaya produk dari data biaya"""
        return float(cost_data.get(product_name, 0.0))
    
    def process_data(self, pesanan_data, income_data, cost_data):
        """Memproses dan menggabungkan data"""
        # Validasi input data
        if pesanan_data is None or income_data is None:
            return None, None
            
        if pesanan_data.empty or income_data.empty:
            return None, None
            
        # Validasi kolom yang diperlukan
        missing_pesanan_cols = [col for col in REQUIRED_COLUMNS["pesanan"] if col not in pesanan_data.columns]
        missing_income_cols = [col for col in REQUIRED_COLUMNS["income"] if col not in income_data.columns]
        
        if missing_pesanan_cols or missing_income_cols:
            print(f"Missing columns in pesanan_data: {missing_pesanan_cols}")
            print(f"Missing columns in income_data: {missing_income_cols}")
            return None, None
        
        # =================================================================
        # LOGIKA BARU: Prioritaskan data dari income.xlsx
        # =================================================================
        
        # 1. Ambil data income yang bersih (tidak refund)
        clean_income = income_data[income_data['Customer refund'] >= 0].copy()
        
        # Debug info
        print(f"Total income records: {len(income_data)}")
        print(f"Clean income records (non-refund): {len(clean_income)}")
        print(f"Total revenue from income: Rp {clean_income['Total settlement amount'].sum():,.0f}")
        print(f"Expected revenue (income.xlsx): Rp 5,202,419")
        print(f"Difference: Rp {clean_income['Total settlement amount'].sum() - 5202419:,.0f}")
        
        if clean_income.empty:
            print("No clean income data found (all orders are refunded)")
            return None, None
        
        # 2. Filter pesanan selesai untuk mendapatkan info produk
        df1 = pesanan_data[pesanan_data['Order Status'] == 'Selesai'].copy()
        
        # Debug info
        print(f"Total pesanan records: {len(pesanan_data)}")
        print(f"Completed orders: {len(df1)}")
        print(f"Unique order IDs in pesanan: {df1['Order ID'].nunique()}")
        
        if df1.empty:
            print("No completed orders found")
            return None, None
        
        # 3. Gabungkan dengan LEFT JOIN dari income ke pesanan
        # Ini memastikan semua data income terambil, meskipun ada duplikat di pesanan
        merged = pd.merge(
            clean_income, 
            df1, 
            left_on='Order/adjustment ID', 
            right_on='Order ID', 
            how='left'
        )
        
        # Debug info
        print(f"Merged records: {len(merged)}")
        print(f"Unique orders after merge: {merged['Order/adjustment ID'].nunique()}")
        print(f"Total revenue after merge: Rp {merged['Total settlement amount'].sum():,.0f}")
        
        # Debug final result
        unique_final = merged.drop_duplicates(subset=['Order/adjustment ID'])
        final_revenue = unique_final['Total settlement amount'].sum()
        print(f"Final unique orders: {len(unique_final)}")
        print(f"Final total revenue: Rp {final_revenue:,.0f}")
        print(f"Final vs Expected difference: Rp {final_revenue - 5202419:,.0f}")
        
        if merged.empty:
            print("No matching orders found between income and pesanan data")
            return None, None
        
        # 4. Hapus duplikat berdasarkan Order ID dari income (yang lebih akurat)
        unique_orders = merged.drop_duplicates(subset=['Order/adjustment ID'])
        
        # 5. Buat ringkasan berdasarkan data yang ada
        # Jika ada kolom produk yang kosong, gunakan default
        summary_columns = ['Seller SKU', 'Product Name', 'Variation']
        available_columns = [col for col in summary_columns if col in unique_orders.columns]
        
        if len(available_columns) >= 2:  # Minimal ada Product Name
            summary = unique_orders.groupby(available_columns, as_index=False).agg(
                TotalQty=('Quantity', 'sum') if 'Quantity' in unique_orders.columns else ('Order/adjustment ID', 'count'),
                Revenue=('Total settlement amount', 'sum')
            )
        else:
            # Fallback: group by Order ID saja
            summary = unique_orders.groupby('Order/adjustment ID', as_index=False).agg(
                Revenue=('Total settlement amount', 'sum')
            )
            summary['TotalQty'] = 1
            summary['Product Name'] = 'Unknown Product'
            summary['Seller SKU'] = 'Unknown SKU'
            summary['Variation'] = 'Unknown Variation'
        
        # Tambahkan perhitungan biaya
        summary['Cost per Unit'] = summary['Product Name'].apply(
            lambda x: self.get_product_cost(x, cost_data)
        )
        summary['Total Cost'] = summary['TotalQty'] * summary['Cost per Unit']
        summary['Profit'] = summary['Revenue'] - summary['Total Cost']
        summary['Profit Margin %'] = (summary['Profit'] / summary['Revenue'] * 100).round(2)
        summary['Share 60%'] = summary['Profit'] * 0.6
        summary['Share 40%'] = summary['Profit'] * 0.4
        
        return merged, summary
    
    def create_excel_report(self, merged_data, summary_data, cost_data):
        """Membuat laporan Excel"""
        output = io.BytesIO()
        
        # Hitung total
        # Gunakan Order/adjustment ID sebagai primary key (sesuai dengan logika baru)
        unique_orders = merged_data.drop_duplicates(subset=['Order/adjustment ID'])

        total_orders  = unique_orders['Order/adjustment ID'].nunique()
        total_revenue = unique_orders['Total settlement amount'].sum()
        total_qty     = unique_orders['Quantity'].sum() if 'Quantity' in unique_orders.columns else 0
        
        # Ringkasan berdasarkan SKU
        summary_by_sku = (
            unique_orders.groupby('Seller SKU', as_index=False)
            .agg({
                'Quantity': 'sum' if 'Quantity' in unique_orders.columns else ('Order/adjustment ID', 'count'),
                'Order/adjustment ID': 'nunique',
                'Total settlement amount': 'sum'
            })
            .rename(columns={
                'Quantity': 'Total Quantity',
                'Order/adjustment ID': 'Total Orders',
                'Total settlement amount': 'Total Revenue'
            })
        )
        
        # Dapatkan nama produk pertama untuk setiap SKU
        sku_products = merged_data.groupby('Seller SKU')['Product Name'].first().to_dict()
        summary_by_sku['Cost per Unit'] = summary_by_sku['Seller SKU'].map(
            lambda sku: self.get_product_cost(sku_products.get(sku, ''), cost_data)
        )
        summary_by_sku['Total Cost'] = summary_by_sku['Total Quantity'] * summary_by_sku['Cost per Unit']
        summary_by_sku['Profit'] = summary_by_sku['Total Revenue'] - summary_by_sku['Total Cost']
        summary_by_sku['Profit Margin %'] = (summary_by_sku['Profit'] / summary_by_sku['Total Revenue'] * 100).round(2)
        summary_by_sku['Share 60%'] = summary_by_sku['Profit'] * 0.6
        summary_by_sku['Share 40%'] = summary_by_sku['Profit'] * 0.4
        
        # Hitung total biaya dan profit
        total_cost = summary_by_sku['Total Cost'].sum()
        total_profit = total_revenue - total_cost
        total_share_60 = total_profit * 0.6
        total_share_40 = total_profit * 0.4
        
        # Analisis penjualan harian
        date_column = None
        possible_date_columns = [
            'Order created time(UTC)', 'Order creation time', 'Order Creation Time', 
            'Creation Time', 'Date', 'Order Date', 'Order created time', 'Created time'
        ]
        
        for col in possible_date_columns:
            if col in merged_data.columns:
                date_column = col
                break
        
        if date_column:
            try:
                merged_data_copy = merged_data.copy()
                merged_data_copy['Order Date'] = pd.to_datetime(merged_data_copy[date_column]).dt.date

                daily_sales = (
                    merged_data_copy[['Order Date', 'Order/adjustment ID', 'Quantity', 'Total settlement amount']]
                    .drop_duplicates(subset=['Order/adjustment ID'])
                    .groupby('Order Date', as_index=False)
                    .agg(
                        Daily_Quantity=('Quantity', 'sum') if 'Quantity' in merged_data_copy.columns else ('Order/adjustment ID', 'count'),
                        Daily_Orders=('Order/adjustment ID', 'nunique'),
                        Daily_Revenue=('Total settlement amount', 'sum')
                    )
                )
            except:
                daily_sales = pd.DataFrame({
                    'Order Date': ['Data tidak tersedia'],
                    'Daily Quantity': [0],
                    'Daily Orders': [0],
                    'Daily Revenue': [0]
                })
        else:
            daily_sales = pd.DataFrame({
                'Order Date': ['Kolom tanggal tidak ditemukan'],
                'Daily Quantity': [0],
                'Daily Orders': [0],
                'Daily Revenue': [0]
            })
        
        # Produk terbaik berdasarkan profit
        top_products = (
            unique_orders
            .groupby('Product Name', as_index=False)
            .agg(
                TotalQty=('Quantity', 'sum'),
                Revenue=('Total settlement amount', 'sum')
            )
            .assign(
                Cost=lambda d: d['Product Name'].map(lambda x: self.get_product_cost(x, cost_data)),
                Total_Cost=lambda d: d['TotalQty'] * d['Cost'],
                Profit=lambda d: d['Revenue'] - d['Total_Cost'],
                Profit_Margin=lambda d: (d['Profit'] / d['Revenue'] * 100).round(2)
            )
            .nlargest(10, 'Profit')
        )
        
        # Buat penulis Excel
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            workbook = writer.book
            
            # Tentukan format
            title_format = workbook.add_format({
                'bold': True, 'font_size': 16, 'align': 'center',
                'bg_color': '#4472C4', 'font_color': 'white'
            })
            
            header_format = workbook.add_format({
                'bold': True, 'font_size': 12,
                'bg_color': '#D9E2F3', 'border': 1
            })
            
            currency_format = workbook.add_format({
                'num_format': '#,##0', 'border': 1
            })
            
            number_format = workbook.add_format({
                'num_format': '#,##0', 'border': 1
            })
            
            percent_format = workbook.add_format({
                'num_format': '0.00%', 'border': 1
            })
            
            # Format tambahan untuk laporan yang lebih profesional
            subtitle_format = workbook.add_format({
                'bold': True, 'font_size': 14, 'align': 'left',
                'bg_color': '#E7E6E6', 'border': 1
            })
            
            info_format = workbook.add_format({
                'font_size': 11, 'align': 'left',
                'bg_color': '#F2F2F2', 'border': 1
            })
            
            highlight_format = workbook.add_format({
                'bold': True, 'font_size': 12, 'align': 'center',
                'bg_color': '#FFD700', 'border': 1
            })
            
            # Lembar ringkasan
            overview_sheet = workbook.add_worksheet('Ringkasan')
            overview_sheet.set_column('A:B', 25)
            overview_sheet.set_column('C:C', 20)
            
            row = 0
            overview_sheet.merge_range(f'A{row+1}:C{row+1}', 'LAPORAN PENJUALAN & ANALISIS PROFIT', title_format)
            row += 2
            
            # Rentang tanggal
            if date_column and date_column in merged_data.columns:
                try:
                    date_range_start = pd.to_datetime(merged_data[date_column]).min()
                    date_range_end = pd.to_datetime(merged_data[date_column]).max()
                except:
                    date_range_start = datetime.now()
                    date_range_end = datetime.now()
            else:
                date_range_start = datetime.now()
                date_range_end = datetime.now()
            
            overview_sheet.write(row, 0, f'Periode:', header_format)
            overview_sheet.write(row, 1, f'{date_range_start.strftime("%d/%m/%Y")} - {date_range_end.strftime("%d/%m/%Y")}')
            row += 1
            
            overview_sheet.write(row, 0, f'Dibuat:', header_format)
            overview_sheet.write(row, 1, f'{datetime.now().strftime("%d %B %Y %H:%M")}')
            row += 3
            
            # Metrik kunci
            overview_sheet.write(row, 0, 'RINGKASAN PENJUALAN & PROFIT', header_format)
            row += 1
            overview_sheet.write(row, 0, 'Total Pesanan:')
            overview_sheet.write(row, 1, total_orders, number_format)
            row += 1
            overview_sheet.write(row, 0, 'Total Kuantitas:')
            overview_sheet.write(row, 1, total_qty, number_format)
            row += 1
            overview_sheet.write(row, 0, 'Total Pendapatan:')
            overview_sheet.write(row, 1, total_revenue, currency_format)
            row += 1
            overview_sheet.write(row, 0, 'Total Biaya:')
            overview_sheet.write(row, 1, total_cost, currency_format)
            row += 1
            overview_sheet.write(row, 0, 'Total Profit:')
            overview_sheet.write(row, 1, total_profit, currency_format)
            row += 1
            overview_sheet.write(row, 0, 'Bagian 60%:')
            overview_sheet.write(row, 1, total_share_60, currency_format)
            row += 1
            overview_sheet.write(row, 0, 'Bagian 40%:')
            overview_sheet.write(row, 1, total_share_40, currency_format)
            row += 2
            
            # Hitung metrik tambahan
            avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
            avg_profit_per_order = total_profit / total_orders if total_orders > 0 else 0
            overall_profit_margin = (total_profit / total_revenue * 100) if total_revenue > 0 else 0
            
            overview_sheet.write(row, 0, 'Nilai Rata-rata Pesanan:')
            overview_sheet.write(row, 1, avg_order_value, currency_format)
            row += 1
            overview_sheet.write(row, 0, 'Rata-rata Profit per Pesanan:')
            overview_sheet.write(row, 1, avg_profit_per_order, currency_format)
            row += 1
            overview_sheet.write(row, 0, 'Margin Profit Keseluruhan:')
            overview_sheet.write(row, 1, overall_profit_margin / 100, percent_format)
            row += 2
            
            # Informasi tambahan
            overview_sheet.write(row, 0, 'INFORMASI TAMBAHAN', subtitle_format)
            row += 1
            overview_sheet.write(row, 0, 'Total SKU:')
            overview_sheet.write(row, 1, len(summary_data), info_format)
            row += 1
            overview_sheet.write(row, 0, 'SKU dengan Profit > 0:')
            profitable_sku = len(summary_data[summary_data['Profit'] > 0])
            overview_sheet.write(row, 1, profitable_sku, info_format)
            row += 1
            overview_sheet.write(row, 0, 'SKU dengan Margin > 20%:')
            high_margin_sku = len(summary_data[summary_data['Profit Margin %'] > 20])
            overview_sheet.write(row, 1, high_margin_sku, info_format)
            row += 1
            overview_sheet.write(row, 0, 'SKU dengan Margin < 10%:')
            low_margin_sku = len(summary_data[summary_data['Profit Margin %'] < 10])
            overview_sheet.write(row, 1, low_margin_sku, info_format)
            row += 2
            
            # Catatan penting
            overview_sheet.write(row, 0, 'CATATAN PENTING', subtitle_format)
            row += 1
            overview_sheet.write(row, 0, '• Data revenue diambil dari income.xlsx (data akurat)', info_format)
            overview_sheet.write(row, 1, '', info_format)
            row += 1
            overview_sheet.write(row, 0, '• Analisis affiliate vs toko tersedia di lembar terpisah', info_format)
            overview_sheet.write(row, 1, '', info_format)
            row += 1
            overview_sheet.write(row, 0, '• Breakdown komisi & fee detail di lembar terpisah', info_format)
            overview_sheet.write(row, 1, '', info_format)
            
            # =================================================================
            # ANALISIS AFFILIATE VS TOKO
            # =================================================================
            
            # Ambil data income untuk analisis affiliate
            if 'income_data' in st.session_state and st.session_state.income_data is not None:
                income = st.session_state.income_data
                
                # Refund Analysis
                refund_df = income[income['Customer refund'] < 0]
                refunded_ids = set(refund_df['Order/adjustment ID'].unique())
                
                # Affiliate vs Store Analysis
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
                
                # Buat lembar Analisis Affiliate vs Toko
                affiliate_sheet = workbook.add_worksheet('Analisis Affiliate vs Toko')
                affiliate_sheet.set_column('A:B', 30)
                affiliate_sheet.set_column('C:D', 20)
                
                row = 0
                affiliate_sheet.merge_range(f'A{row+1}:D{row+1}', 'ANALISIS AFFILIATE VS TOKO', title_format)
                row += 2
                
                # Refund Analysis
                affiliate_sheet.write(row, 0, 'ANALISIS REFUND', header_format)
                row += 1
                affiliate_sheet.write(row, 0, 'Total Order Refund:')
                affiliate_sheet.write(row, 1, refund_df['Order/adjustment ID'].nunique(), number_format)
                row += 1
                affiliate_sheet.write(row, 0, 'Total Nilai Refund:')
                affiliate_sheet.write(row, 1, abs(refund_df['Customer refund'].sum()), currency_format)
                row += 1
                refund_rate = (len(refunded_ids) / income['Order/adjustment ID'].nunique() * 100) if len(income) > 0 else 0
                affiliate_sheet.write(row, 0, 'Tingkat Refund:')
                affiliate_sheet.write(row, 1, refund_rate / 100, percent_format)
                row += 2
                
                # Affiliate vs Store Comparison
                affiliate_sheet.write(row, 0, 'PERBANDINGAN AFFILIATE VS TOKO', header_format)
                row += 1
                
                # Header untuk tabel perbandingan
                affiliate_sheet.write(row, 0, 'Metrik', header_format)
                affiliate_sheet.write(row, 1, 'Order via Affiliate', header_format)
                affiliate_sheet.write(row, 2, 'Order Toko Langsung', header_format)
                affiliate_sheet.write(row, 3, 'Total', header_format)
                row += 1
                
                affiliate_sheet.write(row, 0, 'Jumlah Order')
                affiliate_sheet.write(row, 1, aff_cnt, number_format)
                affiliate_sheet.write(row, 2, tok_cnt, number_format)
                affiliate_sheet.write(row, 3, aff_cnt + tok_cnt, number_format)
                row += 1
                
                affiliate_sheet.write(row, 0, 'Total Revenue')
                affiliate_sheet.write(row, 1, aff_rev, currency_format)
                affiliate_sheet.write(row, 2, tok_rev, currency_format)
                affiliate_sheet.write(row, 3, aff_rev + tok_rev, currency_format)
                row += 1
                
                affiliate_sheet.write(row, 0, 'Total Fee')
                affiliate_sheet.write(row, 1, aff_fee, currency_format)
                affiliate_sheet.write(row, 2, tok_fee, currency_format)
                affiliate_sheet.write(row, 3, aff_fee + tok_fee, currency_format)
                row += 1
                
                affiliate_sheet.write(row, 0, 'Rata-rata Fee %')
                affiliate_sheet.write(row, 1, aff_pct / 100, percent_format)
                affiliate_sheet.write(row, 2, tok_pct / 100, percent_format)
                affiliate_sheet.write(row, 3, ((aff_fee + tok_fee) / (aff_rev + tok_rev) * 100) / 100, percent_format)
                row += 2
                
                # =================================================================
                # BREAKDOWN KOMISI & FEE
                # =================================================================
                
                # Buat lembar Breakdown Komisi & Fee
                commission_sheet = workbook.add_worksheet('Breakdown Komisi & Fee')
                commission_sheet.set_column('A:B', 30)
                commission_sheet.set_column('C:C', 20)
                
                row = 0
                commission_sheet.merge_range(f'A{row+1}:C{row+1}', 'BREAKDOWN KOMISI & FEE', title_format)
                row += 2
                
                all_cols = ['Dynamic Commission', 'Affiliate commission', 'TikTok Shop commission fee']
                available = [c for c in all_cols if c in base.columns]
                
                if available:
                    commission_sheet.write(row, 0, 'JENIS KOMISI/FEE', header_format)
                    commission_sheet.write(row, 1, 'TOTAL (Rp)', header_format)
                    commission_sheet.write(row, 2, 'PERSENTASE', header_format)
                    row += 1
                    
                    for col in available:
                        total = abs(base[col].sum())
                        percentage = (total / base['Total settlement amount'].sum() * 100) if base['Total settlement amount'].sum() > 0 else 0
                        
                        commission_sheet.write(row, 0, col.replace('commission', 'Komisi').replace('fee', 'Fee'))
                        commission_sheet.write(row, 1, total, currency_format)
                        commission_sheet.write(row, 2, percentage / 100, percent_format)
                        row += 1
                    
                    # Total fees
                    total_fee_all = base['Total fees'].sum()
                    total_percentage = (total_fee_all / base['Total settlement amount'].sum() * 100) if base['Total settlement amount'].sum() > 0 else 0
                    
                    commission_sheet.write(row, 0, 'TOTAL FEE KESELURUHAN', header_format)
                    commission_sheet.write(row, 1, total_fee_all, currency_format)
                    commission_sheet.write(row, 2, total_percentage / 100, percent_format)
                else:
                    commission_sheet.write(row, 0, 'Data breakdown komisi tidak tersedia', header_format)
                
                # =================================================================
                # DETAIL SUMBER ORDER & FEE
                # =================================================================
                
                # Buat lembar Detail Sumber Order & Fee
                order_detail_sheet = workbook.add_worksheet('Detail Sumber Order & Fee')
                order_detail_sheet.set_column('A:A', 20)  # Order ID
                order_detail_sheet.set_column('B:C', 15)  # Revenue columns
                order_detail_sheet.set_column('D:D', 12)  # Fees
                order_detail_sheet.set_column('E:G', 15)  # Commission columns
                order_detail_sheet.set_column('H:H', 12)  # Sumber
                
                row = 0
                order_detail_sheet.merge_range(f'A{row+1}:H{row+1}', 'DETAIL SUMBER ORDER & FEE', title_format)
                row += 2
                
                cols_show = ['Order/adjustment ID', 'Total revenue', 'Total settlement amount', 'Total fees']
                commission_cols = ['Dynamic Commission', 'Affiliate commission', 'TikTok Shop commission fee']
                cols_show.extend([c for c in commission_cols if c in base.columns])
                
                # Prepare display data
                aff_display = aff[cols_show].copy() if not aff.empty else pd.DataFrame()
                tok_display = tok[cols_show].copy() if not tok.empty else pd.DataFrame()
                
                if not aff_display.empty:
                    aff_display['Sumber'] = 'Affiliate'
                if not tok_display.empty:
                    tok_display['Sumber'] = 'Toko'
                
                if not aff_display.empty or not tok_display.empty:
                    df_orders = pd.concat([aff_display, tok_display], ignore_index=True)
                    
                    # Write headers
                    headers = ['Order ID', 'Total Revenue', 'Settlement Amount', 'Total Fees']
                    commission_headers = [c.replace('commission', 'Komisi').replace('fee', 'Fee') for c in commission_cols if c in base.columns]
                    headers.extend(commission_headers)
                    headers.append('Sumber')
                    
                    for i, header in enumerate(headers):
                        order_detail_sheet.write(row, i, header, header_format)
                    row += 1
                    
                    # Write data
                    for _, order_row in df_orders.iterrows():
                        col = 0
                        order_detail_sheet.write(row, col, order_row['Order/adjustment ID'])
                        col += 1
                        order_detail_sheet.write(row, col, order_row['Total revenue'], currency_format)
                        col += 1
                        order_detail_sheet.write(row, col, order_row['Total settlement amount'], currency_format)
                        col += 1
                        order_detail_sheet.write(row, col, order_row['Total fees'], currency_format)
                        col += 1
                        
                        # Commission columns
                        for comm_col in commission_cols:
                            if comm_col in order_row:
                                order_detail_sheet.write(row, col, abs(order_row[comm_col]), currency_format)
                            col += 1
                        
                        order_detail_sheet.write(row, col, order_row['Sumber'])
                        row += 1
                else:
                    order_detail_sheet.write(row, 0, 'Tidak ada data order yang tersedia', header_format)
            
            # Tulis lembar lainnya
            summary_data.to_excel(writer, index=False, sheet_name='Ringkasan per Produk')
            summary_by_sku.to_excel(writer, index=False, sheet_name='Ringkasan per SKU')
            daily_sales.to_excel(writer, index=False, sheet_name='Penjualan Harian')
            top_products.to_excel(writer, index=False, sheet_name='Produk Teratas')
            
            # Daftar biaya produk
            if cost_data:
                cost_df = pd.DataFrame(list(cost_data.items()), columns=["Product Name", "Cost per Unit"])
                cost_df = cost_df.sort_values(by="Product Name")
                cost_df.to_excel(writer, index=False, sheet_name='Daftar Biaya Produk')
        
        output.seek(0)
        return output

    def generate_ai_summary(self, summary_df):
        """Generate AI summary untuk ChatGPT"""
        if st.session_state.merged_data is None:
            return "Data belum diproses."

        unique_orders = st.session_state.merged_data.drop_duplicates(subset=['Order ID'])
        total_r = unique_orders['Total settlement amount'].sum()
        total_cost = summary_df['Total Cost'].sum()
        total_p = total_r - total_cost
        avg_m = summary_df['Profit Margin %'].mean()

        top = summary_df.nlargest(5, 'Profit')[['Product Name', 'Profit', 'Profit Margin %']]

        prompt = f"""
    Kamu adalah Chief Data Scientist e-commerce. Buat laporan strategis 360° dari data berikut:

    📊 Total Pendapatan               : Rp {total_r:,.0f}
    📈 Total Profit                   : Rp {total_p:,.0f}
    📉 Margin Rata-rata               : {avg_m:.1f}%

    5 Produk Ter-Profit:
    {top.to_string(index=False)}

    Deliverables:
    1. Executive summary 3 kalimat
    2. 3 SKU prioritas optimize
    3. 2 pricing strategy SKU margin rendah
    4. 2 saran strategi peningkatan profit
        """

        return prompt 