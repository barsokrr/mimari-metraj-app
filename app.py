import streamlit as st
import streamlit_authenticator as stauth
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import numpy as np
from inference_sdk import InferenceHTTPClient

# --- 1. OTURUM HATALARI ÖNLEME (KeyError: 'name' FIX) ---
# Çerez kontrolü sırasında uygulamanın çökmesini engeller.
for key in ['authentication_status', 'name', 'username']:
    if key not in st.session_state:
        st.session_state[key] = None

# --- 2. KİMLİK DOĞRULAMA YAPILANDIRMASI ---
try:
    config = st.secrets.to_dict()
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
except Exception as e:
    st.error(f"Yapılandırma hatası: {e}")
    st.stop()

# --- 3. LOGIN PANELİ (Hataları Yakalayan Yapı) ---
# image_08d0fa.jpg'deki 'name' hatasını bertaraf eden kritik bölüm.
try:
    name, authentication_status, username = authenticator.login('Giriş Yap', 'main')
except Exception:
    # Bozuk çerez varsa state'i temizleyip login ekranını zorla getirir.
    st.session_state['authentication_status'] = None
    st.session_state['name'] = None
    st.session_state['username'] = None
    name, authentication_status, username = None, None, None

# --- 4. UYGULAMA ANA GÖVDESİ ---
if st.session_state["authentication_status"]:
    authenticator.logout('Çıkış Yap', 'sidebar')
    
    # API Ayarları
    ROBO_API_KEY = st.secrets.get("ROBO_API_KEY", "Anahtar_Bulunamadi")
    MODEL_ID = "mimari_duvar_tespiti-2/8"
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=ROBO_API_KEY)

    # --- 5. ANALİZ FONKSİYONLARI ---
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
        except Exception:
            return []

    def calculate_total_length(geometries):
        total = 0
        for geo in geometries:
            for i in range(len(geo) - 1):
                total += math.dist(geo[i], geo[i+1])
        return total

    # --- 6. ARAYÜZ ---
    st.title("🏗️ DUVAR METRAJ PANELİ")
    st.sidebar.success(f"Hoş geldin, {st.session_state['name']}")

    with st.sidebar:
        st.header("⚙️ Ayarlar")
        uploaded = st.file_uploader("Dosya Seç (DXF)", type=["dxf"])
        kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
        birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"])
        katmanlar = st.text_input("Katman Filtresi", "DUVAR")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getbuffer())
            file_path = tmp.name

        target_layers = [x.strip() for x in katmanlar.split(",")] if katmanlar else []
        geos = read_dxf_geometry(file_path, target_layers)
        
        if geos:
            raw_len = calculate_total_length(geos)
            bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
            final_uzunluk = (raw_len / 2) / bolen # Mimari çift çizgi düzeltmesi

            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🔍 Plan Görünümü")
                fig, ax = plt.subplots(figsize=(8, 6))
                for g in geos:
                    xs, ys = zip(*g)
                    ax.plot(xs, ys, color="#e67e22")
                ax.set_aspect("equal")
                ax.axis("off")
                st.pyplot(fig)
                plt.close(fig)
            
            with c2:
                st.subheader("📊 Sonuçlar")
                st.metric("📏 Uzunluk", f"{round(final_uzunluk, 2)} m")
                st.metric("🧱 Alan", f"{round(final_uzunluk * kat_yuk, 2)} m²")
        else:
            st.warning("⚠️ Çizim verisi bulunamadı.")

elif st.session_state["authentication_status"] is False:
    st.error('❌ Kullanıcı adı veya şifre hatalı')
elif st.session_state["authentication_status"] is None:
    st.warning('🔐 Lütfen kullanıcı adı ve şifrenizi giriniz')
