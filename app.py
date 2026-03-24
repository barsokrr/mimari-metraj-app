import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- 1. OTURUM VE SAYFA AYARI ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.set_page_config(page_title="SaaS Metraj Pro - Barış Öker", layout="wide")

st.markdown("""
    <style>
    .profile-area { text-align: center; padding: 10px; margin-bottom: 20px; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; object-fit: cover; border: 2px solid #FF4B4B; margin-bottom: 10px; }
    .user-name { font-weight: bold; font-size: 1.1em; color: white; margin-bottom: 0px; }
    .company-name { font-size: 0.9em; color: #888; margin-top: -5px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. YARDIMCI MOTORLAR ---
def run_roboflow_ai(image_bytes):
    try:
        # KENDİ BİLGİLERİNİ GİR
        rf = Roboflow(api_key="SENIN_API_KEYIN")
        project = rf.workspace("SENIN_WORKSPACE").project("SENIN_PROJEN")
        model = project.version(8).model 
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            prediction = model.predict(tmp.name, confidence=40).json()
        os.remove(tmp.name)
        return prediction.get('predictions', [])
    except: return []

def get_dxf_data(path):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        layers = [layer.dxf.name for layer in doc.layers]
        return doc, msp, layers
    except: return None, None, []

# --- 3. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    st.title("🏗️ Metraj Analiz Giriş")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            user_input = st.text_input("Kullanıcı Adı")
            pass_input = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap"):
                if user_input == "admin" and pass_input == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else: st.error("Hatalı!")

# --- 4. ANA PROGRAM ---
else:
    with st.sidebar:
        st.markdown(f"""
            <div class="profile-area">
                <img src="https://www.w3schools.com/howto/img_avatar.png" class="profile-img">
                <p class="user-name">Barış Öker</p>
                <p class="company-name">Fi-le Yazılım A.Ş.</p>
            </div>
        """, unsafe_allow_html=True)
        
        uploaded = st.file_uploader("DXF Yükle", type=["dxf"])
        
        if uploaded:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getbuffer())
                file_path = tmp.name
                doc, msp, layers = get_dxf_data(file_path)
            
            with st.expander("📂 Katman Seçimleri", expanded=True):
                sel_wall = st.selectbox("Duvar Katmanı", layers, index=layers.index("DUVAR") if "DUVAR" in layers else 0)
                sel_floor = st.selectbox("Zemin Katmanı", layers, index=layers.index("ZEMIN") if "ZEMIN" in layers else 0)
            
            kat_yuk = st.number_input("Kat Yüksekliği (m)", 2.85)
            birim = st.selectbox("Birim", ["cm", "mm", "m"], index=0)
            div = {"cm": 100, "mm": 1000, "m": 1}[birim]
            
        if st.button("Çıkış Yap"):
            st.session_state.logged_in = False
            st.rerun()

    st.title("🏗️ Metraj Analizi")

    if uploaded and 'msp' in locals():
        # 1. DUVAR HESABI (Lineer)
        wall_lines = msp.query(f'*[layer=="{sel_wall}"]')
        raw_wall_len = 0
        for e in wall_lines:
            if e.dxftype() == "LINE":
                raw_wall_len += math.dist(e.dxf.start, e.dxf.end)
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                raw_wall_len += sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
        
        net_wall_area = ((raw_wall_len / 2) / div) * kat_yuk

        # 2. ZEMİN HESABI (Shoelace Alan)
        floor_polys = msp.query(f'LWPOLYLINE[layer=="{sel_floor}"]')
        total_floor_area = 0
        for e in floor_polys:
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) > 2:
                area = 0.5 * abs(sum(pts[i][0]*pts[i+1][1] - pts[i+1][0]*pts[i][1] for i in range(len(pts)-1)) + (pts[-1][0]*pts[0][1] - pts[0][0]*pts[-1][1]))
                total_floor_area += area / (div**2)

        # GÖRSELLEŞTİRME
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Plan Önizleme")
            fig1, ax1 = plt.subplots(figsize=(10, 10), facecolor='#0e1117')
            for e in msp.query('LINE LWPOLYLINE'):
                pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
                xs, ys = zip(*[(p[0], p[1]) for p in pts])
                ax1.plot(xs, ys, color="gray", lw=0.5, alpha=0.4)
            ax1.set_aspect("equal"); ax1.axis("off")
            st.pyplot(fig1)

        with col2:
            st.subheader("AI Nesne Tespiti")
            if st.button("🤖 AI Analizi (Kapı/Pencere Say)"):
                img_buf = BytesIO()
                fig1.savefig(img_buf, format='png', dpi=150)
                preds = run_roboflow_ai(img_buf)
                
                kapi = len([p for p in preds if p['class'].lower() == 'kapi'])
                pencere = len([p for p in preds if p['class'].lower() == 'pencere'])
                
                st.session_state.kapi = kapi
                st.session_state.pencere = pencere
                st.success(f"AI Analizi: {kapi} Kapı, {pencere} Pencere bulundu.")

        # METRİKLER VE TABLO
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Duvar Alanı", f"{net_wall_area:.2f} m²")
        m2.metric("Zemin Alanı", f"{total_floor_area:.2f} m²")
        m3.metric("Kapı Adedi", st.session_state.get('kapi', 0))
        m4.metric("Pencere Adedi", st.session_state.get('pencere', 0))

        df = pd.DataFrame([
            {"İmalat": "Duvar Örülmesi", "Miktar": round(net_wall_area, 2), "Birim": "m²"},
            {"İmalat": "Zemin Kaplama", "Miktar": round(total_floor_area, 2), "Birim": "m²"},
            {"İmalat": "Kapı Montajı", "Miktar": st.session_state.get('kapi', 0), "Birim": "Adet"},
            {"İmalat": "Pencere Montajı", "Miktar": st.session_state.get('pencere', 0), "Birim": "Adet"}
        ])
        st.table(df)
        st.download_button("📥 Excel İndir", df.to_csv(index=False).encode('utf-8'), "metraj_ozet.csv")
        
        os.remove(file_path)
