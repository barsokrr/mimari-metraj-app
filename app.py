import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# --- 1. SİSTEM YAPILANDIRMASI ---
st.set_page_config(page_title="SaaS Metraj Pro | Kurumsal Ar-Ge", layout="wide", page_icon="🏢")

# Profesyonel UI Teması
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    .stMetric { border: 1px solid #c8d6e5; padding: 15px; border-radius: 12px; background: #ffffff; box-shadow: 2px 2px 10px rgba(0,0,0,0.05); }
    .stButton>button { width: 100%; border-radius: 8px; height: 3em; background-color: #2e86de; color: white; }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Kurumsal Metraj Giriş Paneli")
    with st.form("auth_form"):
        user = st.text_input("Kullanıcı Kimliği")
        access_key = st.text_input("Erişim Anahtarı", type="password")
        if st.form_submit_button("Sistemi Aktif Et"):
            if user == "admin" and access_key == "123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Hatalı Yetkilendirme!")
    st.stop()

# --- 2. GELİŞMİŞ AR-GE MOTORU (AKS ANALİZİ) ---
def get_point_to_line_dist(p, line):
    """Noktanın doğruya olan dik uzaklığını hesaplar (Paralel hat eleme için)."""
    p1, p2 = np.array(line[0]), np.array(line[1])
    p3 = np.array(p)
    if np.array_equal(p1, p2): return np.linalg.norm(p3-p1)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def analyze_dxf_professional(file_path, layers, scale_factor, min_wall_len, thickness_tolerance):
    """
    Profesyonel Metraj Algoritması:
    Çizimdeki tüm çizgileri (Line/Polyline/Block) tarar ve birbirine yakın paralel 
    hatları tek bir merkezi aksa indirger.
    """
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        raw_data = []
        target_layers = [l.upper().strip() for l in layers.split(",") if l.strip()]

        # Katman ve Obje Taraması
        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        for e in entities:
            if target_layers and not any(t in e.dxf.layer.upper() for t in target_layers):
                continue
            
            # Segmentlere ayırma işlemi
            current_segments = []
            if e.dxftype() == "INSERT": # Bloklar (Kapı kasası, kolon vb.)
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE":
                        current_segments.append(((sub.dxf.start.x, sub.dxf.start.y), (sub.dxf.end.x, sub.dxf.end.y)))
            elif e.dxftype() == "LINE":
                current_segments.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    current_segments.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))

            # Birim ölçeklendirme
            for s in current_segments:
                p1 = (s[0][0]/scale_factor, s[0][1]/scale_factor)
                p2 = (s[1][0]/scale_factor, s[1][1]/scale_factor)
                dist = math.dist(p1, p2)
                if dist >= min_wall_len:
                    raw_data.append({'path': (p1, p2), 'len': dist, 'active': True})

        # --- AKILLI TEKİLLEŞTİRME (DEDUPLICATION) ---
        # Önce en uzun çizgileri işle (Duvarın ana hattını yakala)
        raw_data.sort(key=lambda x: x['len'], reverse=True)
        final_results = []

        for i in range(len(raw_data)):
            if not raw_data[i]['active']: continue
            
            main_line = raw_data[i]
            main_line['active'] = False
            final_results.append(main_line)
            
            # Bu çizgiye çok yakın olan (duvarın diğer yüzü veya sıva hattı) çizgileri ele
            for j in range(i + 1, len(raw_data)):
                if not raw_data[j]['active']: continue
                
                # İkinci çizginin başlangıç noktasının ana çizgiye uzaklığına bak
                d_offset = get_point_to_line_dist(raw_data[j]['path'][0], main_line['path'])
                
                if d_offset < thickness_tolerance:
                    raw_data[j]['active'] = False # Mükerrer hattı iptal et

        return final_results
    except Exception as e:
        st.error(f"DXF Analiz Hatası: {e}")
        return []

# --- 3. KONTROL PANELİ ---
st.sidebar.header("🛠️ Mühendislik Ayarları")
with st.sidebar:
    uploaded_file = st.file_uploader("AutoCAD DXF Dosyası", type=["dxf"])
    unit_mode = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    layer_input = st.text_input("Katman (Layer) Filtresi", "DUVAR, WALL, 0_DUVAR")
    wall_height = st.number_input("Duvar Yüksekliği (m)", value=2.85, format="%.2f")
    
    st.divider()
    st.subheader("🤖 Ar-Ge Filtreleri")
    min_len_filter = st.slider("Minimum Duvar Uzunluğu (m)", 0.0, 1.0, 0.20)
    thickness_filter = st.slider("Aks Birleştirme Hassasiyeti (m)", 0.10, 0.60, 0.35, 
                                 help="Birbirine bu mesafeden yakın paralel çizgileri tek duvar sayar.")

if uploaded_file:
    # Geçici Dosya Yönetimi
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_file.getbuffer())
        temp_path = tmp.name

    scale = 100 if unit_mode == "cm" else (1000 if unit_mode == "mm" else 1)
    
    with st.spinner('Geometrik Analiz Yapılıyor...'):
        results = analyze_dxf_professional(temp_path, layer_input, scale, min_len_filter, thickness_filter)

    if results:
        total_len = sum(r['len'] for r in results)
        total_area = total_len * wall_height

        # SONUÇ ÖZETİ
        st.subheader("📊 Metraj Analiz Raporu")
        c1, c2, c3 = st.columns(3)
        c1.metric("📏 Toplam Net Uzunluk", f"{round(total_len, 2)} m")
        c2.metric("🧱 Toplam Uygulama Alanı", f"{round(total_area, 2)} m²")
        c3.metric("🧩 Tespit Edilen Tekil Aks", len(results))

        # GÖRSEL DOĞRULAMA (CAD ÖNİZLEME)
        
        st.subheader("🖼️ Geometrik Doğrulama Önizlemesi")
        fig, ax = plt.subplots(figsize=(12, 5))
        for r in results:
            p1, p2 = r['path']
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#27ae60", linewidth=2.5)
            # Etiketleme
            ax.text((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, f"{round(r['len'], 2)}m", fontsize=8, alpha=0.7)
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)

        # HAKEDİŞ CETVELİ
        st.subheader("📋 Detaylı Metraj Cetveli")
        df_results = pd.DataFrame([
            {"No": i+1, "Birim": "m", "Uzunluk": round(r['len'], 3), "Yükseklik(m)": wall_height, "Toplam m²": round(r['len']*wall_height, 3)} 
            for i, r in enumerate(results)
        ])
        st.dataframe(df_results, use_container_width=True)

        # EXCEL AKTARIMI
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_results.to_excel(writer, index=False, sheet_name='Metraj_Raporu')
        st.download_button("📥 Excel Raporunu İndir", data=output.getvalue(), file_name="hakedis_metraj_raporu.xlsx")

    else:
        st.error("Kriterlere uygun duvar bulunamadı. Lütfen Layer ismini veya Tolerans ayarlarını kontrol edin.")
    
    os.remove(temp_path)
else:
    st.info("👋 Başlamak için lütfen sol taraftan bir DXF planı yükleyin.")
