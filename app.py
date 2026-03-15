import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. SAYFA VE GİRİŞ YAPILANDIRMASI ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

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
                st.error("Hatalı giriş!")
    st.stop()

# --- 2. EXCEL VERİ KÜTÜPHANESİ (Paylaştığın Dosyadan Alındı) ---
# Bu liste Excel'deki kalemleri temsil eder
imalat_kutuphanesi = [
    {"poz": "15.150.1006", "ad": "C 30/37 Hazır Beton Dökülmesi (Beton Pompasıyla)", "birim": "m3"},
    {"poz": "15.160.1003/Ö", "ad": "Ø 8- Ø 12 mm Nervürlü Beton Çelik Çubuğu", "birim": "ton"},
    {"poz": "15.180.1003", "ad": "Plywood ile Düz Yüzeyli Betonarme Kalıbı Yapılması", "birim": "m2"},
    {"poz": "15.215.1002", "ad": "19x19x13,5 cm Yatay Delikli Tuğla Duvar (13,5 cm kalınlık)", "birim": "m2"},
    {"poz": "15.275.1106/Ö", "ad": "250 kg Çimento Dozlu Harç ile Kaba Sıva Yapılması", "birim": "m2"},
    {"poz": "15.341.3003", "ad": "Taşyünü Levhalar ile Dış Duvarlarda Isı Yalıtımı (Mantolama)", "birim": "m2"},
    {"poz": "15.540.1323", "ad": "Saf Akrilik Esaslı Su Bazlı Dış Cephe Boyası Yapılması", "birim": "m2"},
    {"poz": "ÖZEL-01", "ad": "İç Cephe Alçı Sıva ve Boya İşleri", "birim": "m2"}
]

# --- 3. DXF ANALİZ MOTORU ---
def get_dxf_geometry(path, target_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        for e in entities:
            if target_layers:
                if not any(t.upper() in e.dxf.layer.upper() for t in target_list): continue
            if e.dxftype() == "INSERT":
                for sub_e in e.virtual_entities():
                    if sub_e.dxftype() in ("LINE", "LWPOLYLINE", "POLYLINE"):
                        pts = [(p[0], p[1]) for p in sub_e.get_points()] if hasattr(sub_e, 'get_points') else [(sub_e.dxf.start[0], sub_e.dxf.start[1]), (sub_e.dxf.end[0], sub_e.dxf.end[1])]
                        geometries.append(pts)
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                geometries.append([(p[0], p[1]) for p in e.get_points()])
            elif e.dxftype() == "LINE":
                geometries.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        return geometries
    except: return []

# --- 4. ARAYÜZ ---
st.sidebar.success("Hoş geldin, BARIŞ")
st.title("🏗️ AKILLI METRAJ VE İMALAT ANALİZİ")

with st.sidebar:
    st.header("📋 İmalat Seçimi")
    # Excel kalemlerini seçilebilir liste yaptık
    secilen_imalat_adi = st.selectbox(
        "Metrajı Yapılacak Kalem", 
        [f"{i['poz']} - {i['ad']}" for i in imalat_kutuphanesi]
    )
    # Seçilen kalemin verilerini ayıkla
    secilen_poz = secilen_imalat_adi.split(" - ")[0]
    secilen_detay = next(item for item in imalat_kutuphanesi if item["poz"] == secilen_poz)

    st.divider()
    st.header("⚙️ Dosya ve Ayarlar")
    uploaded = st.file_uploader("DXF Yükle", type=["dxf"])
    kat_yuk = st.number_input("Yükseklik (Boy) (m)", value=2.85)
    birim_tipi = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katman_ara = st.text_input("DXF Katman Filtresi", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_list = [x.strip() for x in katman_ara.split(",")]
    with st.spinner("Analiz ediliyor..."):
        full_project = get_dxf_geometry(file_path)
        analysis_data = get_dxf_geometry(file_path, target_list)

    if analysis_data:
        # Metraj Hesaplama
        raw_len = sum(math.dist(g[i], g[i+1]) for g in analysis_data for i in range(len(g)-1))
        bolen = 100 if birim_tipi == "cm" else (1000 if birim_tipi == "mm" else 1)
        net_metraj = (raw_len / 2) / bolen 
        miktar = net_metraj * kat_yuk if secilen_detay["birim"] == "m2" else net_metraj

        # Görseller
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🖼️ Plan")
            fig1, ax1 = plt.subplots(); [ax1.plot(*zip(*g), color="gray", lw=0.1, alpha=0.3) for g in full_project]
            ax1.set_aspect("equal"); ax1.axis("off"); st.pyplot(fig1)
        with c2:
            st.subheader("🔍 Seçili İmalat Hattı")
            fig2, ax2 = plt.subplots(); [ax2.plot(*zip(*g), color="#e67e22", lw=1) for g in analysis_data]
            ax2.set_aspect("equal"); ax2.axis("off"); st.pyplot(fig2)

        # --- EXCEL FORMATLI ÇIKTI ---
        st.divider()
        st.subheader(f"📊 Metraj Cetveli: {secilen_detay['ad']}")
        
        df_final = pd.DataFrame({
            "S. NO": [1],
            "POZ/KOD": [secilen_detay["poz"]],
            "İMALATIN ADI": [secilen_detay["ad"]],
            "BİRİM": [secilen_detay["birim"]],
            "EN (Uzunluk)": [round(net_metraj, 2)],
            "BOY (Yükseklik)": [round(kat_yuk, 2) if secilen_detay["birim"] == "m2" else "-"],
            "MİKTAR": [round(miktar, 2)]
        })
        
        st.table(df_final)
        st.download_button("📥 Excel Formatında İndir", df_final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "metraj.csv")
    else:
        st.warning("Seçilen katmanda veri bulunamadı.")
