import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
from io import BytesIO
from roboflow import Roboflow

# --- TEMA VE GÖRÜNÜRLÜK AYARLARI ---
st.set_page_config(page_title="Metraj Pro | AI Destekli Analiz", layout="wide")

st.markdown("""
    <style>
    /* Metrik kutularındaki yazıların görünür olması için (Siyah yazı) */
    [data-testid="stMetricValue"] > div { color: #1f1f1f !important; font-weight: bold !important; }
    [data-testid="stMetricLabel"] > div { color: #495057 !important; }
    [data-testid="stMetric"] { background-color: #f8f9fa !important; border-radius: 10px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

def run_roboflow_ai(image_path):
    try:
        # Görsel 03b0be'deki gerçek Private API Key
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        # Görsel 03b13b ve 041220'deki proje verileri
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        prediction = model.predict(image_path, confidence=40).json()
        return prediction.get('predictions', [])
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

# --- ANA PANEL ---
st.sidebar.title("🏢 Metraj Paneli")
dxf_up = st.sidebar.file_uploader("DXF Dosyası", type=["dxf"])
layer_sel = st.sidebar.text_input("Katman", "DUVAR")
unit_sel = st.sidebar.selectbox("Birim", ["cm", "mm", "m"])
h_sel = st.sidebar.number_input("Yükseklik (m)", value=2.85)

if dxf_up:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_up.getbuffer())
        t_path = tmp.name

    # DXF Okuma ve Metraj Hesaplama
    doc = ezdxf.readfile(t_path)
    msp = doc.modelspace()
    walls = []
    sc = 100 if unit_sel == "cm" else (1000 if unit_sel == "mm" else 1)

    for e in msp.query('LINE LWPOLYLINE POLYLINE'):
        if layer_sel.upper() in e.dxf.layer.upper():
            if e.dxftype() == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            else:
                pts = [(p[0], p[1]) for p in e.get_points()]
            
            for i in range(len(pts)-1):
                ln = math.dist(pts[i], pts[i+1]) / sc
                if ln > 0.05:
                    walls.append({"No": len(walls)+1, "Uzunluk (m)": round(ln, 2)})

    if walls:
        df = pd.DataFrame(walls)
        total_l = df["Uzunluk (m)"].sum()

        st.subheader("🚀 Analiz Sonuçları")
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Uzunluk", f"{total_l:.2f} m")
        c2.metric("Toplam Alan", f"{(total_l * h_sel):.2f} m²")
        c3.metric("Parça Sayısı", len(walls))

        # Çizim Alanı
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0e1117')
        # ... (Çizim kodları buraya)
        st.pyplot(fig)

        if st.button("🤖 AI Analizini Başlat"):
            with st.spinner("AI taranıyor..."):
                img_path = "plan_img.png"
                fig.savefig(img_path)
                results = run_roboflow_ai(img_path)
                if results:
                    st.success(f"AI {len(results)} nesne tespit etti.")
                else:
                    st.warning("Tespit yapılamadı.")

        # Excel Kaydetme
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📊 Excel İndir", output.getvalue(), "Metraj_Raporu.xlsx")

    os.remove(t_path)
