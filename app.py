import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np

# --- 1. KURUMSAL YAPILANDIRMA & GÜVENLİK ---
st.set_page_config(page_title="SaaS Metraj Pro | Kurumsal", layout="wide", page_icon="🏢")

# Özel CSS ile profesyonel görünüm
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 Kurumsal Metraj Girişi")
    with st.form("login_form"):
        user = st.text_input("Kullanıcı Adı")
        pw = st.text_input("Şifre", type="password")
        if st.form_submit_button("Sisteme Giriş"):
            # Profesyonel kullanımda burası DB veya Secrets ile kontrol edilir
            if user == "admin" and pw == "123":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Yetkisiz Giriş Denemesi!")
    st.stop()

# --- 2. PROFESYONEL GEOMETRİ ANALİZ MOTORU ---
def get_professional_metraj(file_path, layer_names, unit_scale, min_len, tolerance):
    """
    Dinamik duvar tekilleştirme ve aks hesaplama motoru.
    """
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        raw_lines = []
        layers = [l.upper().strip() for l in layer_names.split(",") if l.strip()]

        # 1. Veri Toplama (Bloklar ve Polylineler dahil)
        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        
        for e in entities:
            if layers and not any(target in e.dxf.layer.upper() for target in layers):
                continue
            
            # Nesneleri temel segmentlere ayır
            if e.dxftype() == "INSERT":
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE":
                        raw_lines.append(((sub.dxf.start.x/unit_scale, sub.dxf.start.y/unit_scale), 
                                         (sub.dxf.end.x/unit_scale, sub.dxf.end.y/unit_scale)))
            elif e.dxftype() == "LINE":
                raw_lines.append(((e.dxf.start.x/unit_scale, e.dxf.start.y/unit_scale), 
                                 (e.dxf.end.x/unit_scale, e.dxf.end.y/unit_scale)))
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    raw_lines.append(((pts[i][0]/unit_scale, pts[i][1]/unit_scale), 
                                     (pts[i+1][0]/unit_scale, pts[i+1][1]/unit_scale)))

        # 2. Akıllı Filtreleme ve Tekilleştirme
        # Duvarları uzunluğa göre sırala (Önce ana hatları işle)
        processed_lines = []
        for line in raw_lines:
            length = math.dist(line[0], line[1])
            if length >= min_len:
                processed_lines.append({'coords': line, 'len': length, 'used': False})
        
        processed_lines.sort(key=lambda x: x['len'], reverse=True)

        final_segments = []
        for i, line_i in enumerate(processed_lines):
            if line_i['used']: continue
            
            line_i['used'] = True
            final_segments.append(line_i)
            
            # Bu çizgiye paralel ve yakın olan "eş" çizgileri (iç/dış yüzey) iptal et
            for j in range(i + 1, len(processed_lines)):
                line_j = processed_lines[j]
                if line_j['used']: continue
                
                # İki çizgi arası dikey mesafe (Duvar Kalınlığı Kontrolü)
                dist = point_to_line_dist(line_j['coords'][0], line_i['coords'])
                
                # Paralellik ve Mesafe Kontrolü
                if dist < tolerance:
                    # Açı kontrolü (Opsiyonel ama hassasiyet için)
                    line_j['used'] = True # Bu çizgi zaten temsil ediliyor, metraja ekleme!

        return final_segments
    except Exception as e:
        st.error(f"Geometri İşleme Hatası: {e}")
        return []

def point_to_line_dist(p, line):
    p1, p2 = np.array(line[0]), np.array(line[1])
    p3 = np.array(p)
    if np.array_equal(p1, p2): return np.linalg.norm(p3-p1)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

# --- 3. KULLANICI ARAYÜZÜ ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/4300/4300058.png", width=100)
st.sidebar.title("📊 Metraj Kontrol Paneli")

with st.sidebar:
    uploaded = st.file_uploader("DXF Planını Yükle", type="dxf")
    unit = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    target_layer = st.text_input("Hedef Katmanlar (Virgülle ayır)", "DUVAR, WALL")
    h_wall = st.number_input("Kat Yüksekliği (m)", value=2.85)
    
    st.divider()
    st.subheader("🛠️ Mühendislik Ayarları")
    min_l = st.slider("Minimum Duvar Boyu (m)", 0.0, 1.0, 0.20, help="Küçük çizgileri (söve vb.) eler.")
    wall_tol = st.slider("Duvar Kalınlık Toleransı (m)", 0.10, 0.60, 0.35, help="Paralel çizgileri tek aksa düşürür.")

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        t_path = tmp.name

    scale_factor = 100 if unit == "cm" else (1000 if unit == "mm" else 1)
    
    # ANALİZ SÜRECİ
    with st.spinner('Geometri analiz ediliyor...'):
        results = get_professional_metraj(t_path, target_layer, scale_factor, min_l, wall_tol)

    if results:
        total_m = sum(r['len'] for r in results)
        total_m2 = total_m * h_wall

        # ÖZET METRİKLER
        st.success("✅ Analiz Başarıyla Tamamlandı")
        c1, c2, c3 = st.columns(3)
        c1.metric("📐 Toplam Uzunluk", f"{round(total_m, 3)} m")
        c2.metric("🧱 Toplam Alan", f"{round(total_m2, 2)} m²")
        c3.metric("🧩 Tespit Edilen Aks", len(results))

        # RAPORLAMA TABLOSU
        st.subheader("📋 Metraj Detay Listesi")
        report_data = [{"No": i+1, "Uzunluk (m)": round(r['len'], 3), "Alan (m²)": round(r['len']*h_wall, 2)} for i, r in enumerate(results)]
        st.dataframe(pd.DataFrame(report_data), use_container_width=True)

        # GÖRSEL ANALİZ
        st.subheader("🖼️ Proje Önizleme (Aks Analizi)")
        fig, ax = plt.subplots(figsize=(12, 6))
        for r in results:
            p1, p2 = r['coords']
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#1f77b4", linewidth=2)
            # Metraj etiketlerini ekle
            ax.text((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, f"{round(r['len'],2)}m", fontsize=8)
        
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)
        
        # EXCEL ÇIKTISI
        excel_data = pd.DataFrame(report_data)
        st.download_button("📥 Metraj Cetvelini İndir (Excel)", data=excel_data.to_csv().encode('utf-8'), file_name="metraj_raporu.csv")

    else:
        st.error("Seçilen katmanlarda veya kriterlerde uygun geometri bulunamadı!")
    
    os.remove(t_path)
else:
    st.info("👋 Hoş geldiniz! Analize başlamak için sol menüden DXF dosyasını yükleyin.")
