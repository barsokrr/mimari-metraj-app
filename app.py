import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. SAYFA YAPILANDIRMASI VE GÜVENLİK ---
st.set_page_config(page_title="SaaS Metraj Pro | Dijital Cetvel", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Kurumsal Giriş")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş Yap"):
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı kimlik bilgileri!")
    st.stop()

# --- 2. EXCEL VERİ BANKASI (REFERANS ALINAN KALEMLER) ---
# Paylaştığın Excel dosyasındaki hiyerarşi buraya aktarıldı
IMALAT_KUTUPHANESI = {
    "01.01.01 - BETONARME İMALATLARI": [
        {"poz": "15.150.1006", "ad": "C 30/37 Hazır Beton Dökülmesi (Pompa ile)", "birim": "m3"},
        {"poz": "15.160.1003/Ö", "ad": "Ø 8- Ø 12 mm Nervürlü Beton Çelik Çubuğu", "birim": "ton"},
        {"poz": "15.180.1003", "ad": "Plywood ile Betonarme Kalıbı Yapılması", "birim": "m2"}
    ],
    "01.01.03 - DUVAR İMALATLARI": [
        {"poz": "15.215.1002", "ad": "19x19x13,5 cm Yatay Delikli Tuğla Duvar", "birim": "m2"},
        {"poz": "15.215.1010", "ad": "20 cm Kalınlığında Gazbeton Duvar Yapılması", "birim": "m2"}
    ],
    "01.01.07 - CEPHE İMALATLARI": [
        {"poz": "15.341.3003", "ad": "Taşyünü Levhalar ile Dış Cephe Mantolama (8cm)", "birim": "m2"},
        {"poz": "15.540.1323", "ad": "Saf Akrilik Esaslı Dış Cephe Boyası Yapılması", "birim": "m2"},
        {"poz": "15.420.1101/Ö", "ad": "Andezit Levha ile Duvar Kaplaması", "birim": "m2"}
    ]
}

# --- 3. ANALİZ MOTORU ---
def get_dxf_geometry(path, target_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geoms = []
        for e in msp.query('LINE LWPOLYLINE POLYLINE INSERT'):
            if target_layers and not any(t.upper() in e.dxf.layer.upper() for t in target_layers):
                continue
            if e.dxftype() == "INSERT":
                for sub_e in e.virtual_entities():
                    if sub_e.dxftype() in ("LINE", "LWPOLYLINE", "POLYLINE"):
                        pts = [(p[0], p[1]) for p in sub_e.get_points()] if hasattr(sub_e, 'get_points') else [(sub_e.dxf.start[0], sub_e.dxf.start[1]), (sub_e.dxf.end[0], sub_e.dxf.end[1])]
                        geoms.append(pts)
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                geoms.append([(p[0], p[1]) for p in e.get_points()])
            elif e.dxftype() == "LINE":
                geoms.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        return geoms
    except: return []

# --- 4. ANA ARAYÜZ ---
st.sidebar.success("Oturum Açık: BARIŞ")
st.title("🏗️ Dijital Metraj Cetveli ve Plan Analizi")

with st.sidebar:
    st.header("📋 Excel İmalat Seçimi")
    ana_grup = st.selectbox("Ana İş Grubu", list(IMALAT_KUTUPHANESI.keys()))
    alt_kalemler = IMALAT_KUTUPHANESI[ana_grup]
    secilen_item = st.selectbox("İmalat Kalemi (Poz)", [f"{i['poz']} - {i['ad']}" for i in alt_kalemler])
    
    # Seçilen pozun detaylarını çek
    poz_kod = secilen_item.split(" - ")[0]
    imalat_detay = next(item for item in alt_kalemler if item["poz"] == poz_kod)

    st.divider()
    st.header("⚙️ Dosya Ayarları")
    uploaded = st.file_uploader("DXF Dosyasını Buraya Bırakın", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği / Boy (m)", value=2.85)
    birim_faktor = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katman_filtre = st.text_input("DXF Katman İsmi", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_layers = [x.strip() for x in katman_filtre.split(",")]
    full_proj = get_dxf_geometry(file_path)
    filtered_proj = get_dxf_geometry(file_path, target_layers)

    if filtered_proj:
        # Metraj Hesaplama (Çift çizgi optimizasyonu dahil)
        raw_len = sum(math.dist(g[i], g[i+1]) for g in filtered_proj for i in range(len(g)-1))
        bolen = 100 if birim_faktor == "cm" else (1000 if birim_faktor == "mm" else 1)
        net_uzunluk = (raw_len / 2) / bolen
        miktar = net_uzunluk * kat_yuk if imalat_detay["birim"] == "m2" else net_uzunluk

        # Görsel Paneller
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🖼️ Mimari Plan")
            fig1, ax1 = plt.subplots(); [ax1.plot(*zip(*g), color="gray", lw=0.1, alpha=0.3) for g in full_proj]
            ax1.set_aspect("equal"); ax1.axis("off"); st.pyplot(fig1)
        with col2:
            st.subheader("🔍 Analiz Edilen Hatlar")
            fig2, ax2 = plt.subplots(); [ax2.plot(*zip(*g), color="#e67e22", lw=1) for g in filtered_proj]
            ax2.set_aspect("equal"); ax2.axis("off"); st.pyplot(fig2)

        # --- EXCEL FORMATLI METRAJ CETVELİ ---
        st.divider()
        st.subheader(f"📊 {ana_grup} - Metraj Cetveli")
        
        # Excel dosyasındaki resmi sütun yapısı
        df_final = pd.DataFrame({
            "S. NO": [1],
            "POZ/KOD": [imalat_detay["poz"]],
            "İMALATIN ADI": [imalat_detay["ad"]],
            "BİRİM": [imalat_detay["birim"]],
            "EN (Uzunluk)": [round(net_uzunluk, 2)],
            "BOY (Yükseklik)": [round(kat_yuk, 2) if imalat_detay["birim"] == "m2" else "-"],
            "MİKTAR": [round(miktar, 2)]
        })
        
        st.table(df_final)
        
        # Profesyonel İndirme Butonu
        csv_data = df_final.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📥 Resmi Metraj Cetvelini İndir (Excel CSV)",
            data=csv_data,
            file_name=f"{poz_kod}_metraj_cetveli.csv",
            mime="text/csv"
        )
    else:
        st.warning("Seçilen katmanda veri bulunamadı. Lütfen DXF katman ismini kontrol edin.")
else:
    st.info("💡 Analize başlamak için sol menüden imalat kalemini seçin ve DXF dosyanızı yükleyin.")
