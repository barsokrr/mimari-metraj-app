import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# --- 1. KURUMSAL TASARIM VE YAPILANDIRMA ---
st.set_page_config(page_title="SaaS Metraj Pro | Otonom", layout="wide", page_icon="🏗️")

# Özel CSS: st.center yerine profesyonel ortalama ve stil
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { border: 1px solid #d1d8e0; padding: 20px; border-radius: 12px; background: white; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .auth-container { max-width: 400px; margin: 0 auto; padding-top: 100px; }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. GİRİŞ EKRANI (Düzeltilmiş Ortalamalı Yapı) ---
if not st.session_state.logged_in:
    cols = st.columns([1, 2, 1]) # Ekranı 3'e bölerek ortadaki sütunu kullanıyoruz
    with cols[1]:
        st.title("🏗️ SaaS Metraj Pro")
        st.subheader("Kurumsal Erişim Paneli")
        with st.form("login_form"):
            user = st.text_input("Kullanıcı Adı")
            pw = st.text_input("Şifre", type="password")
            submit = st.form_submit_button("Sisteme Giriş Yap")
            if submit:
                if user == "admin" and pw == "123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Giriş bilgileri hatalı!")
    st.stop()

# --- 3. PROFESYONEL GEOMETRİ ANALİZ MOTORU ---
def get_distance_point_to_line(p, line):
    p1, p2 = np.array(line[0]), np.array(line[1])
    p3 = np.array(p)
    if np.array_equal(p1, p2): return np.linalg.norm(p3-p1)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def run_metraj_engine(file_path, scale_val, layers):
    """
    Otonom Ar-Ge Motoru: Çift çizgileri ayıklar, 
    parçalı çizgileri birleştirir ve net metrajı hesaplar.
    """
    # Sabit Mühendislik Parametreleri (Kullanıcıdan gizlendi)
    MIN_LEN = 0.20 # 20cm altı detayları eler
    GAP_TOL = 0.35 # 35cm altı paralel çizgileri tek aks yapar

    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        segments = []
        target_layers = [l.upper().strip() for l in layers.split(",") if l.strip()]

        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        for e in entities:
            if target_layers and not any(t in e.dxf.layer.upper() for t in target_layers):
                continue
            
            temp_segs = []
            if e.dxftype() == "INSERT":
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE":
                        temp_segs.append(((sub.dxf.start.x, sub.dxf.start.y), (sub.dxf.end.x, sub.dxf.end.y)))
            elif e.dxftype() == "LINE":
                temp_segs.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    temp_segs.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))

            for s in temp_segs:
                p1, p2 = (s[0][0]/scale_val, s[0][1]/scale_val), (s[1][0]/scale_val, s[1][1]/scale_val)
                length = math.dist(p1, p2)
                if length >= MIN_LEN:
                    segments.append({'path': (p1, p2), 'len': length, 'active': True})

        # Tekilleştirme Algoritması (Deduplication)
        segments.sort(key=lambda x: x['len'], reverse=True)
        final_walls = []

        for i in range(len(segments)):
            if not segments[i]['active']: continue
            curr = segments[i]
            curr['active'] = False
            final_walls.append(curr)

            for j in range(i + 1, len(segments)):
                if not segments[j]['active']: continue
                # Paralellik ve Mesafe Kontrolü
                dist = get_distance_point_to_line(segments[j]['path'][0], curr['path'])
                if dist < GAP_TOL:
                    segments[j]['active'] = False
        
        return final_walls
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return []

# --- 4. ANA ARAYÜZ ---
st.sidebar.title("🏗️ Metraj Kontrol Merkezi")
with st.sidebar:
    st.markdown("### Dosya Yükleme")
    file = st.file_uploader("DXF Formatında Plan", type=["dxf"])
    unit = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    layer = st.text_input("Duvar Katmanı (Layer)", "DUVAR")
    height = st.number_input("Kat Yüksekliği (m)", value=2.85)
    st.divider()
    if st.button("Oturumu Kapat"):
        st.session_state.logged_in = False
        st.rerun()

if file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(file.getbuffer())
        temp_path = tmp.name

    scale = 100 if unit == "cm" else (1000 if unit == "mm" else 1)
    
    with st.spinner('Otonom metraj motoru çalışıyor...'):
        results = run_metraj_engine(temp_path, scale, layer)

    if results:
        total_l = sum(r['len'] for r in results)
        total_a = total_l * height

        # METRİKLER
        st.success("✅ Analiz Tamamlandı")
        col1, col2, col3 = st.columns(3)
        col1.metric("📏 Net Uzunluk", f"{round(total_l, 2)} m")
        col2.metric("🧱 Toplam Alan", f"{round(total_a, 2)} m²")
        col3.metric("🧩 Aks Sayısı", len(results))

        # GÖRSELLEŞTİRME
        st.subheader("🖼️ Analiz Edilen Duvar Aksları")
        
        fig, ax = plt.subplots(figsize=(10, 5))
        for r in results:
            p1, p2 = r['path']
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#0984e3", lw=2)
            ax.text((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, f"{round(r['len'],2)}m", fontsize=7)
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)

        # CETVEL VE EXCEL
        st.subheader("📋 Metraj Cetveli")
        df = pd.DataFrame([
            {"Sıra": i+1, "Uzunluk (m)": round(r['len'], 3), "Alan (m²)": round(r['len']*height, 2)} 
            for i, r in enumerate(results)
        ])
        st.dataframe(df, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Metraj')
        st.download_button("📥 Excel Cetvelini İndir", data=output.getvalue(), file_name="metraj_raporu.xlsx")

    else:
        st.warning("Belirtilen katmanda uygun geometri bulunamadı.")
    
    os.remove(temp_path)
else:
    st.info("💡 Analiz için lütfen bir DXF dosyası yükleyin.")
