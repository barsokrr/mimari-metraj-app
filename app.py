import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- 1. SAYFA YAPILANDIRMASI ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

# CSS: Profil alanı ve buton özelleştirmeleri
st.markdown("""
    <style>
    .profile-area { text-align: center; padding: 10px; margin-bottom: 20px; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; object-fit: cover; border: 2px solid #FF4B4B; margin-bottom: 10px; }
    .user-name { font-weight: bold; font-size: 1.1em; color: white; margin-bottom: 0px; }
    .company-name { font-size: 0.9em; color: #888; margin-top: -5px; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #262730; color: white; }
    .stDownloadButton>button { width: 100%; background-color: #00c853; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AI MODEL FONKSİYONU ---
def run_roboflow_ai(image_bytes):
    try:
        rf = Roboflow(api_key="SENIN_API_KEYIN")
        project = rf.workspace("SENIN_WORKSPACE").project("SENIN_PROJEN")
        model = project.version(8).model 
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            prediction = model.predict(tmp.name, confidence=40).json()
        os.remove(tmp.name)
        return prediction.get('predictions', [])
    except Exception: return []

# --- 3. DXF GEOMETRİ FONKSİYONU ---
def get_dxf_geometry(path, target_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        entities = msp.query('LINE LWPOLYLINE POLYLINE')
        for e in entities:
            if target_layers:
                layer_name = e.dxf.layer.upper()
                if not any(t.upper() in layer_name for t in target_layers): continue
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
                if len(pts) > 1: geometries.append(pts)
            elif e.dxftype() == "LINE":
                geometries.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        return geometries
    except: return []

# --- 4. YAN MENÜ (SIDEBAR) ---
with st.sidebar:
    # --- PROFIL ALANI ---
    # Not: URL kısmına kendi profil resminin linkini koyabilirsin.
    st.markdown(f"""
        <div class="profile-area">
            <img src="https://www.w3schools.com/howto/img_avatar.png" class="profile-img">
            <p class="user-name"> Kullanıcı Adı </p>
            <p class="company-name">Firma</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.write("---")
    
    # Dosya Yükleme Alanı
    uploaded = st.file_uploader("Dosya yükleyin • DXF", type=["dxf"])
    
    # Ayarlar
    katmanlar = st.text_input("Katman Filtresi", "DUVAR")
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    
    # Sayfa sonuna itmek için boşluk
    for _ in range(5): st.write("")
    
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. ANA EKRAN VE ANALİZ ---
st.title("🏗️ Metraj Analizi")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_list = [x.strip() for x in katmanlar.split(",")]
    full_project = get_dxf_geometry(file_path)
    wall_analysis = get_dxf_geometry(file_path, target_list)

    if wall_analysis:
        raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_analysis for i in range(len(g)-1))
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        net_uzunluk = (raw_len / 2) / bolen
        toplam_alan = net_uzunluk * kat_yuk

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Orijinal Plan")
            fig1, ax1 = plt.subplots(figsize=(10, 10), facecolor='#0e1117')
            for g in full_project:
                xs, ys = zip(*g)
                ax1.plot(xs, ys, color="gray", lw=0.5, alpha=0.5)
            ax1.set_aspect("equal"); ax1.axis("off")
            st.pyplot(fig1)

        with col2:
            st.subheader("Duvar Analizi (AI & CAD)")
            fig2, ax2 = plt.subplots(figsize=(10, 10), facecolor='#0e1117')
            for g in wall_analysis:
                xs, ys = zip(*g)
                ax2.plot(xs, ys, color="#FF4B4B", lw=1.5)
            ax2.set_aspect("equal"); ax2.axis("off")
            
            if st.button("🤖 AI ile Doğrula"):
                img_buf = BytesIO()
                fig2.savefig(img_buf, format='png')
                preds = run_roboflow_ai(img_buf)
                st.info(f"AI {len(preds)} adet yapısal eleman doğruladı.")
            st.pyplot(fig2)

        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Toplam Uzunluk", f"{net_uzunluk:.2f} m")
        m2.metric("Toplam Alan", f"{toplam_alan:.2f} m²")

        df = pd.DataFrame({
            "İmalat": ["Duvar Metrajı"],
            "Miktar": [round(toplam_alan, 2)],
            "Birim": ["m²"],
            "Kat Yüksekliği": [kat_yuk]
        })
        st.table(df)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Metraj Cetvelini İndir (CSV)", csv, "rapor.csv")
    os.remove(file_path)
else:
    st.info("Lütfen sol menüden bir DXF dosyası yükleyerek analizi başlatın.")
