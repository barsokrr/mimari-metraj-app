import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
from datetime import datetime

# --- 1. KURUMSAL YAPILANDIRMA ---
st.set_page_config(page_title="Metraj Pro | Mühendislik Çözümleri", layout="wide", page_icon="🏗️")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🛡️ Kurumsal Metraj Giriş Paneli")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Sisteme Giriş Yap"):
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Yetkisiz Erişim: Bilgilerinizi kontrol edin.")
    st.stop()

# --- 2. EXCEL REFERANS VERİ TABANI (Tüm Kalemler) ---
# Excel dosyanızdaki hiyerarşi ve birimler referans alınmıştır.
IS_GRUPLARI = {
    "01.01.01 BETONARME İMALATLARI": [
        {"poz": "15.150.1006", "ad": "C 30/37 Hazır Beton Dökülmesi (Pompa ile)", "birim": "m3"},
        {"poz": "15.160.1003/Ö", "ad": "Ø 8- Ø 12 mm Nervürlü Çelik (Kesme, Bükme)", "birim": "ton"},
        {"poz": "15.180.1003", "ad": "Plywood ile Düz Yüzeyli Betonarme Kalıbı", "birim": "m2"}
    ],
    "01.01.03 DUVAR İMALATLARI": [
        {"poz": "15.215.1002", "ad": "19x19x13,5 cm Yatay Delikli Tuğla Duvar", "birim": "m2"},
        {"poz": "15.215.1010", "ad": "20 cm Kalınlığında Gazbeton Duvar (Ytong)", "birim": "m2"}
    ],
    "01.01.07 CEPHE İMALATLARI": [
        {"poz": "15.341.3003", "ad": "8 cm Taşyünü Levha ile Mantolama", "birim": "m2"},
        {"poz": "15.420.1101/Ö", "ad": "3 cm Andezit Levha Duvar Kaplaması", "birim": "m2"},
        {"poz": "15.540.1323", "ad": "Akrilik Su Bazlı Dış Cephe Boyası", "birim": "m2"}
    ]
}

# --- 3. GELİŞMİŞ GEOMETRİ ANALİZ MOTORU ---
def analyze_dxf(path, filter_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        all_lines = []
        filtered_lines = []
        
        # Tüm nesneleri tara (Bloklar dahil)
        query_str = 'LINE LWPOLYLINE POLYLINE INSERT'
        for e in msp.query(query_str):
            layer = e.dxf.layer.upper()
            
            # Nesne geometrisini çıkar (Recursive/Derin tarama)
            pts_list = []
            if e.dxftype() == "INSERT":
                for sub in e.virtual_entities():
                    if hasattr(sub, 'get_points'):
                        pts_list.append([(p[0], p[1]) for p in sub.get_points()])
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts_list.append([(p[0], p[1]) for p in e.get_points()])
            elif e.dxftype() == "LINE":
                pts_list.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
            
            # Koordinatları depola
            for pts in pts_list:
                all_lines.append(pts)
                if filter_layers and any(f.upper() in layer for f in filter_layers):
                    filtered_lines.append(pts)
                    
        return all_lines, filtered_lines
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return [], []

# --- 4. ANA PANEL VE YÖNETİM ---
st.sidebar.markdown(f"**Operatör:** BARIŞ  \n**Tarih:** {datetime.now().strftime('%d.%m.%Y')}")

with st.sidebar:
    st.header("📋 İmalat Tanımlama")
    grup = st.selectbox("İş Grubu Seçin", list(IS_GRUPLARI.keys()))
    kalem_secimi = st.selectbox("Poz Seçin", [f"{i['poz']} | {i['ad']}" for i in IS_GRUPLARI[grup]])
    
    # Seçilen Poz Detayı
    secilen_poz_no = kalem_secimi.split(" | ")[0]
    secilen_poz_detay = next(i for i in IS_GRUPLARI[grup] if i["poz"] == secilen_poz_no)
    
    st.divider()
    st.header("⚙️ Teknik Ayarlar")
    uploaded_file = st.file_uploader("Mimari Proje (DXF)", type=["dxf"])
    k_yukseklik = st.number_input("H (Yükseklik) (m)", value=2.85, format="%.2f")
    c_birim = st.selectbox("Proje Ölçeği", ["cm", "mm", "m"], index=0)
    layer_name = st.text_input("Katman (Layer) Filtresi", "DUVAR")

# --- 5. ANALİZ VE HESAPLAMA ---
if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        path = tmp.name

    target_layers = [l.strip() for l in layer_name.split(",")]
    with st.spinner("Geometri analiz ediliyor..."):
        full_p, filtered_p = analyze_dxf(path, target_layers)

    if filtered_p:
        # Uzunluk Hesabı (Ölçek düzeltmesi ile)
        raw_l = sum(math.dist(p[i], p[i+1]) for line in filtered_p for i in range(len(line)-1))
        scale = 100 if c_birim == "cm" else (1000 if c_birim == "mm" else 1)
        
        # Mimari Proje Düzeltmesi: Çift çizgi duvarlar için L/2 kullanılır
        l_net = (raw_l / 2) / scale
        
        # Miktar Hesabı (Birim Tipine Göre)
        if secilen_poz_detay["birim"] == "m2":
            miktar = l_net * k_yukseklik
        else:
            miktar = l_net # m, mtül vb.

        # --- GÖRSEL ANALİZ ---
        st.subheader(f"🔍 Analiz Sonucu: {secilen_poz_no}")
        col_a, col_b = st.columns(2)
        
        with col_a:
            st.caption("Orijinal Plan Katmanları")
            fig1, ax1 = plt.subplots(); [ax1.plot(*zip(*line), color="#bdc3c7", lw=0.2) for line in full_p]
            ax1.set_aspect("equal"); ax1.axis("off"); st.pyplot(fig1)
            
        with col_b:
            st.caption("Metrajı Alınan İmalat Hatları")
            fig2, ax2 = plt.subplots(); [ax2.plot(*zip(*line), color="#d35400", lw=1.2) for line in filtered_p]
            ax2.set_aspect("equal"); ax2.axis("off"); st.pyplot(fig2)

        # --- RESMİ METRAJ CETVELİ (EXCEL FORMATI) ---
        st.divider()
        st.subheader("📊 Metraj Cetveli")
        
        cetvel_df = pd.DataFrame({
            "S. NO": [1],
            "POZ/KOD": [secilen_poz_no],
            "İMALATIN ADI": [secilen_poz_detay["ad"]],
            "BİRİM": [secilen_poz_detay["birim"]],
            "EN (L)": [round(l_net, 2)],
            "BOY (H)": [round(k_yukseklik, 2) if secilen_poz_detay["birim"] == "m2" else "-"],
            "MİKTAR": [round(miktar, 2)]
        })
        
        st.dataframe(cetvel_df, use_container_width=True)
        
        # İndirme İşlemi
        csv = cetvel_df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 Excel Metrajını İndir", csv, f"{secilen_poz_no}_metraj.csv", "text/csv")
        
        st.info(f"💡 Analiz Notu: {c_birim} ölçeğinde {len(filtered_p)} adet imalat çizgisi tespit edilmiştir.")
    else:
        st.warning(f"'{layer_name}' katmanında veri bulunamadı. Lütfen AutoCAD katman ismini kontrol edin.")
