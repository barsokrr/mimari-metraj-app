import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 1. AYARLAR VE GİRİŞ SİSTEMİ ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Giriş"):
            # Secrets üzerinden admin/123 kontrolü
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı kullanıcı adı veya şifre")
    st.stop()

# --- 2. GELİŞMİŞ DXF ANALİZ MOTORU ---
def process_entity(e, geoms, target_layers=None):
    """Geometriyi ayrıştırır ve koordinatları listeye ekler."""
    layer = e.dxf.layer.upper().strip()
    is_target = True if not target_layers else any(t.upper() in layer for t in target_layers)
    
    if is_target:
        if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) > 1: geoms.append(pts)
        elif e.dxftype() == "LINE":
            geoms.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        elif e.dxftype() in ("ARC", "CIRCLE"):
            # Yayları ve daireleri düz çizgi parçalarına bölerek çizer
            pts = [(p[0], p[1]) for p in e.flattening(distance=0.1)]
            if len(pts) > 1: geoms.append(pts)

def get_dxf_data(path, target_layers=None):
    """Blokları (INSERT) ve tüm nesneleri çözen ana fonksiyon."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geoms = []
        # virtual_entities() ile blokların içindeki çizgileri dünya koordinatlarına çevirir
        for e in msp.query('LINE LWPOLYLINE POLYLINE ARC CIRCLE INSERT'):
            if e.dxftype() == "INSERT":
                for sub_e in e.virtual_entities():
                    process_entity(sub_e, geoms, target_layers)
            else:
                process_entity(e, geoms, target_layers)
        return geoms
    except:
        return []

# --- 3. ANA ARAYÜZ VE ANALİZ ---
st.sidebar.success(f"Hoş geldin, BARIŞ") #
if st.sidebar.button("Çıkış Yap"):
    st.session_state.logged_in = False
    st.rerun()

st.title("🏗️ DUVAR METRAJ VE PLAN ANALİZİ")

with st.sidebar:
    st.header("⚙️ Proje Ayarları")
    uploaded = st.file_uploader("Dosya Seç (DXF)", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katmanlar_input = st.text_input("Analiz Katmanı (Örn: DUVAR)", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    target_list = [x.strip() for x in katmanlar_input.split(",")]
    
    with st.spinner("Plan analiz ediliyor..."):
        all_lines = get_dxf_data(file_path, None)  # Orijinal plan
        wall_lines = get_dxf_data(file_path, target_list)  # Sadece duvarlar

    if wall_lines:
        # Metraj Hesaplama: Mimari çift çizgi optimizasyonu
        raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_lines for i in range(len(g)-1))
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        net_uzunluk = (raw_len / 2) / bolen
        toplam_alan = net_uzunluk * kat_yuk

        st.success(f"✅ {len(wall_lines)} adet duvar objesi tespit edildi.")

        # Görselleştirme Panelleri
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🖼️ Orijinal Plan (Tümü)")
            fig1, ax1 = plt.subplots(figsize=(10, 10))
            for g in all_lines:
                xs, ys = zip(*g)
                ax1.plot(xs, ys, color="gray", linewidth=0.1, alpha=0.3)
            ax1.set_aspect("equal")
            ax1.axis("off")
            st.pyplot(fig1)

        with col2:
            st.subheader("🔍 Duvar Analizi (Filtreli)")
            fig2, ax2 = plt.subplots(figsize=(10, 10))
            for g in wall_lines:
                xs, ys = zip(*g)
                ax2.plot(xs, ys, color="#e67e22", linewidth=1)
            ax2.set_aspect("equal")
            ax2.axis("off")
            st.pyplot(fig2)

        # Metraj Bilgileri
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
    else:
        st.warning(f"⚠️ '{katmanlar_input}' katmanında veri bulunamadı.")
        # Dosyadaki katmanları göstererek yardımcı olalım
        try:
            temp_doc = ezdxf.readfile(file_path)
            st.info(f"Mevcut Katmanlar: {', '.join([l.dxf.name for l in temp_doc.layers][:15])}...")
        except: pass
else:
    st.info("👋 Başlamak için bir DXF dosyası yükleyin.")
