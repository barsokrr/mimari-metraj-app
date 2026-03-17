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
from PIL import Image, ImageDraw

# --- 1. SAYFA VE TEMA AYARLARI ---
st.set_page_config(page_title="Metraj Pro | Orijinal Plan Analizi", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetric"] { background-color: #ffffff !important; border-radius: 12px; padding: 15px; }
    [data-testid="stMetricValue"] > div { color: #1f1f1f !important; font-weight: bold !important; }
    [data-testid="stMetricLabel"] > div { color: #495057 !important; }
    h1, h2, h3, p, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. FONKSİYONLAR ---

def run_roboflow_ai(image_bytes):
    try:
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_img:
            tmp_img.write(image_bytes.getvalue())
            tmp_img_path = tmp_img.name
            
        prediction = model.predict(tmp_img_path, confidence=40).json()
        os.remove(tmp_img_path)
        return prediction.get('predictions', [])
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

def get_dxf_elements(path, scale, target_layer):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        walls = []
        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if target_layer.upper() in e.dxf.layer.upper():
                pts = [(p[0], p[1]) for p in ([(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)] if e.dxftype() == "LINE" else e.get_points())]
                for i in range(len(pts)-1):
                    ln = math.dist(pts[i], pts[i+1]) / scale
                    if ln > 0.15: # Hatalı küçük çizgileri filtrele
                        walls.append({"p1": pts[i], "p2": pts[i+1], "Uzunluk": round(ln, 2), "Layer": e.dxf.layer})
        return walls
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}"); return []

# --- 3. ARAYÜZ ---
st.sidebar.title("🏢 Kontrol Paneli")
dxf_file = st.sidebar.file_uploader("DXF Planını Yükleyin", type=["dxf"])
target_layer = st.sidebar.text_input("Hedef Katman", "DUVAR")
unit = st.sidebar.selectbox("Birim", ["cm", "mm", "m"])
wall_h = st.sidebar.number_input("Yükseklik (m)", value=2.85)

if dxf_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_file.getbuffer())
        temp_path = tmp.name

    scale = 100 if unit == "cm" else (1000 if unit == "mm" else 1)
    data = get_dxf_elements(temp_path, scale, target_layer)

    if data:
        df = pd.DataFrame(data)
        total_l = df["Uzunluk"].sum()

        # METRİKLER
        c1, c2, c3 = st.columns(3)
        c1.metric("Toplam Uzunluk", f"{total_l:.2f} m")
        c2.metric("Toplam Alan", f"{(total_l * wall_h):.2f} m²")
        c3.metric("Segment Sayısı", len(data))

        # PLAN GÖRÜNTÜLEME
        st.subheader("🖼️ Orijinal Plan ve AI Analizi")
        fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
        for w in data:
            ax.plot([w["p1"][0], w["p2"][0]], [w["p1"][1], w["p2"][1]], color="#00d2ff", lw=1.5)
        ax.set_aspect("equal")
        ax.axis("off")
        
        # Orijinal planı imaj olarak belleğe al
        img_buf = BytesIO()
        fig.savefig(img_buf, format='png', bbox_inches='tight', pad_inches=0)
        img_buf.seek(0)
        
        col_left, col_right = st.columns([2, 1])
        
        with col_left:
            if st.button("🤖 AI İle Planı Tara ve İşaretle"):
                results = run_roboflow_ai(img_buf)
                if results:
                    # Orijinal plan üzerine AI kutularını çiz
                    plan_img = Image.open(img_buf).convert("RGB")
                    draw = ImageDraw.Draw(plan_img)
                    for res in results:
                        x, y, w, h = res['x'], res['y'], res['width'], res['height']
                        draw.rectangle([x-w/2, y-h/2, x+w/2, y+h/2], outline="red", width=3)
                    st.image(plan_img, caption="AI Tarafından İşaretlenmiş Orijinal Plan", use_container_width=True)
                else:
                    st.image(img_buf, caption="Orijinal Plan Görünümü", use_container_width=True)
            else:
                st.image(img_buf, caption="Orijinal Plan Görünümü", use_container_width=True)

        with col_right:
            st.write("📋 Metraj Listesi")
            st.dataframe(df[["Uzunluk", "Layer"]], use_container_width=True)

    os.remove(temp_path)
