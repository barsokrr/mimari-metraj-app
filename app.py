import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. AYARLAR VE GÜVENLİK ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            # Secrets kontrolü
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı giriş!")
    st.stop()

# --- 2. DXF ANALİZ MOTORU ---
def process_entity(e, geoms, target_layers=None):
    """Geometriyi ayrıştırır ve koordinatları toplar."""
    layer = e.dxf.layer.upper().strip()
    is_target = True if not target_layers else any(t.upper() in layer for t in target_layers)
    
    if is_target:
        if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) > 1: geoms.append(pts)
        elif e.dxftype() == "LINE":
            geoms.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        elif e.dxftype() in ("ARC", "CIRCLE"):
            pts = [(p[0], p[1]) for p in e.flattening(distance=0.1)]
            if len(pts) > 1: geoms.append(pts)

def get_dxf_data(path, target_layers=None):
    """Blokları (INSERT) ve tüm nesneleri çözen ana fonksiyon."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geoms = []
        # Blok içindeki nesneleri sanal olarak ana plana çıkarır
        for e in msp.query('LINE LWPOLYLINE POLYLINE ARC CIRCLE INSERT'):
            if e.dxftype() == "INSERT":
                for sub_e in e.virtual_entities():
                    process_entity(sub_e, geoms, target_layers)
            else:
                process_entity(e, geoms, target_layers)
        return geoms
    except:
        return []

# --- 3. ARAYÜZ ---
st.sidebar.success(f"Hoş geldin, BARIŞ") #
st.title("🏗️ DUVAR METRAJ VE PLAN ANALİZİ")

with st.sidebar:
    st.header("⚙️ Proje Ayarları")
    uploaded = st.file_uploader("DXF Dosyası", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
    birim = st.selectbox("Birim", ["cm", "mm", "m"])
    katman_input = st.text_input("Analiz Katmanı (Örn: DUVAR)", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_list = [x.strip() for x in katman_input.split(",")]
    
    with st.spinner("Analiz ediliyor..."):
        all_lines = get_dxf_data(file_path, None) # Orijinal plan
        wall_lines = get_dxf_data(file_path, target_list) # Duvarlar

    if wall_lines:
        # Metraj
