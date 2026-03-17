import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
from io import BytesIO
from roboflow import Roboflow

# --- 1. GÖRÜNÜRLÜK VE TEMA AYARLARI ---
st.set_page_config(page_title="Metraj Pro | AI Destekli Analiz", layout="wide")

st.markdown("""
    <style>
    /* Metrik kutularındaki beyaz üzerine beyaz yazı sorununu çözer */
    [data-testid="stMetricValue"] > div { color: #1f1f1f !important; font-weight: bold !important; }
    [data-testid="stMetricLabel"] > div { color: #495057 !important; }
    [data-testid="stMetric"] { background-color: #f8f9fa !important; border-radius: 12px; padding: 15px; border: 1px solid #e0e0e0; }
    h1, h2, h3 { color: #ffffff !important; }
    .stApp { background-color: #0e1117; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. ANALİZ FONKSİYONLARI ---

def run_roboflow_ai(image_path):
    try:
        # image_03b0be.jpg dosyasından alınan gerçek Private API Key'iniz
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        # image_041220.jpg dosyasından alınan Workspace ve Proje ID
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        
        prediction = model.predict(image_path, confidence=40).json()
        return prediction.get('predictions', [])
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

# --- 3. ANA ARAYÜZ ---
st.title("🏢 Metraj Kontrol Paneli")
st.sidebar.info(f"👤 Kullanıcı: Barış Öker")

with st.sidebar:
    dxf_up = st.file_uploader("DXF Dosyası Seçin", type=["dxf"])
    layer_sel = st.text_input("Katman (Layer)", "DUVAR")
    unit_sel = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    h_sel = st.number_input("Yükseklik (m)", value=2.85)

if dxf_up:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_up.getbuffer())
        t_path = tmp.name

    try:
        doc = ezdxf.readfile(t_path)
        msp = doc.modelspace()
        walls = []
        # Birim ölçeklendirme
        sc = 100 if unit_sel == "cm" else (1000 if unit_sel == "mm" else 1)

        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if layer_sel.upper() in e.dxf.layer.upper():
                if e.dxftype() == "LINE":
                    pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
                else:
                    pts = [(p[0], p[1]) for p in e.get_points()]
                
                for i in range(len(pts)-1):
                    dist = math.dist(pts[i], pts[i+1]) / sc
                    if dist > 0.05:
                        walls.append({"ID": f"W-{len(walls)+1}", "Uzunluk (m)": round(dist, 2)})

        if walls:
            df = pd.DataFrame(walls)
            total_l = df["Uzunluk (m)"].sum()

            # Metrikler
            c1, c2, c3 = st.columns(3)
            c1.metric("Net Uzunluk", f"{total_l:.2f} m")
            c2.metric("Toplam Alan", f"{(total_l * h_sel):.2f} m²")
            c3.metric("Aks Sayısı", len(walls))

            # Çizim ve AI Analizi
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            # (Burada çizim kodları çalışır...)
            ax.set_aspect("equal")
            ax.axis("off")
            st.pyplot(fig)

            if st.button("🤖 Roboflow AI Analizini Başlat"):
                with st.spinner("AI taranıyor..."):
                    img_temp = "ai_analysis.png"
                    fig.savefig(img_temp, bbox_inches='tight', pad_inches=0)
                    results = run_roboflow_ai(img_temp)
                    if results:
                        st.success(f"{len(results)} bölge tespit edildi.")
                    else:
                        st.warning("Belirgin bir tespit yapılamadı.")

            # Excel Çıktısı (openpyxl gerektirir)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📊 Excel Raporu İndir", output.getvalue(), f"Metraj_{dxf_up.name}.xlsx")

    except Exception as e:
        st.error(f"Bir hata oluştu: {e}")
    finally:
        os.remove(t_path)
