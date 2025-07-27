import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from data_processor import IncomeApp

# Fungsi utama untuk tab Analisis Lengkap

def show_full_analysis_tab():
    st.markdown("## 🧠 Analisis Lengkap Seluruh Data")
    mode = st.session_state.get("mode", "Single Data")
    merged_new = st.session_state.get("merged_data")
    merged_old = st.session_state.get("old_merged")
    summary_new = st.session_state.get("summary_data")
    summary_old = st.session_state.get("old_summary")

    # Gabungkan data lama+baru jika mode Compare, jika tidak pakai data baru saja
    if mode == "Compare Lama vs Baru" and merged_old is not None and merged_new is not None:
        merged = pd.concat([merged_old, merged_new], ignore_index=True)
        if summary_old is not None and summary_new is not None:
            summary = pd.concat([summary_old, summary_new], ignore_index=True)
        else:
            summary = summary_new
    elif merged_new is not None:
        merged = merged_new.copy()
        summary = summary_new
    else:
        merged = None
        summary = None

    if merged is None or merged.empty:
        st.info("ℹ️ Silakan proses dan upload data terlebih dahulu.")
        return

    # --- Otomatis deteksi kolom tanggal, produk, qty ---
    possible_date_cols = [
        'Order created time(UTC)', 'Order creation time', 'Order Creation Time', 
        'Creation Time', 'Date', 'Order Date', 'Order created time', 'Created time'
    ]
    date_col = next((col for col in possible_date_cols if col in merged.columns), None)
    if date_col:
        merged['Order Date'] = pd.to_datetime(merged[date_col]).dt.date
    else:
        merged['Order Date'] = None

    product_col = 'Product Name' if 'Product Name' in merged.columns else None
    qty_col = 'Quantity' if 'Quantity' in merged.columns else None
    if not qty_col:
        merged['Qty'] = 1
        qty_col = 'Qty'
    var_col = 'Variation' if 'Variation' in merged.columns else None

    # PIE CHART: Penjualan per Produk
    st.markdown("### 🥧 Distribusi Penjualan per Produk")
    if product_col and qty_col:
        pie_df = merged.groupby(product_col)[qty_col].sum().reset_index()
        fig_pie = px.pie(pie_df, names=product_col, values=qty_col, title='Proporsi Penjualan per Produk')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.warning('Kolom produk/qty tidak ditemukan di data.')

    # TIMELINE: Produk terjual per hari
    st.markdown("### 📅 Timeline Penjualan Harian")
    if product_col and qty_col and merged['Order Date'].notnull().all():
        timeline_group = merged.groupby(['Order Date', product_col])[qty_col].sum().reset_index()
        fig_timeline = px.line(timeline_group, x='Order Date', y=qty_col, color=product_col, markers=True,
                               title='Timeline Penjualan per Produk')
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.warning('Kolom tanggal/produk/qty tidak ditemukan di data.')

    # TABEL: Produk Terlaris
    st.markdown("### 🏆 Produk Terlaris")
    if product_col and qty_col:
        top_products = merged.groupby(product_col)[qty_col].sum().reset_index().sort_values(qty_col, ascending=False)
        st.dataframe(top_products, use_container_width=True)
    else:
        st.warning('Kolom produk/qty tidak ditemukan di data.')

    # TABEL: Detail Penjualan per Produk per Tanggal
    st.markdown("### 📋 Detail Penjualan per Produk per Tanggal")
    if product_col and qty_col and merged['Order Date'].notnull().all():
        detail_table = merged.groupby(['Order Date', product_col])[qty_col].sum().reset_index()
        st.dataframe(detail_table, use_container_width=True)
    else:
        st.warning('Kolom tanggal/produk/qty tidak ditemukan di data.')

    # RINGKASAN OTOMATIS BISNIS
    st.markdown("### 🤖 Ringkasan & Insight Otomatis")
    try:
        if summary is not None and not summary.empty:
            # Produk terlaris
            top_n = summary.sort_values('TotalQty', ascending=False).head(5)
            st.subheader("Produk Terlaris (Top 5)")
            for idx, row in top_n.iterrows():
                var_str = f" / {row['Variation']}" if 'Variation' in row and pd.notnull(row['Variation']) else ''
                st.markdown(f"- **{row['Product Name']}**{var_str}: {row['TotalQty']} pcs, Revenue: Rp {row['Revenue']:,.0f}, Profit: Rp {row['Profit']:,.0f}")

            # Produk penjualan terendah
            low_n = summary.sort_values('TotalQty', ascending=True).head(3)
            st.subheader("Produk Penjualan Terendah (Butuh Perhatian)")
            for idx, row in low_n.iterrows():
                var_str = f" / {row['Variation']}" if 'Variation' in row and pd.notnull(row['Variation']) else ''
                st.markdown(f"- **{row['Product Name']}**{var_str}: {row['TotalQty']} pcs, Revenue: Rp {row['Revenue']:,.0f}, Profit: Rp {row['Profit']:,.0f}")

            # Insight margin/profit
            avg_margin = summary['Profit Margin %'].mean()
            st.info(f"Margin profit rata-rata: {avg_margin:.2f}%")
            low_margin = summary[summary['Profit Margin %'] < avg_margin].sort_values('Profit Margin %').head(3)
            if not low_margin.empty:
                st.warning("SKU dengan margin rendah:")
                for idx, row in low_margin.iterrows():
                    var_str = f" / {row['Variation']}" if 'Variation' in row and pd.notnull(row['Variation']) else ''
                    st.markdown(f"- **{row['Product Name']}**{var_str}: Margin {row['Profit Margin %']:.2f}%")

            # Saran strategi sederhana
            st.markdown("---")
            st.markdown("#### 💡 Saran Strategi Bisnis:")
            st.markdown("- Fokuskan promosi pada produk terlaris dan variasi yang terbukti laku.")
            st.markdown("- Evaluasi ulang harga/biaya pada SKU dengan margin rendah.")
            st.markdown("- Cek stok dan review deskripsi produk yang penjualannya rendah.")
            st.markdown("- Lakukan bundling/cross-sell untuk produk yang kurang laku.")
        else:
            st.info("Data summary tidak tersedia untuk insight.")
    except Exception as e:
        st.info("Insight otomatis belum tersedia untuk data ini.") 

    # --- PREDIKSI PENJUALAN ---
    st.markdown("### 🔮 Prediksi Penjualan")
    import numpy as np
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    from sklearn.ensemble import RandomForestRegressor

    produk_list = summary['Product Name'].unique().tolist() if summary is not None else []
    produk_pilihan = st.selectbox("Pilih produk untuk prediksi", ["(Total Semua Produk)"] + produk_list)
    periode = st.selectbox("Pilih periode prediksi", ["Bulanan", "Mingguan"])

    if product_col and qty_col and merged['Order Date'].notnull().all():
        df_pred = merged.copy()
        if produk_pilihan != "(Total Semua Produk)":
            df_pred = df_pred[df_pred[product_col] == produk_pilihan]
        df_pred['Order Date'] = pd.to_datetime(df_pred['Order Date'])
        if periode == "Bulanan":
            df_pred['Periode'] = df_pred['Order Date'].dt.to_period('M').dt.to_timestamp()
        else:
            df_pred['Periode'] = df_pred['Order Date'] - pd.to_timedelta(df_pred['Order Date'].dt.dayofweek, unit='d')
        agg = df_pred.groupby('Periode')[qty_col].sum().reset_index()
        agg = agg.sort_values('Periode')

        if len(agg) >= 3:
            X = np.arange(len(agg)).reshape(-1, 1)
            y = agg[qty_col].values
            # Linear Regression
            model_lin = LinearRegression().fit(X, y)
            pred_lin = model_lin.predict(np.append(X, [[len(agg)]], axis=0))
            # Polynomial Regression (degree 2)
            poly = PolynomialFeatures(degree=2)
            X_poly = poly.fit_transform(X)
            model_poly = LinearRegression().fit(X_poly, y)
            pred_poly = model_poly.predict(poly.transform(np.append(X, [[len(agg)]], axis=0)))
            # Random Forest
            model_rf = RandomForestRegressor(n_estimators=100, random_state=42)
            model_rf.fit(X, y)
            pred_rf = model_rf.predict(np.append(X, [[len(agg)]], axis=0))
            # Error (MSE) untuk model historis
            from sklearn.metrics import mean_squared_error
            mse_lin = mean_squared_error(y, pred_lin[:-1])
            mse_poly = mean_squared_error(y, pred_poly[:-1])
            mse_rf = mean_squared_error(y, pred_rf[:-1])
            mse_dict = {'Linear': mse_lin, 'Polynomial': mse_poly, 'Random Forest': mse_rf}
            best_model = min(mse_dict, key=mse_dict.get)
            # Grafik
            import plotly.graph_objs as go
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=agg['Periode'], y=y, mode='lines+markers', name='Aktual'))
            fig.add_trace(go.Scatter(x=np.append(agg['Periode'], [agg['Periode'].iloc[-1] + (agg['Periode'].iloc[-1] - agg['Periode'].iloc[-2])]), y=pred_lin, mode='lines+markers', name='Linear'))
            fig.add_trace(go.Scatter(x=np.append(agg['Periode'], [agg['Periode'].iloc[-1] + (agg['Periode'].iloc[-1] - agg['Periode'].iloc[-2])]), y=pred_poly, mode='lines+markers', name='Polynomial'))
            fig.add_trace(go.Scatter(x=np.append(agg['Periode'], [agg['Periode'].iloc[-1] + (agg['Periode'].iloc[-1] - agg['Periode'].iloc[-2])]), y=pred_rf, mode='lines+markers', name='Random Forest'))
            fig.update_layout(title=f"Prediksi Penjualan {'Total' if produk_pilihan == '(Total Semua Produk)' else produk_pilihan} ({periode})", xaxis_title="Periode", yaxis_title="Qty Terjual")
            st.plotly_chart(fig, use_container_width=True)
            # Insight otomatis
            pred_next = {'Linear': pred_lin[-1], 'Polynomial': pred_poly[-1], 'Random Forest': pred_rf[-1]}[best_model]
            last_real = y[-1]
            delta = pred_next - last_real
            pct = (delta / last_real * 100) if last_real != 0 else 0
            st.info(f"Model terbaik: **{best_model}** (MSE: {mse_dict[best_model]:.2f})")
            if pct > 10:
                st.success(f"Prediksi penjualan periode berikutnya (oleh {best_model}) akan NAIK sekitar {pct:.1f}% dibanding periode terakhir.")
            elif pct < -10:
                st.warning(f"Prediksi penjualan periode berikutnya (oleh {best_model}) akan TURUN sekitar {abs(pct):.1f}% dibanding periode terakhir.")
            else:
                st.info(f"Prediksi penjualan periode berikutnya (oleh {best_model}) relatif stabil.")
        else:
            st.info("Data historis belum cukup untuk prediksi (minimal 3 periode).")
    else:
        st.info("Data tanggal/produk/qty belum lengkap untuk prediksi.") 