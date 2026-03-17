import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- AYARLAR ---
st.set_page_config(page_title="Hassas Metraj Pro", layout="wide")

def get_all_layers(dxf_path):
    try:
        doc = ezdxf.readfile(dxf_path)
        return sorted([layer.dxf.name for layer in doc.layers])
    except: return ["0"]

def get_dxf_geometry(dxf_path, target_layer, scale):
    """DXF'den sadece seçili katmandaki gerçek çizgileri çeker."""
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        lines = []
        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if e.dxf.layer == target_layer:
                # Koordinat ayıklama
                if e.dxftype() == "LINE":
                    pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
                else:
                    pts = [(p[0], p[1]) for p in e.get_points()]
                
                for i in range(len(pts)-1):
                    length = math.dist(pts[i], pts[i+1]) / scale
                    lines.append({"p1": pts[i], "p2": pts[i+1], "Uzunluk": round(length, 2)})
        return lines
    except: return []

# --- ARAYÜZ ---
st.title("🏗️ Profesyonel DXF Metraj Analizi")

dxf_file = st.sidebar.file_uploader("DXF Dosyası", type=["dxf"])

if dxf_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_file.getbuffer())
        tmp_path = tmp.name

    layers = get_all_layers(tmp_path)
    
    # KATMAN SEÇİMİ (BUTON GRUBU GİBİ SİDEBAR'DA)
    st.sidebar.subheader("📂 Katmanlar")
    selected_layer = st.sidebar.radio("Analiz Edilecek Katmanı Seçin:", layers)
    
    unit = st.sidebar.selectbox("Birim", ["cm", "mm", "m"])
    scale = 100 if unit == "cm" else (1000 if unit == "mm" else 1)
    
    # VERİYİ İŞLE
    geometry = get_dxf_geometry(tmp_path, selected_layer, scale)
    df = pd.DataFrame(geometry)

    if not df.empty:
        col1, col2 = st.columns([2, 1])

        with col2:
            st.subheader("📊 Metraj Listesi")
            # İnteraktif seçim
            selected_idx = st.selectbox("Planda vurgulanacak çizgi ID:", df.index)
            st.metric("Toplam Metraj", f"{df['Uzunluk'].sum():.2f} m")
            st.dataframe(df[["Uzunluk"]], use_container_width=True)

        with col1:
            st.subheader("🗺️ Teknik Çizim")
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#111')
            
            # Tüm Çizgileri Çiz
            for i, row in df.iterrows():
                is_sel = (i == selected_idx)
                color = "#32CD32" if is_sel else "#555"
                width = 4 if is_sel else 1
                ax.plot([row['p1'][0], row['p2'][0]], [row['p1'][1], row['p2'][1]], 
                        color=color, lw=width, marker='o', markersize=2 if is_sel else 0)
                
                if is_sel:
                    ax.text(row['p1'][0], row['p1'][1], f" {row['Uzunluk']}m", color="white", fontsize=12)

            ax.set_aspect("equal")
            ax.axis("off")
            st.pyplot(fig)
    else:
        st.warning(f"'{selected_layer}' katmanında veri bulunamadı.")
    
    os.remove(tmp_path)
