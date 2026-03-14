import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import numpy as np
import streamlit_authenticator as stauth
from inference_sdk import InferenceHTTPClient

# --- 1. OTURUM DURUMU ÖN HAZIRLIĞI (KeyError: 'name' Çözümü) ---
# Görselde görülen (image_139ba0) 'name' anahtarı hatasını önlemek için 
# kütüphane çağrılmadan önce session_state başlatılmalıdır.
if 'authentication_status' not in st.session_state:
    st.session_state['authentication_status'] = None
if 'name' not in st.session_state:
    st.session_state['name'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None

# --- 2. KİMLİK DOĞRULAMA YAPILANDIRMASI ---
try:
    # 'Secrets does not support item assignment' hatasını (image_139fdb) önlemek için 
    # verileri sözlük kopyası olarak alıyoruz.
    config = st.secrets.to_dict()
    
    # Secrets içindeki credentials ve cookie yapılandırmasını kontrol ediyoruz.
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )
except Exception as e:
    st.error(f"Sistem yapılandırma hatası: {e}")
    st.stop()

# --- 3. GİRİŞ PANELİ ---
# v0.2.3 sürümü için doğru login imzasını kullanıyoruz.
# login() metodu bu sürümde name, status ve username döndürür.
name, authentication_status, username = authenticator.login('Giriş Yap', 'main')

# --- 4. UYGULAMA MANTIĞI ---
if st.session_state["authentication_status"]:
    # Çıkış butonunu sidebar'a yerleştiriyoruz.
    authenticator.logout('Çıkış Yap', 'sidebar')
    
    # API Anahtarı kontrolü.
    try:
        ROBO_API_KEY = st.secrets["ROBOFLOW_API_KEY"]
    except KeyError:
        st.error("Secrets: 'ROBOFLOW_API_KEY' eksik!")
        st.stop()

    MODEL_ID = "mimari_duvar_tespiti-2/8"
    CLIENT = InferenceHTTPClient(api_url="https://detect.roboflow.com", api_key=ROBO_API_KEY)

    # --- 5. ANALİZ FONKSİYONLARI ---
    def read_dxf_geometry(path, target_layers):
        try:
            doc = ezdxf.readfile(path)
            msp = doc.modelspace()
            polygons = []
            entities = list(msp.query('LINE LWPOLYLINE POLYLINE'))
            
            # Blok içindeki çizgileri patlatıp listeye ekle
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
            st.error(f"DXF Dosyası Okunamadı: {e}")
            return []

    def calculate_total_length(geometries):
        total = 0
        for geo in geometries:
            for i in range(len(geo) - 1):
                total += math.dist(geo[i], geo[i+1])
        return total

    # --- 6. ARAYÜZ TASARIMI ---
    st.title("🏗️ DUVAR METRAJ PANELİ")
    # Kullanıcı adını güvenli bir şekilde gösteriyoruz.
    st.sidebar.success(f"Hoş geldin, {st.session_state.get('name', 'Kullanıcı')}")

    with st.sidebar:
        st.header("⚙️ Analiz Ayarları")
        uploaded = st.file_uploader("Dosya Seç (DXF veya Görsel)", type=["dxf", "jpg", "png", "jpeg"])
        kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01)
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
                # Mimari projelerde duvarlar çift çizgi olduğu için 2'ye bölüyoruz.
                bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
                final_uzunluk = (raw_len / 2) / bolen

        if geos:
            c1, c2 = st.columns([2, 1])
            with c1:
                st.subheader("🔍 Plan Analiz Görünümü")
                fig, ax = plt.subplots(figsize=(10, 8))
                all_x, all_y = [], []
                for g in geos:
                    xs, ys = zip(*g)
                    all_x.extend(xs); all_y.extend(ys)
                    ax.plot(xs, ys, color="#e67e22", linewidth=0.8)

                # Çizimi otomatik ortalayıp yakınlaştırıyoruz
                if all_x and all_y:
                    x_min, x_max = np.percentile(all_x, [1, 99])
                    y_min, y_max = np.percentile(all_y, [1, 99])
                    ax.set_xlim(x_min, x_max)
                    ax.set_ylim(y_min, y_max)

                ax.set_aspect("equal")
                ax.axis("off")
                st.pyplot(fig)
                plt.close(fig)

            with c2:
                st.subheader("📊 Metraj Sonuçları")
                # Görseldeki (image_148f60) değerleri (56.24 m) referans alarak gösterim.
                st.metric("📏 Toplam Uzunluk", f"{round(final_uzunluk, 2)} m")
                st.metric("🧱 Duvar Alanı", f"{round(final_uzunluk * kat_yuk, 2)} m²")
                
                # Referans sapması hesaplama
                referans_deger = 58.08
                sapma = final_uzunluk - referans_deger
                st.metric("🎯 Referans Sapması", f"{round(sapma, 2)} m", delta=f"{round(sapma, 2)} m", delta_color="inverse")
                
                st.info(f"Hesaplama {birim} üzerinden optimize edildi.")
        else:
            st.warning("⚠️ Katmanlarda veri bulunamadı.")
    else:
        st.info("👋 Başlamak için bir plan dosyası yükleyin.")

elif st.session_state["authentication_status"] is False:
    st.error('Kullanıcı adı veya şifre hatalı')
elif st.session_state["authentication_status"] is None:
    st.warning('Lütfen kullanıcı adı ve şifrenizi giriniz')
