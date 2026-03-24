import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- 1. OTURUM VE SAYFA YAPILANDIRMASI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.set_page_config(page_title="SaaS Metraj Pro - Barış Öker", layout="wide")

# --- 2. ROBOFLOW AI FONKSİYONU (ASIL ZEKA BURASI) ---
def run_roboflow_ai(image_bytes):
    try:
        # Kendi API bilgilerini buraya girmeyi unutma
        rf = Roboflow(api_key="SENIN_API_KEYIN")
        project = rf.workspace("SENIN_WORKSPACE").project("SENIN_PROJEN")
        model = project.version(8).model 
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            prediction = model.predict(tmp.name, confidence=40).json()
        os.remove(tmp.name)
        return prediction.get('predictions', [])
    except Exception as e:
        return []

# --- 3. DXF GEOMETRİ MOTORU ---
def get_comprehensive_data(path, target_layer="DUVAR"):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        all_layers = [l.dxf.name for l in doc.layers]
        
        # Duvar Analizi
        wall_len = 0
        walls = msp.query(f'*[layer=="{target_layer}"]')
        for e in walls:
            if e.dxftype() == "LINE":
                wall_len += math.dist(e.dxf.start, e.dxf.end)
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                wall_len += sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
        
        return wall_len, all_layers, msp
    except: return 0, [], None

# --- 4. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Pro Giriş")
    with st.form("login"):
        u = st.text_input("Kullanıcı")
        p = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else: st.error("Hatalı Giriş!")

# --- 5. ANA EKRAN ---
else:
    with st.sidebar:
        st.markdown(f'<div style="text-align:center"><img src="https://www.w3schools.com/howto/img_avatar.png" width="80" style="border-radius:50%"><br><b>Barış Öker</b><br><small>Fi-le Yazılım A.Ş.</small></div>', unsafe_allow_html=True)
        st.write("---")
        uploaded = st.file_uploader("DXF Dosyası", type=["dxf"])
        
        if uploaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getbuffer())
                path = tmp.name
            
            raw_len, layers, msp = get_comprehensive_data(path)
            sel_layer = st.selectbox("Metraj Katmanı (Duvar)", layers, index=layers.index("DUVAR") if "DUVAR" in layers else 0)
            kat_yuk = st.number_input("Kat Yüksekliği (m)", 2.85)
            birim = st.selectbox("Birim", ["cm", "mm", "m"], index=0)
            div = {"cm": 100, "mm": 1000, "m": 1}[birim]
            
        if st.button("Güvenli Çıkış"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("📊 Metraj Analizi")

    if uploaded and 'msp' in locals():
        # Yeniden hesapla (Seçilen katmana göre)
        final_len, _, _ = get_comprehensive_data(path, sel_layer)
        net_m2 = ((final_len / 2) / div) * kat_yuk
        
        # ROBOLFLOW İÇİN GÖRSEL HAZIRLA
        fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0e1117')
        for e in msp.query('LINE LWPOLYLINE'):
            pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
            xs, ys = zip(*[(p[0], p[1]) for p in pts])
            ax.plot(xs, ys, color="white", lw=0.7, alpha=0.5)
        ax.set_aspect("equal"); ax.axis("off")
        
        # METRİKLER
        c1, c2, c3 = st.columns(3)
        c1.metric("Duvar Metrajı (m²)", f"{net_m2:.2f}")
        
        if st.button("🤖 AI Analizi Yap (Kapı/Pencere Say)"):
            img_buf = BytesIO()
            fig.savefig(img_buf, format='png')
            preds = run_roboflow_ai(img_buf)
            
            pencereler = len([p for p in preds if p['class'] == 'pencere'])
            kapilar = len([p for p in preds if p['class'] == 'kapi'])
            
            c2.metric("Kapı (AI Tahmin)", kapilar)
            c3.metric("Pencere (AI Tahmin)", pencereler)
            st.success(f"AI Analizi Tamamlandı: {len(preds)} nesne bulundu.")
        
        st.pyplot(fig)
        
        # TABLO
        df = pd.DataFrame([{"İmalat": "Duvar Metrajı", "Miktar": round(net_m2, 2), "Birim": "m²"}])
        st.table(df)
        os.remove(path)
    else:
        st.info("Lütfen bir DXF dosyası yükleyin.")
