import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. SAYFA VE OTURUM AYARLARI ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Giriş Sistemi (Bypass)
if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            try:
                # Secrets'tan admin şifresini kontrol et
                if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                    st.session_state.logged_in = True
                    st.session_state.name = st.secrets["credentials"]["usernames"]["admin"]["name"]
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre")
            except:
                st.error("Yapılandırma dosyası (Secrets) bulunamadı.")
    st.stop()

# --- 2. GELİŞMİŞ DXF ANALİZ MOTORU ---
def get_dxf_data(path, target_layers=None):
    """
    Tüm nesne tiplerini (Bloklar, Yaylar, Daireler) destekleyen eksiksiz okuyucu.
   
    """
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geoms = []
        
        # Orijinal plandaki eksikliği gidermek için kapsamlı sorgu
        entities = msp.query('LINE LWPOLYLINE POLYLINE ARC CIRCLE INSERT')
        
        for e in entities:
            # Filtreleme (Sadece duvar analizi yapılıyorsa)
            if target_layers:
                layer_name = e.dxf.layer.upper()
                if not any(t.upper() in layer_name for t in target_layers):
                    continue

            # Nesne Türüne Göre İşleme
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
                if len(pts) > 1: geoms.append(pts)
            
            elif e.dxftype() == "LINE":
                geoms.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
            
            elif e.dxftype() in ("ARC", "CIRCLE"):
                # Yay ve daireleri düz çizgi segmentlerine bölerek tam gösterir
                pts = [(p[0], p[1]) for p in e.flattening(distance=0.1)]
                if len(pts) > 1: geoms.append(pts)

            elif e.dxftype() == "INSERT":
                # Blok içindeki kapı/pencere vb. nesneleri çözümler
                for sub_e in e.virtual_entities():
                    if sub_e.dxftype() == "LINE":
                        geoms.append([(sub_e.dxf.start[0], sub_e.dxf.start[1]), 
                                      (sub_e.dxf.end[0], sub_e.dxf.end[1])])
                    elif sub_e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                        pts = [(p[0], p[1]) for p in sub_e.get_points()]
                        if len(pts) > 1: geoms.append(pts)
        
        return geoms
    except Exception:
        return []

# --- 3. ANA PANEL VE GÖRSELLEŞTİRME ---
st.sidebar.success(f"Hoş geldin, {st.session_state.get('name', 'BARIŞ')}") #
if st.sidebar.button("Çıkış Yap"):
    st.session_state.logged_in = False
    st.rerun()

st.title("🏗️ DUVAR METRAJ VE PLAN ANALİZİ")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("Dosya Seç (DXF)", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katmanlar = st.text_input("Analiz Katmanı (Örn: DUVAR)", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    # Analizleri Başlat
    target_list = [x.strip() for x in katmanlar.split(",")]
    full_project = get_dxf_data(file_path) # Tüm proje
    wall_analysis = get_dxf_data(file_path, target_list) # Filtreli duvarlar

    if wall_analysis:
        # Metraj Hesaplamaları
        raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_analysis for i in range(len(g)-1))
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        net_uzunluk = (raw_len / 2) / bolen # Mimari çift çizgi düzeltmesi
        toplam_alan = net_uzunluk * kat_yuk

        st.success(f"✅ {len(wall_analysis)} adet duvar objesi tespit edildi.")

        # --- YAN YANA GÖRSEL PANELLER ---
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🖼️ Orijinal Plan (Tümü)")
            fig1, ax1 = plt.subplots(figsize=(10, 10))
            for g in full_project:
                xs, ys = zip(*g)
                # İnce ve hafif şeffaf çizgilerle profesyonel arka plan
                ax1.plot(xs, ys, color="gray", linewidth=0.2, alpha=0.3)
            ax1.set_aspect("equal")
            ax1.axis("off")
            st.pyplot(fig1)

        with col2:
            st.subheader("🔍 Duvar Analizi (Filtreli)")
            fig2, ax2 = plt.subplots(figsize=(10, 10))
            for g in wall_analysis:
                xs, ys = zip(*g)
                # Belirgin turuncu çizgilerle metraj analizi
                ax2.plot(xs, ys, color="#e67e22", linewidth=1.2)
            ax2.set_aspect("equal")
            ax2.axis("off")
            st.pyplot(fig2)

        # --- METRAJ CETVELİ VE RAPOR ---
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("📏 Toplam Uzunluk", f"{round(net_uzunluk, 2)} m")
        m2.metric("🧱 Toplam Duvar Alanı", f"{round(toplam_alan, 2)} m²")
        
        df = pd.DataFrame({
            "Açıklama": ["Toplam Duvar Metrajı"],
            "Uzunluk (m)": [round(net_uzunluk, 4)],
            "Yükseklik (m)": [kat_yuk],
            "Alan (m2)": [round(toplam_alan, 4)]
        })
        st.table(df)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Metraj Cetvelini İndir (CSV)", csv, "metraj_raporu.csv", "text/csv")
        
        st.info("💡 Not: Uzunluk hesabı mimari çift çizgiye göre otomatik optimize edilmiştir.")
    else:
        st.warning("⚠️ Seçilen katmanlarda çizim bulunamadı. Lütfen katman adını kontrol edin.")
else:
    st.info("👋 Başlamak için bir DXF dosyası yükleyin.")
