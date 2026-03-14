import streamlit as st
import streamlit_authenticator as stauth
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import numpy as np
from inference_sdk import InferenceHTTPClient

# --- 1. OTURUM HATALARI ÖNLEME (KeyError: 'name' FIX) ---
# Çerez kontrolü sırasında 'name' anahtarı bulunamazsa uygulamanın çökmesini engeller.
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- 2. KİMLİK DOĞRULAMA YAPILANDIRMASI ---
try:
    # Secrets objesi salt okunur olduğu için bir sözlük kopyası alınır.
    config = st.secrets.to_dict()
    
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
except Exception as e:
    st.error(f"Sistem yapılandırma hatası: {e}")
    st.stop()

# --- 3. LOGIN PANELİ (Hataları Yakalayan Yapı) ---
try:
    # v0.2.3 sürümü için doğru değişken atamaları.
    name, authentication_status, username = authenticator.login('Giriş Yap', 'main')
except KeyError:
    # Bozuk çerez durumunda state'i sıfırlayarak login ekranını zorla getirir.
    st.session_state['authentication_status'] = None
    st.warning("Oturum verisi bozulmuş, lütfen tekrar giriş yapın.") #
    name, authentication_status, username = None, None, None

# --- 4. UYGULAMA ANA GÖVDESİ ---
if st.session_state["authentication_status"]:
    authenticator.logout('Çıkış Yap', 'sidebar')
    
    # API Anahtarı Kontrolü
    ROBO_API_KEY = st.secrets.get("ROBO_API_KEY", "Anahtar Bulunamadı")
    MODEL_ID = "mimari_duvar_tespiti-2/8"
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=ROBO_API_KEY)

    # --- 5. DXF ANALİZ FONKSİYONLARI ---
    def read_dxf_geometry(path, target_layers):
        try:
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()
            polygons = []
            # Belirtilen katmanlardaki çizgileri sorgula
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
            # Mimari çift çizgi düzeltmesi
            final_uzunluk = (raw_len / 2) / bolen

            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🔍 Plan Analizi")
                fig, ax = plt.subplots()
                for g in geos:
                    xs, ys = zip(*g)
                    ax.plot(xs, ys, color="#e67e22")
                ax.set_aspect("equal")
                ax.axis("off")
                st.pyplot(fig)
            
            with c2:
                st.subheader("📊 Sonuçlar")
                st.metric("📏 Uzunluk", f"{round(final_uzunluk, 2)} m")
                st.metric("🧱 Alan", f"{round(final_uzunluk * kat_yuk, 2)} m²")
        else:
            st.warning("Seçilen katmanlarda çizim bulunamadı.")

elif st.session_state["authentication_status"] is False:
    st.error('Kullanıcı adı veya şifre hatalı')
elif st.session_state["authentication_status"] is None:
    st.warning('Lütfen kullanıcı adı ve şifrenizi giriniz') #
