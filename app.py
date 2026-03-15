import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os

# --- 1. AYARLAR VE GİRİŞ SİSTEMİ ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            # Secrets kontrolü (Streamlit Cloud'da ayarlı olmalıdır)
            try:
                admin_pw = st.secrets["credentials"]["usernames"]["admin"]["password"]
                if user == "admin" and pw == admin_pw:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı kullanıcı adı veya şifre")
            except:
                # Yerel çalışma için yedek (Test amaçlı)
                if user == "admin" and pw == "123":
                    st.session_state.logged_in = True
                    st.rerun()
    st.stop()

# --- 2. DXF VERİ OKUMA MOTORU (GÜNCELLENDİ) ---
def get_dxf_geometry(path, target_layers=None):
    """
    DXF dosyasını okur ve belirtilen katmandaki çizgilerin koordinatlarını döndürür.
    """
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        
        # Katman isimlerini standardize et
        if target_layers:
            target_layers = [t.upper().strip() for t in target_layers if t.strip()]

        # Tüm geometri tiplerini tara
        entities = msp.query('LINE LWPOLYLINE POLYLINE')
        
        for e in entities:
            # Katman filtresi
            if target_layers and e.dxf.layer.upper() not in target_layers:
                continue
            
            pts = []
            if e.dxftype() == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
            
            if len(pts) > 1:
                geometries.append(pts)
        
        return geometries
    except Exception as e:
        st.error(f"Veri Okuma Hatası: {e}")
        return []

# --- 3. ANA ARAYÜZ VE ANALİZ ---
st.sidebar.success(f"Hoş geldin, BARIŞ")

with st.sidebar:
    st.header("⚙️ Proje Ayarları")
    uploaded = st.file_uploader("DXF Dosyası Seç", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katmanlar_input = st.text_input("Hedef Katman (Örn: DUVAR)", "DUVAR")
    
    st.divider()
    cizim_modu = st.radio("Hesaplama Modu", ["Tek Çizgi (Aks)", "Çift Çizgi (Mimari)"], index=1)

if uploaded:
    # 1. DOSYAYI GEÇİCİ OLARAK KAYDET (ezdxf için şart)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    # 2. VERİLERİ ÇEK
    target_list = [x.strip() for x in katmanlar_input.split(",")]
    wall_analysis = get_dxf_geometry(file_path, target_list)

    if wall_analysis:
        # 3. HASSAS UZUNLUK HESABI
        toplam_ham_uzunluk = 0
        for g in wall_analysis:
            for i in range(len(g) - 1):
                # Öklid mesafesi formülü
                dist = math.sqrt((g[i+1][0] - g[i][0])**2 + (g[i+1][1] - g[i][1])**2)
                toplam_ham_uzunluk += dist

        # 4. ÖLÇEK VE MİKTAR DÜZELTMELERİ
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        metre_uzunluk = toplam_ham_uzunluk / bolen

        if cizim_modu == "Çift Çizgi (Mimari)":
            final_uzunluk = metre_uzunluk / 2
        else:
            final_uzunluk = metre_uzunluk

        toplam_alan = final_uzunluk * kat_yuk

        # 5. EKRANA YAZDIRMA
        st.success(f"✅ Veri başarıyla yüklendi: {len(wall_analysis)} adet çizgi bulundu.")
        
        col1, col2, col3 = st.columns(3)
        col1.metric("📏 Toplam Metraj", f"{round(final_uzunluk, 2)} m")
        col2.metric("🧱 Duvar Alanı", f"{round(toplam_alan, 2)} m²")
        col3.metric("📂 Obje Sayısı", len(wall_analysis))

        # Rapor Tablosu
        df_res = pd.DataFrame({
            "Açıklama": ["Duvar Analizi"],
            "Ham Veri (AutoCAD Birimi)": [round(toplam_ham_uzunluk, 2)],
            "Birim": [birim],
            "Net Uzunluk (m)": [round(final_uzunluk, 3)],
            "Yükseklik (m)": [kat_yuk],
            "Alan (m2)": [round(toplam_alan, 3)]
        })
        st.table(df_res)

        # Görselleştirme
        fig, ax = plt.subplots(figsize=(10, 6))
        for g in wall_analysis:
            x, y = zip(*g)
            ax.plot(x, y, color="#2ecc71", linewidth=2)
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)

    else:
        st.warning(f"⚠️ '{katmanlar_input}' katmanında veri bulunamadı. Lütfen AutoCAD katman ismini kontrol edin.")
    
    # Geçici dosyayı sil (Güvenlik için)
    if os.path.exists(file_path):
        os.remove(file_path)
else:
    st.info("💡 Lütfen sol menüden bir DXF dosyası yükleyerek başlayın.")
