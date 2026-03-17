import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# Hata almamak için kütüphaneleri güvenli içe aktaralım
try:
    from roboflow import Roboflow
except ImportError:
    st.error("Kütüphane hatası: Roboflow paketi yüklü değil.")

# --- 1. KURUMSAL TEMA VE CSS ---
st.set_page_config(page_title="Metraj Pro | AI Destekli Analiz", layout="wide", page_icon="🏢")

# --- 2. ANALİZ FONKSİYONLARI ---

def get_refined_segments(path, scale, layers):
    """DXF'den LINE ve POLYLINE verilerini çeker."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        walls = []
        targets = [l.upper().strip() for l in layers.split(",") if l.strip()]
        counter = 1

        # Hem LINE hem de POLYLINE sorguluyoruz (Daha kapsamlı metraj için)
        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if targets and not any(t in e.dxf.layer.upper() for t in targets): continue
            
            pts = []
            if e.dxftype() == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            else:
                pts = [(p[0], p[1]) for p in e.get_points()]

            for i in range(len(pts)-1):
                p1, p2 = (pts[i][0]/scale, pts[i][1]/scale), (pts[i+1][0]/scale, pts[i+1][1]/scale)
                ln = math.dist(p1, p2)
                if ln > 0.10: # Çok kısa çizgileri ele
                    walls.append({
                        "ID": f"D-{counter:03d}",
                        "p1": p1, "p2": p2, 
                        "Metraj (m)": round(ln, 2),
                        "Layer": e.dxf.layer
                    })
                    counter += 1
        return walls
    except Exception as e:
        st.error(f"DXF Hatası: {e}")
        return []

def run_roboflow_ai(image_path):
    """Görseldeki panel verilerine göre AI tespiti yapar."""
    try:
        # Görsel 03b0be'den alınan API Key
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        # Görsel 041220'den alınan Proje ve Versiyon
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        prediction = model.predict(image_path, confidence=50).json()
        return prediction['predictions']
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

# --- 3. ANA EKRAN AKIŞI ---
st.sidebar.title("📊 Metraj Kontrol Paneli")
with st.sidebar:
    dxf_up = st.file_uploader("DXF Dosyası Seçin", type=["dxf"])
    layer_sel = st.text_input("Katman (Layer)", "DUVAR")
    unit_sel = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    h_sel = st.number_input("Yükseklik (m)", value=2.85)

if dxf_up:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_up.getbuffer())
        t_path = tmp.name

    sc = 100 if unit_sel == "cm" else (1000 if unit_sel == "mm" else 1)
    walls = get_refined_segments(t_path, sc, layer_sel)

    if walls:
        df = pd.DataFrame(walls)
        st.subheader("🚀 Analiz Raporu")
        
        # Metrikler (Beyaz kutular)
        c1, c2, c3 = st.columns(3)
        total_l = df["Metraj (m)"].sum()
        c1.metric("Net Uzunluk", f"{total_l:.2f} m")
        c2.metric("Toplam Alan", f"{(total_l * h_sel):.2f} m²")
        c3.metric("Aks Sayısı", len(walls))

        # Önizleme
        fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
        for _, w in df.iterrows():
            ax.plot([w["p1"][0]*sc, w["p2"][0]*sc], [w["p1"][1]*sc, w["p2"][1]*sc], color="#00d2ff", lw=1.5)
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)

        # AI Butonu
        if st.button("🤖 Roboflow AI Analizini Başlat"):
            with st.spinner("AI analiz ediyor..."):
                temp_img = "current_plan.png"
                fig.savefig(temp_img, bbox_inches='tight', pad_inches=0)
                ai_results = run_roboflow_ai(temp_img)
                if ai_results:
                    st.success(f"AI {len(ai_results)} bölge tespit etti.")
                    for res in ai_results:
                        st.write(f"📍 {res['class']} - %{res['confidence']*100:.1f}")

        # Excel İndirme
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📊 Excel Raporu İndir", output.getvalue(), "Metraj_Raporu.xlsx")

    os.remove(t_path)
