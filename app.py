import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# --- 1. KURUMSAL TASARIM ---
st.set_page_config(page_title="SaaS Metraj Pro | Final", layout="wide", page_icon="🏗️")

st.markdown("""
    <style>
    .main { background-color: #fcfcfc; }
    .stMetric { border: 2px solid #3498db; padding: 20px; border-radius: 15px; background: white; }
    div[data-testid="stSidebar"] { background-color: #f0f2f6; }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GİRİŞ KONTROLÜ ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ SaaS Metraj Pro Giriş")
    with st.center():
        with st.form("login"):
            u = st.text_input("Kullanıcı")
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap"):
                if u == "admin" and p == "123":
                    st.session_state.logged_in = True
                    st.rerun()
    st.stop()

# --- 3. AKILLI GEOMETRİ MOTORU (OTONOM SÜRÜM) ---
def get_dist_p2l(p, line):
    p1, p2 = np.array(line[0]), np.array(line[1])
    p3 = np.array(p)
    if np.array_equal(p1, p2): return np.linalg.norm(p3-p1)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def process_dxf_autonomously(file_path, unit_scale, layer_filter):
    """
    Kullanıcıya sormadan arka planda çalışan otonom metraj motoru.
    """
    # Sabit Mühendislik Parametreleri (Arka Planda)
    MIN_WALL_LEN = 0.25      # 25cm altı çizgileri 'çöp' kabul eder
    THICKNESS_TOL = 0.35     # 35cm altı paralel çizgileri tek aksa birleştirir
    
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        raw_segs = []
        
        # Filtreleme
        targets = [l.upper().strip() for l in layer_filter.split(",") if l.strip()]
        
        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        for e in entities:
            if targets and not any(t in e.dxf.layer.upper() for t in targets):
                continue
                
            segs = []
            if e.dxftype() == "INSERT":
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE":
                        segs.append(((sub.dxf.start.x, sub.dxf.start.y), (sub.dxf.end.x, sub.dxf.end.y)))
            elif e.dxftype() == "LINE":
                segs.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    segs.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))

            for s in segs:
                p1 = (s[0][0]/unit_scale, s[0][1]/unit_scale)
                p2 = (s[1][0]/unit_scale, s[1][1]/unit_scale)
                ln = math.dist(p1, p2)
                if ln >= MIN_WALL_LEN:
                    raw_segs.append({'path': (p1, p2), 'len': ln, 'active': True})

        # Tekilleştirme Algoritması
        raw_segs.sort(key=lambda x: x['len'], reverse=True)
        final = []

        for i in range(len(raw_segs)):
            if not raw_segs[i]['active']: continue
            
            base = raw_segs[i]
            base['active'] = False
            final.append(base)
            
            for j in range(i + 1, len(raw_segs)):
                if not raw_segs[j]['active']: continue
                
                # Paralellik ve mesafe kontrolü
                d = get_dist_p2l(raw_segs[j]['path'][0], base['path'])
                if d < THICKNESS_TOL:
                    raw_segs[j]['active'] = False
                    
        return final
    except:
        return []

# --- 4. ARAYÜZ ---
st.sidebar.title("🏢 SaaS Metraj Pro")
with st.sidebar:
    st.info("Otonom analiz modu aktif. Algoritma çizim hatalarını otomatik ayıklar.")
    f = st.file_uploader("DXF Dosyasını Buraya Bırakın", type=["dxf"])
    u_type = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    l_name = st.text_input("Katman (Layer) İsmi", "DUVAR")
    h = st.number_input("Kat Yüksekliği (m)", value=2.85)
    st.divider()
    if st.button("Sistemi Sıfırla"):
        st.rerun()

if f:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(f.getbuffer())
        path = tmp.name

    sc = 100 if u_type == "cm" else (1000 if u_type == "mm" else 1)
    
    # OTONOM ANALİZ
    res = process_dxf_autonomously(path, sc, l_name)

    if res:
        total_l = sum(r['len'] for r in res)
        total_a = total_l * h

        st.success("✅ Analiz Başarıyla Tamamlandı")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("📐 Toplam Uzunluk", f"{round(total_l, 2)} m")
        m2.metric("🧱 Toplam Alan", f"{round(total_a, 2)} m²")
        m3.metric("🧩 Tekil Duvar Sayısı", len(res))

        # GÖRSEL DOĞRULAMA
        
        st.subheader("🖼️ Geometrik Analiz Önizlemesi")
        fig, ax = plt.subplots(figsize=(12, 6))
        for r in res:
            p1, p2 = r['path']
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#3498db", lw=2.5)
            ax.text((p1[0]+p2[0])/2, (p1[1]+p2[1])/2, f"{round(r['len'],2)}m", fontsize=8)
        ax.set_aspect("equal"); ax.axis("off")
        st.pyplot(fig)

        # RAPORLAMA
        st.subheader("📋 Detaylı Metraj Listesi")
        df = pd.DataFrame([
            {"Sıra": i+1, "Uzunluk (m)": round(r['len'], 3), "Yükseklik (m)": h, "Alan (m²)": round(r['len']*h, 2)} 
            for i, r in enumerate(res)
        ])
        st.dataframe(df, use_container_width=True)

        # EXCEL
        out = BytesIO()
        with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
            df.to_excel(wr, index=False, sheet_name='Metraj')
        st.download_button("📥 Excel Raporu Al", data=out.getvalue(), file_name="metraj_final.xlsx")

    else:
        st.warning("Seçilen layer ismine sahip veri bulunamadı.")
    
    os.remove(path)
