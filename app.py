import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO
from roboflow import Roboflow

# --- 1. SAYFA VE TEMA AYARLARI ---
st.set_page_config(page_title="Metraj Pro | AI Destekli Analiz", layout="wide", page_icon="🏢")

# Metriklerin beyaz arka planda görünmeme sorununu çözen CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    [data-testid="stMetricValue"] > div { 
        color: #1f1f1f !important; 
        font-weight: bold !important; 
    }
    [data-testid="stMetricLabel"] > div { 
        color: #495057 !important; 
    }
    h1, h2, h3, p, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. YARDIMCI FONKSİYONLAR ---

def run_roboflow_ai(image_path):
    """Roboflow API bağlantısı ve tahmini."""
    try:
        # Paneldeki gerçek Private API Key
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        # Paneldeki Workspace ve Proje ID bilgileri
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model # Dataset Version: 8
        
        prediction = model.predict(image_path, confidence=40).json()
        return prediction.get('predictions', [])
    except Exception as e:
        st.error(f"AI Bağlantı Hatası: {e}")
        return []

def get_dxf_data(path, scale, layers):
    """DXF dosyasından geometri verilerini çeker."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        walls = []
        targets = [l.upper().strip() for l in layers.split(",") if l.strip()]
        
        # LINE ve POLYLINE tiplerini destekler
        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if targets and not any(t in e.dxf.layer.upper() for t in targets):
                continue
            
            pts = []
            if e.dxftype() == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            else:
                pts = [(p[0], p[1]) for p in e.get_points()]

            for i in range(len(pts)-1):
                p1, p2 = pts[i], pts[i+1]
                ln = math.dist(p1, p2) / scale
                if ln > 0.05: # Çok kısa çizgileri yoksay
                    walls.append({
                        "ID": f"W-{len(walls)+1:03d}",
                        "p1": p1, "p2": p2, 
                        "Uzunluk (m)": round(ln, 2),
                        "Layer": e.dxf.layer
                    })
        return walls
    except Exception as e:
        st.error(f"DXF Hatası: {e}")
        return []

# --- 3. ANA UYGULAMA AKIŞI ---

st.sidebar.title("🏢 Kontrol Paneli")
with st.sidebar:
    st.info(f"👤 Kullanıcı: Barış Öker") #
    dxf_file = st.file_uploader("DXF Planını Yükleyin", type=["dxf"])
    target_layer = st.text_input("Hedef Katman (Layer)", "DUVAR")
    unit = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    wall_h = st.number_input("Duvar Yüksekliği (m)", value=2.85, step=0.01)

if dxf_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_file.getbuffer())
        temp_path = tmp.name

    # Ölçek hesaplama
    scale_factor = 100 if unit == "cm" else (1000 if unit == "mm" else 1)
    wall_data = get_dxf_data(temp_path, scale_factor, target_layer)

    if wall_data:
        df = pd.DataFrame(wall_data)
        total_length = df["Uzunluk (m)"].sum()

        # Sonuç Metrikleri
        st.subheader("📊 Analiz Sonuçları")
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Uzunluk", f"{total_length:.2f} m")
        c2.metric("Toplam Alan", f"{(total_length * wall_h):.2f} m²")
        c3.metric("Segment Sayısı", len(wall_data))

        st.divider()

        # Görselleştirme ve AI Analizi
        col_map, col_list = st.columns([2, 1])
        
        with col_map:
            st.write("🖼️ Plan Önizleme")
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            for _, w in df.iterrows():
                ax.plot([w["p1"][0], w["p2"][0]], [w["p1"][1], w["p2"][1]], color="#00d2ff", lw=1.5)
            ax.set_aspect("equal")
            ax.axis("off")
            st.pyplot(fig)

        with col_list:
            st.write("📋 Detaylı Liste")
            st.dataframe(df[["ID", "Uzunluk (m)", "Layer"]], use_container_width=True, hide_index=True)

        # AI Analiz Butonu
        if st.button("🤖 Roboflow AI Analizini Başlat"):
            with st.spinner("AI planı analiz ediyor..."):
                img_buf = BytesIO()
                fig.savefig(img_buf, format='png', bbox_inches='tight', pad_inches=0)
                ai_results = run_roboflow_ai(img_buf)
                
                if ai_results:
                    st.success(f"{len(ai_results)} adet mimari öğe tespit edildi.")
                    for res in ai_results:
                        st.write(f"✅ {res['class']} tespiti - Güven: %{res['confidence']*100:.1f}")
                else:
                    st.warning("Tespit yapılamadı. Modelinizi veya görseli kontrol edin.")

        # Excel Raporu (openpyxl gerektirir)
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df[["ID", "Uzunluk (m)", "Layer"]].to_excel(writer, index=False)
            st.download_button("📊 Excel Raporu İndir", output.getvalue(), f"Metraj_{dxf_file.name}.xlsx")
        except Exception as e:
            st.error(f"Excel Hatası: {e}. Lütfen requirements.txt dosyasına 'openpyxl' ekleyin.")

    os.remove(temp_path)
