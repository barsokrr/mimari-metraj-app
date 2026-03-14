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
    st.title("🏗️ SaaS Metraj Giriş")
    with st.form("login"):
        user = st.text_input("User")
        pw = st.text_input("Pass", type="password")
        if st.form_submit_button("Giriş"):
            if user == "admin" and pw == st.secrets["credentials"]["usernames"]["admin"]["password"]:
                st.session_state.logged_in = True
                st.rerun()
    st.stop()

# --- 2. GELİŞMİŞ GEOMETRİ MOTORU (EKSİKSİZ TESPİT) ---
def process_entity(e, geoms, target_layers=None):
    """Nesneleri türlerine göre ayrıştırır ve koordinatlarını çıkarır."""
    layer = e.dxf.layer.upper().strip()
    is_target = True if not target_layers else any(t.upper() in layer for t in target_layers)
    
    if is_target:
        if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) > 1: geoms.append(pts)
        elif e.dxftype() == "LINE":
            geoms.append([(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])])
        elif e.dxftype() in ("ARC", "CIRCLE"):
            pts = [(p[0], p[1]) for p in e.flattening(distance=0.1)]
            if len(pts) > 1: geoms.append(pts)

def get_dxf_data_pro(path, target_layers=None):
    """Blok içindeki (nested) tüm verileri dünya koordinatlarına çevirerek okur."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geoms = []
        
        # 1. Ana Modelspace Nesneleri
        for e in msp.query('LINE LWPOLYLINE POLYLINE ARC CIRCLE'):
            process_entity(e, geoms, target_layers)
            
        # 2. Bloklar (INSERT) - Kapı, pencere ve duvar blokları
        for insert in msp.query('INSERT'):
            # virtual_entities() tüm blok hiyerarşisini düz bir listeye çevirir
            for sub_e in insert.virtual_entities():
                process_entity(sub_e, geoms, target_layers)
        
        return geoms
    except:
        return []

# --- 3. ANA PANEL ---
st.title("🏗️ DUVAR METRAJ VE PLAN ANALİZİ")

with st.sidebar:
    st.header("⚙️ Proje Ayarları")
    uploaded = st.file_uploader("Dosya Seç (DXF)", type=["dxf"])
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85)
    birim = st.selectbox("Birim", ["cm", "mm", "m"])
    katman_input = st.text_input("Analiz Katmanı (İçerenleri arar)", "DUVAR")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    # Katman filtresini listeye çevir
    target_list = [x.strip() for x in katman_input.split(",")] if katman_input else None
    
    # Veri İşleme
    with st.spinner("Plan analiz ediliyor, lütfen bekleyin..."):
        all_lines = get_dxf_data_pro(file_path, None) # Görsel için hepsi
        wall_lines = get_dxf_data_pro(file_path, target_list) # Metraj için duvarlar

    if wall_lines:
        # Hesaplama: Çift çizgi / 2 mantığı
        raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_lines for i in range(len(g)-1))
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        net_m = (raw_len / 2) / bolen
        toplam_m2 = net_m * kat_yuk

        st.success(f"✅ {len(wall_lines)} adet duvar nesnesi analiz edildi.")

        # Görselleştirme
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🖼️ Orijinal Plan")
            fig1, ax1 = plt.subplots(figsize=(8, 8))
            for g in all_lines:
                xs, ys = zip(*g)
                ax1.plot(xs, ys, color="gray", linewidth=0.1, alpha=0.3)
            ax1.set_aspect("equal")
            ax1.axis("off")
            st.pyplot(fig1)

        with col2:
            st.subheader("🔍 Duvar Analizi")
            fig2, ax2 = plt.subplots(figsize=(8, 8))
            for g in wall_lines:
                xs, ys = zip(*g)
                ax2.plot(xs, ys, color="#e67e22", linewidth=1)
            ax2.set_aspect("equal")
            ax2.axis("off")
            st.pyplot(fig2)

        # Tablo ve Rapor
        st.divider()
        m1, m2 = st.columns(2)
        m1.metric("Toplam Uzunluk", f"{round(net_m, 2)} m")
        m2.metric("Duvar Alanı", f"{round(toplam_m2, 2)} m²")

        df = pd.DataFrame({
            "Açıklama": ["Duvar Metrajı"],
            "Uzunluk (m)": [round(net_m, 4)],
            "Yükseklik (m)": [kat_yuk],
            "Alan (m2)": [round(toplam_m2, 4)]
        })
        st.table(df)
        st.download_button("📥 Excel/CSV İndir", df.to_csv(index=False).encode('utf-8'), "metraj.csv")
    else:
        st.warning(f"⚠️ '{katman_input}' ismini içeren bir katman bulundu ancak içinde çizgi yok veya katman ismi hatalı.")
        # Dosyadaki tüm katmanları göstererek kullanıcıya yardımcı olalım
        try:
            temp_doc = ezdxf.readfile(file_path)
            existing_layers = [l.dxf.name for l in temp_doc.layers]
            st.info(f"Dosyadaki mevcut katmanlar: {', '.join(existing_layers[:15])}...")
        except: pass
