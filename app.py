import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
from inference_sdk import InferenceHTTPClient

# --- 1. GÜVENLİ OTURUM VE AYARLAR ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

try:
    config = st.secrets.to_dict()
    admin_username = "admin"
    admin_password = config['credentials']['usernames']['admin']['password']
    admin_name = config['credentials']['usernames']['admin']['name']
except Exception as e:
    st.error(f"Yapılandırma Hatası: {e}")
    st.stop()

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. MANUEL GİRİŞ SİSTEMİ (Bypass) ---
if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if user == admin_username and pw == admin_password:
                st.session_state.logged_in = True
                st.session_state.name = admin_name
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre")
    st.stop()

# --- 3. ANALİZ FONKSİYONLARI ---
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
    except:
        return []

def calculate_total_length(geometries):
    total = 0
    for geo in geometries:
        for i in range(len(geo) - 1):
            total += math.dist(geo[i], geo[i+1])
    return total

# --- 4. ANA PANEL (Giriş Sonrası) ---
st.sidebar.success(f"Hoş geldin, {st.session_state.name}")
if st.sidebar.button("Çıkış Yap"):
    st.session_state.logged_in = False
    st.rerun()

st.title("🏗️ DUVAR METRAJ PANELİ")

# Sidebar Ayarları
with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("Dosya Seç (DXF)", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katmanlar = st.text_input("Katman Filtresi", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_layers = [x.strip() for x in katmanlar.split(",")] if katmanlar else []
    geos = read_dxf_geometry(file_path, target_layers)
    
    if geos:
        # Hesaplamalar
        raw_len = calculate_total_length(geos)
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        
        # Mimari çift çizgi düzeltmesi (/2) ve birim dönüşümü
        net_uzunluk = (raw_len / 2) / bolen
        toplam_alan = net_uzunluk * kat_yuk
        
        st.success(f"✅ {len(geos)} adet duvar objesi tespit edildi.")

        # Görselleştirme ve Metrikler
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("🔍 Plan Analizi")
            fig, ax = plt.subplots(figsize=(10, 8))
            for g in geos:
                xs, ys = zip(*g)
                ax.plot(xs, ys, color="#e67e22", linewidth=1)
            ax.set_aspect("equal")
            ax.axis("off")
            st.pyplot(fig)
            plt.close(fig)

        with col2:
            st.subheader("📊 Metraj Bilgileri")
            st.metric("📏 Toplam Uzunluk", f"{round(net_uzunluk, 2)} m")
            st.metric("🧱 Toplam Duvar Alanı", f"{round(toplam_alan, 2)} m²")
            
            # Veri Tablosu ve İndirme
            metraj_data = {
                "Açıklama": ["Toplam Duvar Metrajı"],
                "Uzunluk (m)": [round(net_uzunluk, 2)],
                "Yükseklik (m)": [kat_yuk],
                "Alan (m2)": [round(toplam_alan, 2)]
            }
            df = pd.DataFrame(metraj_data)
            st.table(df)
            
            # CSV Olarak İndir
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Metraj Cetvelini İndir (CSV)",
                data=csv,
                file_name='metraj_raporu.csv',
                mime='text/csv',
            )
            
            st.info("💡 Not: Uzunluk hesabı mimari çift çizgiye göre otomatik optimize edilmiştir.")
    else:
        st.warning("⚠️ Seçilen katmanlarda çizim verisi bulunamadı.")
else:
    st.info("👋 Başlamak için yan menüden bir DXF dosyası yükleyin.")
