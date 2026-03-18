import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. SAYFA VE OTURUM YAPILANDIRMASI ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

# Oturum durumunu kontrol et (Senin başarılı giriş sistemin)
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("Fi-le Yazılım")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            # admin/123 kontrolü
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre")
    st.stop()

# --- 2. GELİŞMİŞ DXF OKUMA FONKSİYONU ---
def get_dxf_geometry(path, target_layers=None):
    """
    target_layers None ise tüm projeyi okur. 
    Liste verilirse sadece o katmanları filtreler.
    """
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        entities = msp.query('LINE LWPOLYLINE POLYLINE')
        
        for e in entities:
            # Katman filtresi kontrolü
            if target_layers:
                layer_name = e.dxf.layer.upper()
                if not any(t.upper() in layer_name for t in target_layers):
                    continue
            
            # Geometri tipine göre koordinatları al
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
                if len(pts) > 1: geometries.append(pts)
            elif e.dxftype() == "LINE":
                geometries.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        return geometries
    except Exception:
        return []

# --- 3. ANA ARAYÜZ VE ANALİZ ---
st.sidebar.success(f"Hoş geldin, BARIŞ") # Görselindeki isim
if st.sidebar.button("Çıkış Yap"):
    st.session_state.logged_in = False
    st.rerun()

st.title("Metraj analizi")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("Dosya Seç (DXF)", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katmanlar = st.text_input("Katman Filtresi", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    # Veri Hazırlama
    target_list = [x.strip() for x in katmanlar.split(",")]
    full_project = get_dxf_geometry(file_path) # Tüm proje
    wall_analysis = get_dxf_geometry(file_path, target_list) # Filtrelenmiş duvarlar

    if wall_analysis:
        # Hesaplama Mantığı
        raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_analysis for i in range(len(g)-1))
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        net_uzunluk = (raw_len / 2) / bolen # Mimari çift çizgi düzeltmesi
        toplam_alan = net_uzunluk * kat_yuk

        st.success(f"✅ {len(wall_analysis)} adet duvar objesi tespit edildi.")

        # --- YAN YANA GÖRSELLEŞTİRME ---
        col_img1, col_img2 = st.columns(2)
        
        with col_img1:
            st.subheader("Gerçek Plan")
            fig1, ax1 = plt.subplots(figsize=(8, 8))
            for g in full_project:
                xs, ys = zip(*g)
                ax1.plot(xs, ys, color="gray", linewidth=0.2, alpha=0.4)
            ax1.set_aspect("equal")
            ax1.axis("off")
            st.pyplot(fig1)

        with col_img2:
            st.subheader("Duvar analizi")
            fig2, ax2 = plt.subplots(figsize=(8, 8))
            for g in wall_analysis:
                xs, ys = zip(*g)
                ax2.plot(xs, ys, color="#e67e22", linewidth=1)
            ax2.set_aspect("equal")
            ax2.axis("off")
            st.pyplot(fig2)

        # --- METRAJ BİLGİLERİ VE RAPOR ---
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("📏 Toplam Uzunluk", f"{round(net_uzunluk, 2)} m")
        c2.metric("🧱 Toplam Duvar Alanı", f"{round(toplam_alan, 2)} m²")
        
        # Rapor Tablosu
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
        st.warning("⚠️ Seçilen katmanda veri bulunamadı.")
