import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import numpy as np
from inference_sdk import InferenceHTTPClient

# --- 1. AYARLARI YÜKLE ---
try:
    config = st.secrets.to_dict()
    admin_username = "admin"
    admin_password = config['credentials']['usernames']['admin']['password']
    admin_name = config['credentials']['usernames']['admin']['name']
except Exception as e:
    st.error(f"Secrets okunamadı: {e}")
    st.stop()

# --- 2. MANUEL OTURUM KONTROLÜ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

def login():
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        submit = st.form_submit_button("Giriş Yap")
        
        if submit:
            if user == admin_username and pw == admin_password:
                st.session_state.logged_in = True
                st.session_state.name = admin_name
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre")

# --- 3. UYGULAMA ANA GÖVDESİ ---
if not st.session_state.logged_in:
    login()
else:
    # Çıkış Butonu
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()

    st.sidebar.success(f"Hoş geldin, {st.session_state.name}")
    
    # API Ayarları
    ROBO_API_KEY = st.secrets.get("ROBOFLOW_API_KEY", "Anahtar_Yok")
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=ROBO_API_KEY)

    st.title("🏗️ DUVAR METRAJ PANELİ")

    # Analiz Fonksiyonu
    def read_dxf_geometry(path, target_layers):
        try:
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()
            polygons = []
            entities = list(msp.query('LINE LWPOLYLINE POLYLINE'))
            for e in entities:
                layer_name = e.dxf.layer.upper()
                is_target = any(t.upper() in layer_name for t in target_layers) if target_layers else True
                if is_target:
                    if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                        pts = [(p[0], p[1]) for p in e.get_points()]
                        if len(pts) > 1: polygons.append(pts)
                    elif e.dxftype() == "LINE":
                        p1, p2 = e.dxf.start, e.dxf.end
                        polygons.append([(p1[0], p1[1]), (p2[0], p2[1])])
            return polygons
        except: return []

    # Arayüz Elemanları
    with st.sidebar:
        uploaded = st.file_uploader("DXF Yükle", type=["dxf"])
        kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
        birim = st.selectbox("Birim", ["cm", "mm", "m"])
        katman = st.text_input("Katman Filtresi", "DUVAR")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getbuffer())
            file_path = tmp.name

        geos = read_dxf_geometry(file_path, [katman])
        if geos:
            st.success(f"{len(geos)} adet duvar objesi tespit edildi.")
            # Buraya metraj hesaplama ve görselleştirme gelecek
            fig, ax = plt.subplots()
            for g in geos:
                xs, ys = zip(*g)
                ax.plot(xs, ys, color="orange")
            ax.set_aspect("equal")
            st.pyplot(fig)
        else:
            st.warning("Seçili katmanda çizim bulunamadı.")
