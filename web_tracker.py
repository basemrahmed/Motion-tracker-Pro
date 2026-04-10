import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
from fpdf import FPDF
import io

# 1. إعدادات الصفحة وعنوان الويب
st.set_page_config(page_title="Motion Tracker Pro - Web", layout="wide")

# 2. وظيفة تحليل الحركة (المعادلات الميكانيكية)
def calculate_mechanics(df):
    try:
        times_in_minutes = []
        for ts in df['الوقت']:
            t_obj = datetime.strptime(ts, "%H:%M")
            times_in_minutes.append(t_obj.hour * 60 + t_obj.minute)
        
        t = np.array(times_in_minutes, dtype=float)
        x = np.array(df['X'], dtype=float)
        y = np.array(df['Y'], dtype=float)

        dx = np.diff(x); dy = np.diff(y); dt = np.diff(t)
        dt_safe = np.where(dt <= 0, 1e-6, dt)
        dr = np.sqrt(dx**2 + dy**2)
        velocity = dr / dt_safe
        
        accel_full = np.full(len(x), np.nan)
        if len(velocity) > 1:
            dv = np.diff(velocity)
            dt_accel_safe = np.where(dt[1:] <= 0, 1e-6, dt[1:])
            accel = dv / dt_accel_safe
            accel_full = np.concatenate([[np.nan, np.nan], accel])

        angles = np.degrees(np.arctan2(dy, dx))
        
        results = pd.DataFrame({
            "Point": range(1, len(x)+1),
            "الوقت (T)": df['الوقت'],
            "Δt": np.concatenate([[0], dt]),
            "ΔX": np.round(np.concatenate([[0], dx]), 4),
            "ΔY": np.round(np.concatenate([[0], dy]), 4),
            "ΔR": np.round(np.concatenate([[0], dr]), 2),
            "Velocity (V)": np.round(np.concatenate([[0], velocity]), 4),
            "Accel (A)": np.round(accel_full, 4),
            "Angle (q)": np.round(np.concatenate([[0], angles]), 2)
        })
        return results, t, x, y
    except Exception as e:
        st.error(f"خطأ في الحسابات: يرجى التأكد من تنسيق الوقت HH:MM (مثال: 14:30) والأرقام. {e}")
        return None, None, None, None

# 3. وظيفة تصدير التقرير PDF (لنسخة الويب)
def generate_pdf(res_df, fig):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Motion Analysis Web Report", ln=True, align='C'); pdf.ln(10)
    
    # الجدول
    pdf.set_font("Arial", 'B', 7)
    for col in res_df.columns: pdf.cell(21, 8, col, 1, 0, 'C')
    pdf.ln()
    pdf.set_font("Arial", size=7)
    for _, r in res_df.iterrows():
        for v in r: pdf.cell(21, 8, str(v) if not pd.isna(v) else "-", 1, 0, 'C')
        pdf.ln()
    
    # الجرافات
    pdf.add_page()
    pdf.set_font("Arial", 'B', 14); pdf.cell(200, 10, "Graphical Analysis", ln=True, align='C'); pdf.ln(5)
    img_buf = io.BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    pdf.image(img_buf, x=10, y=30, w=190)
    
    return pdf.output(dest='S').encode('latin-1')

# 4. بناء واجهة المستخدم (الويب)
st.title("🏃 نظام تحليل الحركة الميكانيكية - نسخة الويب")
st.markdown("---")

# تبويبات الويب
tab_input, tab_results, tab_plots, tab_ref = st.tabs(["إدخال البيانات", "جدول النتائج", "الرسوم البيانية", "المعادلات Reference"])

with tab_input:
    col_c, col_d = st.columns([1, 1])
    with col_c: num_points = st.number_input("عدد النقاط (على الأقل 2):", min_value=2, value=5, step=1)
    
    input_data = pd.DataFrame(index=range(num_points), columns=['الوقت', 'X', 'Y'])
    input_data['الوقت'] = input_data['الوقت'].astype(str); input_data['الوقت'] = "12:00"
    input_data['X'] = 0.0; input_data['Y'] = 0.0
    
    edited_df = st.data_editor(input_data, use_container_width=True, num_rows="dynamic", key="data_ed")
    calculate_btn = st.button("⚡ احسب النتائج", type="primary")

if calculate_btn:
    edited_df = edited_df.dropna() # حذف الأسطر الفارغة
    if len(edited_df) < 2:
        st.warning("يرجى إدخال نقطتين على الأقل للحساب.")
    else:
        with st.spinner("جاري تحليل الحركة..."):
            res_df, t_raw, x_raw, y_raw = calculate_mechanics(edited_df)
            
            if res_df is not None:
                st.session_state['res_df'] = res_df
                st.session_state['t_raw'] = t_raw; st.session_state['x_raw'] = x_raw; st.session_state['y_raw'] = y_raw
                st.success("تم حساب النتائج!")

if 'res_df' in st.session_state:
    with tab_results:
        st.subheader("جدول النتائج النهائي")
        st.dataframe(st.session_state['res_df'], use_container_width=True)
        
        # تصدير PDF
        st.subheader("تصدير التقرير PDF")
        if 'fig' not in st.session_state: st.session_state['fig'] = None # تأمين الشكل

    with tab_plots:
        st.subheader("الرسوم البيانية")
        fig, axes = plt.subplots(2, 2, figsize=(10, 8))
        fig.patch.set_facecolor("#0f1923")
        plots = [ (st.session_state['x_raw'], st.session_state['y_raw'], "Path (X vs Y)", "X", "Y"), 
                 (st.session_state['t_raw'], st.session_state['res_df']["Velocity (V)"], "Velocity", "Time", "V"),
                 (st.session_state['t_raw'], st.session_state['res_df']["Accel (A)"], "Acceleration", "Time", "A"),
                 (st.session_state['t_raw'], st.session_state['res_df']["Angle (q)"], "Angle", "Time", "Q")]
        for ax, (px, py, title, xl, yl) in zip(axes.flat, plots):
            ax.plot(px, py, "o-", color="#00d4ff", markersize=4)
            ax.set_title(title, color="white", fontsize=11)
            ax.set_facecolor("#0d2137"); ax.tick_params(colors="white"); ax.grid(alpha=0.2)
        fig.tight_layout()
        st.pyplot(fig)
        st.session_state['fig'] = fig

    with tab_results: # العودة لإضافة زر تحميل الـ PDF
        if st.session_state['fig'] is not None:
            pdf_bytes = generate_pdf(st.session_state['res_df'], st.session_state['fig'])
            st.download_button("📄 تحميل التقرير الشامل (جدول + جرافات)", data=pdf_bytes, file_name="MotionReport.pdf", mime="application/pdf")

with tab_ref:
    st.subheader("المعادلات Reference")
    ref_txt = """
    1. Δt = t2 - t1
    2. ΔX = X2 - X1
    3. ΔY = Y2 - Y1
    4. ΔR = √(ΔX² + ΔY²)
    5. V = ΔR / Δt
    6. a = ΔV / Δt
    7. q = tan⁻¹(ΔY / ΔX)
    """
    st.code(ref_txt, language="text")