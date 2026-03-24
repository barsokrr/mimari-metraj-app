import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os

# --- 1. OTURUM VE SAYFA AYARI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.set_page_config(page_title="SaaS Metraj Pro - Barış Öker", layout="wide")

# --- 2. ANALİZ FONKSİYONLARI ---
def analyze_dxf(path, wall_layer="DUVAR", floor_layer="ZEMIN"):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        
        results = {
            "wall_len": 0,
            "floor_area": 0,
            "door_count": 0, # ARC'lar buraya sayılacak
            "entities": []
        }

        # 1. DUVAR VE ZEMİN (Senin çalışan mantığın)
        entities = msp.query('LINE LWPOLYLINE ARC') # ARC'ları da sorguya ekledik
        
        for e in entities:
            # DUVAR UZUNLUĞU
            if wall_layer.upper() in e.dxf.layer.upper():
                if e.dxftype() == "LINE":
                    results["wall_len"] += math.dist(e.dxf.start, e.dxf.end)
                elif e.dxftype() == "LWPOLYLINE":
                    pts = list(e.get_points())
                    results["wall_len"] += sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))

            # ZEMİN ALANI (Kapalı Poligonlar)
            if floor_layer.upper() in e.dxf.layer.upper() and e.dxftype() == "LWPOLYLINE":
                pts = [(p[0], p[1]) for p in e.get_points()]
                if len(pts) > 2:
                    area = 0.5 * abs(sum(pts[i][0]*pts[i+1][1] - pts[i+1][0]*pts[i][1] for i in range(len(pts)-1)) + (pts[-1][0]*pts[0][1] - pts[0][0]*pts[-1][1]))
                    results["floor_area"] += area

            # KAPI SAYIMI (ARC MANTIĞI)
            # Mimari standartta kapı kanadı açılışı ARC ile çizilir.
            if e.dxftype() == "ARC":
                results["door_count"] += 1

        return results, msp
    except:
        return None, None

# --- 3. ANA EKRAN ---
if st.session_state.logged_in or True: # Girişi şimdilik True tuttum
    with st.sidebar:
        st.markdown(f"**Barış Öker**\nFi-le Yazılım A.Ş.")
        uploaded = st.file_uploader("DXF Yükle", type=["dxf"])
        w_lay = st.text_input("Duvar Katmanı", "DUVAR")
        f_lay = st.text_input("Zemin Katmanı", "ZEMIN")
        kat_h = st.number_input("Kat Yüksekliği", 2.85)
        birim = st.selectbox("Birim", ["cm", "mm", "m"])
        div = {"cm": 100, "mm": 1000, "m": 1}[birim]

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getbuffer())
            data, msp = analyze_dxf(tmp.name, w_lay, f_lay)
        
        if data:
            # m2 ve Adet Hesapları
            final_wall_m2 = ((data["wall_len"] / 2) / div) * kat_h
            final_floor_m2 = data["floor_area"] / (div**2)
            
            # Sonuç Ekranı
            c1, c2, c3 = st.columns(3)
            c1.metric("Duvar Metrajı", f"{final_wall_m2:.2f} m²")
            c2.metric("Zemin Metrajı", f"{final_floor_m2:.2f} m²")
            c3.metric("Kapı Adedi (ARC)", data["door_count"])

            # Plan Çizimi
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            for e in msp.query('LINE LWPOLYLINE ARC'):
                if e.dxftype() == "ARC":
                    # Yayları çizmek biraz daha karmaşıktır ama görselde nokta olarak görebiliriz
                    ax.plot(e.dxf.center[0], e.dxf.center[1], 'ro', markersize=2)
                else:
                    pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
                    xs, ys = zip(*[(p[0], p[1]) for p in pts])
                    ax.plot(xs, ys, color="gray", lw=0.5, alpha=0.5)
            ax.set_aspect("equal"); ax.axis("off")
            st.pyplot(fig)
        
        os.remove(tmp.name)
