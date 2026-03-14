import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import cv2
import numpy as np
import streamlit_authenticator as stauth
from inference_sdk import InferenceHTTPClient

# --- 1. KİMLİK DOĞRULAMA (AUTH) YAPILANDIRMASI ---
# Secrets'tan verileri hata almadan çekmek için kopyasını oluşturuyoruz
try:
    # TOML verisini doğrudan kullanmak yerine kopyasını alarak hata riskini sıfırlıyoruz
    credentials = dict(st.secrets["credentials"])
    cookie = dict(st.secrets["cookie"])
    
    authenticator = stauth.Authenticate(
        credentials,
        cookie['name'],
        cookie['key'],
        cookie['expiry_days']
    )
except Exception as e:
    st.error(f"Secrets yapılandırma hatası: {e}")
    st.stop()

# Giriş Panelini Göster
name, authentication_status, username = authenticator.login('Giriş Yap', 'main')

if authentication_status:
    # --- 2. GÜVENLİ API VE ARAYÜZ AYARLARI ---
    authenticator.logout('Çıkış Yap', 'sidebar')
    
    try:
        ROBO_API_KEY = st.secrets["ROBOFLOW_API_KEY"] #
    except KeyError:
        st.error("Hata: Secrets içinde 'ROBOFLOW_API_KEY' bulunamadı!")
        st.stop()

    MODEL_ID = "mimari_duvar_tespiti-2/8" #
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=ROBO_API_KEY)

    # --- 3. FONKSİYONLAR ---
    def read_dxf_geometry(path, target_layers):
        try:
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()
            polygons = []
            entities = list(msp.query('LINE LWPOLYLINE POLYLINE'))
            for insert in msp.query('INSERT'):
                try: entities.extend(insert.explode())
                except: continue
            for e in entities:
                layer_name = e.dxf.layer.upper()
                is_target_layer = any(t.upper() in layer_name for t in target_layers) if target_layers else True
                if is_target_layer:
                    if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                        pts = [(p[0], p[1]) for p in e.get_points()]
                        if len(pts) > 1: polygons.append(pts)
                    elif e.dxftype() == "LINE":
                        p1, p2 = e.dxf.start, e.dxf.end
                        polygons.append([(p1[0], p1[1]), (p2[0], p2[1])])
            return polygons
        except Exception as e:
            st.error(f"DXF Okuma Hatası: {e}")
            return []

    def calculate_total_length(geometries):
        total = 0
        for geo in geometries:
            for i in range(len(geo) - 1):
                total += math.dist(geo[i], geo[i+1])
        return total

    # --- 4. ARAYÜZ TASARIMI ---
    st.title("🏗️ DUVAR METRAJ PANELİ")

    with st.sidebar:
        st.header("⚙️ Analiz Ayarları")
        uploaded = st.file_uploader("Dosya Seç (DXF veya Görsel)", type=["dxf", "jpg", "png", "jpeg"])
        kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01) #
        birim = st.selectbox("Çizim Birimi (DXF)", ["cm", "mm", "m"], index=0)
        katmanlar = st.text_input("DXF Katman Filtresi", "DUVAR, WALL, MIM_DUVAR")

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp:
            tmp.write(uploaded.getbuffer())
            file_path = tmp.name

        is_dxf = uploaded.name.lower().endswith(".dxf")
        geos = []
        final_uzunluk = 0

        if is_dxf:
            target_layers = [x.strip() for x in katmanlar.split(",")] if katmanlar else []
            geos = read_dxf_geometry(file_path, target_layers)
            if geos:
                raw_len = calculate_total_length(geos)
                bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
                final_uzunluk = (raw_len / 2) / bolen # Çift çizgi düzeltmesi

        if geos:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🔍 Plan Analiz Görünümü")
                fig, ax = plt.subplots(figsize=(12, 10))
                all_x, all_y = [], []
                for g in geos:
                    xs, ys = zip(*g)
                    all_x.extend(xs); all_y.extend(ys)
                    ax.plot(xs, ys, color="#e67e22", linewidth=0.8)

                # AKILLI ODAKLANMA (AUTO-ZOOM)
                if all_x and all_y:
                    x_min, x_max = np.percentile(all_x, [1, 99])
                    y_min, y_max = np.percentile(all_y, [1, 99])
                    pad_x, pad_y = (x_max - x_min) * 0.05, (y_max - y_min) * 0.05
                    ax.set_xlim(x_min - pad_x, x_max + pad_x)
                    ax.set_ylim(y_min - pad_y, y_max + pad_y)

                ax.set_aspect("equal")
                ax.axis("off")
                st.pyplot(fig)
                plt.close(fig)

            with c2:
                st.subheader("📊 Metraj Sonuçları")
                st.metric("📏 Toplam Uzunluk", f"{round(final_uzunluk, 2)} m") #
                st.metric("🧱 Duvar Alanı", f"{round(final_uzunluk * kat_yuk, 2)} m²")
                
                # Referans Karşılaştırma
                referans_deger = 58.08
                sapma = final_uzunluk - referans_deger
                st.metric("🎯 Referans Sapması", f"{round(sapma, 2)} m", delta=f"{round(sapma, 2)} m", delta_color="inverse")
        else:
            st.warning("⚠️ Çizim bulunamadı.")
    else:
        st.info("👋 Başlamak için bir plan dosyası yükleyin.")

elif authentication_status == False:
    st.error('Kullanıcı adı veya şifre hatalı')
elif authentication_status == None:
    st.warning('Lütfen kullanıcı adı ve şifrenizi giriniz')
