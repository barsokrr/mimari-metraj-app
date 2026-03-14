import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. AYARLAR VE GİRİŞ ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ Mimari Metraj Giriş")
    with st.form("login"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı giriş!")
    st.stop()

# --- 2. DXF ANALİZ MOTORU ---
def get_dxf_geometry(path, target_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        # Blokları ve temel geometrileri oku
        for e in msp.query('LINE LWPOLYLINE POLYLINE ARC CIRCLE INSERT'):
            if target_layers:
                layer_name = e.dxf.layer.upper()
                if not any(t.upper() in layer_name for t in target_layers):
                    continue
            
            if e.dxftype() == "INSERT":
                for sub_e in e.virtual_entities():
                    if sub_e.dxftype() in ("LINE", "LWPOLYLINE", "POLYLINE"):
                        pts = [(p[0], p[1]) for p in sub_e.get_points()] if hasattr(sub_e, 'get_points') else [(sub_e.dxf.start[0], sub_e.dxf.start[1]), (sub_e.dxf.end[0], sub_e.dxf.end[1])]
                        if len(pts) > 1: geometries.append(pts)
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
                if len(pts) > 1: geometries.append(pts)
            elif e.dxftype() == "LINE":
                geometries.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        return geometries
    except:
        return []

# --- 3. ANA PANEL ---
st.sidebar.success("Hoş geldin, BARIŞ")
st.title("🏗️ Mimari Duvar Metrajı")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("DXF Dosyası", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (Boy) (m)", value=2.85)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katmanlar = st.text_input("Katman Filtresi", "DUVAR")
    # Excel'den gelen Poz Bilgisi
    poz_no = st.text_input("Poz/Kod (Excel'den)", "15.150.1006")
    imalat_adi = st.text_input("İmalat Adı", "Tuğla Duvar Yapılması (20cm)")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_list = [x.strip() for x in katmanlar.split(",")]
    full_project = get_dxf_geometry(file_path)
    wall_analysis = get_dxf_geometry(file_path, target_list)

    if wall_analysis:
        # Metraj Hesaplama
        raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_analysis for i in range(len(g)-1))
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        net_uzunluk = (raw_len / 2) / bolen # Çift çizgi düzeltmesi
        toplam_alan = net_uzunluk * kat_yuk

        st.success(f"✅ {len(wall_analysis)} adet duvar objesi tespit edildi.")

        # Görselleştirme
        col_img1, col_img2 = st.columns(2)
        with col_img1:
            st.subheader("🖼️ Orijinal Plan")
            fig1, ax1 = plt.subplots(figsize=(8, 8))
            for g in full_project:
                xs, ys = zip(*g)
                ax1.plot(xs, ys, color="gray", linewidth=0.1, alpha=0.3)
            ax1.set_aspect("equal")
            ax1.axis("off")
            st.pyplot(fig1)

        with col_img2:
            st.subheader("🔍 Duvar Analizi")
            fig2, ax2 = plt.subplots(figsize=(8, 8))
            for g in wall_analysis:
                xs, ys = zip(*g)
                ax2.plot(xs, ys, color="#e67e22", linewidth=1)
            ax2.set_aspect("equal")
            ax2.axis("off")
            st.pyplot(fig2)

        # --- EXCEL FORMATINDA METRAJ CETVELİ ---
        st.divider()
        st.subheader("📊 İnşaat Yapı İşleri Metraj Cetveli")
        
        # Excel dosyasındaki sütun yapısına uygun DataFrame oluşturma
        metraj_df = pd.DataFrame({
            "S. NO": [1],
            "POZ/KOD": [poz_no],
            "İMALATIN ADI": [imalat_adi],
            "BİRİM": ["m2"],
            "EN (m)": [round(net_uzunluk, 2)],
            "BOY (m)": [kat_yuk],
            "MİKTAR": [round(toplam_alan, 2)],
            "TOPLAM TUTAR": ["Hesaplanacak"]
        })
        
        st.table(metraj_df)
        
        # İndirme Seçeneği
        csv = metraj_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Excel Formatında (CSV) İndir", csv, "duvar_metraj_cetveli.csv", "text/csv")
        
        st.info("💡 Not: Uzunluk hesabı (EN), mimari planlardaki çift çizgi duvar yapısına göre otomatik optimize edilmiştir.")
    else:
        st.warning("⚠️ Seçilen katmanlarda veri bulunamadı.")
else:
    st.info("👋 Başlamak için bir DXF dosyası yükleyin.")
