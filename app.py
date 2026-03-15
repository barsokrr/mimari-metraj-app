import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. AYARLAR VE GÜVENLİK ---
st.set_page_config(page_title="SaaS Metraj Pro | Hata Ayıklanmış", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre")
    st.stop()

# --- 2. GELİŞMİŞ GEOMETRİ MOTORU (Kusursuz Hesaplama) ---
def get_dxf_geometry(path, target_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        
        # Filtreyi temizle
        if target_layers:
            target_layers = [t.upper().strip() for t in target_layers]

        # LINE, LWPOLYLINE ve POLYLINE objelerini tara
        entities = msp.query('LINE LWPOLYLINE POLYLINE')
        
        for e in entities:
            if target_layers and e.dxf.layer.upper() not in target_layers:
                continue
            
            pts = []
            if e.dxftype() == "LINE":
                # LINE objesi için doğrudan start ve end koordinatları
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                # Polyline noktalarını al (3D veriyi 2D'ye indirge)
                pts = [(p[0], p[1]) for p in e.get_points()]
            
            if len(pts) > 1:
                geometries.append(pts)
        return geometries
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}")
        return []

# --- 3. ANA ARAYÜZ ---
st.sidebar.success(f"Operatör: BARIŞ")

with st.sidebar:
    st.header("⚙️ Proje Ayarları")
    uploaded = st.file_uploader("DXF Dosyası Yükle", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
    birim_katsayi = st.selectbox("Çizim Birimi (AutoCAD Unit)", ["cm", "mm", "m"], index=0)
    katmanlar = st.text_input("Hedef Katman (Layer)", "DUVAR")
    
    st.divider()
    st.subheader("🛠️ Hesaplama Modu")
    # EN ÖNEMLİ KISIM: Tek çizgi mi çift çizgi mi?
    cizim_tipi = st.radio("Çizim Tipi", ["Tek Çizgi (Aks)", "Çift Çizgi (Mimari)"], index=1)

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_list = [x.strip() for x in katmanlar.split(",")]
    wall_analysis = get_dxf_geometry(file_path, target_list)

    if wall_analysis:
        # HASSAS UZUNLUK HESABI
        toplam_ham_uzunluk = 0
        for segment in wall_analysis:
            for i in range(len(segment) - 1):
                # Öklid Mesafesi: sqrt((x2-x1)^2 + (y2-y1)^2)
                d = math.sqrt((segment[i+1][0] - segment[i][0])**2 + (segment[i+1][1] - segment[i][1])**2)
                toplam_ham_uzunluk += d

        # Birim Dönüştürme
        bolen = 100 if birim_katsayi == "cm" else (1000 if birim_katsayi == "mm" else 1)
        metre_uzunluk = toplam_ham_uzunluk / bolen

        # Mimari Düzeltme: Eğer çift çizgi ise toplamı 2'ye böl
        if cizim_tipi == "Çift Çizgi (Mimari)":
            final_uzunluk = metre_uzunluk / 2
        else:
            final_uzunluk = metre_uzunluk

        toplam_alan = final_uzunluk * kat_yuk

        # --- SONUÇ PANELİ ---
        st.success(f"✅ Analiz Tamamlandı: {len(wall_analysis)} adet obje işlendi.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("📏 Net Uzunluk", f"{round(final_uzunluk, 3)} m")
        with c2:
            st.metric("🧱 Toplam Alan", f"{round(toplam_alan, 3)} m²")

        # Rapor Tablosu
        df = pd.DataFrame({
            "İmalat": ["Duvar Metrajı"],
            "Ham Veri (Unit)": [round(toplam_ham_uzunluk, 2)],
            "Birim": [birim_katsayi],
            "Net Uzunluk (m)": [round(final_uzunluk, 3)],
            "Yükseklik (m)": [kat_yuk],
            "Toplam Alan (m2)": [round(toplam_alan, 3)]
        })
        st.table(df)
        
        # Görselleştirme
        fig, ax = plt.subplots(figsize=(10, 5))
        for g in wall_analysis:
            xs, ys = zip(*g)
            ax.plot(xs, ys, color="#e67e22", linewidth=1.5)
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)
    else:
        st.warning("Seçilen katmanda veri bulunamadı.")
