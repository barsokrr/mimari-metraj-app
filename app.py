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

# Oturum kontrolü (Önceki başarılı yapı)
if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login"):
        user = st.text_input("Username")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Giriş"):
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı giriş")
    st.stop()

# --- 2. GELİŞMİŞ ANALİZ FONKSİYONLARI ---
def get_dxf_data(path, target_layers=None):
    """Belirli katmanları veya (None ise) tüm projeyi okur."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geoms = []
        # Temel çizim elemanlarını sorgula
        entities = msp.query('LINE LWPOLYLINE POLYLINE')
        
        for e in entities:
            if target_layers:
                layer_name = e.dxf.layer.upper()
                if not any(t.upper() in layer_name for t in target_layers):
                    continue
            
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
                if len(pts) > 1: geoms.append(pts)
            elif e.dxftype() == "LINE":
                geoms.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        return geoms
    except:
        return []

# --- 3. ANA PANEL ---
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

    # Verileri Hazırla
    target_layers = [x.strip() for x in katman_input.split(",")]
    full_project = get_dxf_data(file_path) # Tüm proje
    wall_analysis = get_dxf_data(file_path, target_layers) # Sadece duvarlar

    # GÖRSELLEŞTİRME: YAN YANA PANELLER
    col_img1, col_img2, col_metrics = st.columns([1.5, 1.5, 1])

    with col_img1:
        st.subheader("🖼️ Orijinal Plan")
        fig1, ax1 = plt.subplots(figsize=(6, 6))
        for g in full_project:
            xs, ys = zip(*g)
            ax1.plot(xs, ys, color="gray", linewidth=0.3, alpha=0.5)
        ax1.set_aspect("equal")
        ax1.axis("off")
        st.pyplot(fig1)

    with col_img2:
        st.subheader("🔍 Duvar Analizi")
        fig2, ax2 = plt.subplots(figsize=(6, 6))
        for g in wall_analysis:
            xs, ys = zip(*g)
            ax2.plot(xs, ys, color="#e67e22", linewidth=1)
        ax2.set_aspect("equal")
        ax2.axis("off")
        st.pyplot(fig2)

    with col_metrics:
        st.subheader("📊 Metraj")
        if wall_analysis:
            # Hesaplama mantığı
            raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_analysis for i in range(len(g)-1))
            bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
            net_m = (raw_len / 2) / bolen
            
            st.metric("Toplam Uzunluk", f"{round(net_m, 2)} m")
            st.metric("Duvar Alanı", f"{round(net_m * kat_yuk, 2)} m²")
            
            # Excel Raporu
            df = pd.DataFrame({
                "Açıklama": ["Duvar Metrajı"],
                "Metraj (m)": [round(net_m, 2)],
                "Alan (m2)": [round(net_m * kat_yuk, 2)]
            })
            st.download_button("📥 Raporu İndir", df.to_csv(index=False).encode('utf-8'), "metraj.csv")
