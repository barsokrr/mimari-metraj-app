import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# --- 1. KURUMSAL YAPILANDIRMA VE ARAYÜZ ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide", page_icon="🏢")

# Okunabilirlik için CSS Güncellemesi (Beyaz kartlar ve siyah metinler)
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    /* Metrik kartlarının içindeki metinleri siyah yapıyoruz */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"] {
        color: #1e272e !important;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        padding: 15px;
        border-radius: 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.05);
    }
    .stButton>button { width: 100%; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. GÜVENLİ GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    col_l, col_m, col_r = st.columns([1, 1.5, 1])
    with col_m:
        st.title("🏢 Kurumsal Metraj Girişi")
        with st.form("auth"):
            u = st.text_input("Kullanıcı")
            p = st.text_input("Erişim Anahtarı", type="password")
            if st.form_submit_button("Sistemi Başlat"):
                if u == "admin" and p == "123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Giriş Başarısız!")
    st.stop()

# --- 3. OTONOM GEOMETRİ MOTORU ---
def get_p2l_dist(p, line):
    p1, p2 = np.array(line[0]), np.array(line[1])
    p3 = np.array(p)
    if np.array_equal(p1, p2): return np.linalg.norm(p3-p1)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def run_smart_engine(path, scale, layers):
    # Mühendislik Sabitleri (Arka planda otonom çalışır)
    MIN_L = 0.20  # 20cm altı çizgiler elenir
    GAP_TOL = 0.35 # 35cm altı paralel çizgiler tek aksa düşürülür

    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        segments = []
        targets = [l.upper().strip() for l in layers.split(",") if l.strip()]

        for e in msp.query('LINE LWPOLYLINE POLYLINE INSERT'):
            if targets and not any(t in e.dxf.layer.upper() for t in targets):
                continue
            
            temp = []
            if e.dxftype() == "INSERT":
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE":
                        temp.append(((sub.dxf.start.x, sub.dxf.start.y), (sub.dxf.end.x, sub.dxf.end.y)))
            elif e.dxftype() == "LINE":
                temp.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    temp.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))

            for s in temp:
                p1 = (s[0][0]/scale, s[0][1]/scale)
                p2 = (s[1][0]/scale, s[1][1]/scale)
                dist = math.dist(p1, p2)
                if dist >= MIN_L:
                    segments.append({'path': (p1, p2), 'len': dist, 'active': True})

        # Tekilleştirme (Double-Line Ayıklama)
        segments.sort(key=lambda x: x['len'], reverse=True)
        final = []
        for i in range(len(segments)):
            if not segments[i]['active']: continue
            base = segments[i]
            base['active'] = False
            final.append(base)
            for j in range(i + 1, len(segments)):
                if not segments[j]['active']: continue
                if get_p2l_dist(segments[j]['path'][0], base['path']) < GAP_TOL:
                    segments[j]['active'] = False
        return final
    except:
        return []

# --- 4. ANA KONTROL PANELİ ---
st.sidebar.title("🛠️ Veri Girişi")
with st.sidebar:
    f = st.file_uploader("AutoCAD DXF Dosyası", type=["dxf"])
    u_type = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    l_name = st.text_input("Katman (Layer) Filtresi", "DUVAR")
    h = st.number_input("Kat Yüksekliği (m)", value=2.85)
    st.divider()
    if st.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.rerun()

if f:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(f.getbuffer())
        t_path = tmp.name

    scale = 100 if u_type == "cm" else (1000 if u_type == "mm" else 1)
    
    with st.spinner('Analiz yapılıyor...'):
        results = run_smart_engine(t_path, scale, l_name)

    if results:
        t_len = sum(r['len'] for r in results)
        t_area = t_len * h

        st.success("✅ Analiz Tamamlandı")
        
        # BEYAZ KARTLAR (Siyah Metinli)
        m1, m2, m3 = st.columns(3)
        m1.metric("📏 Net Uzunluk", f"{round(t_len, 2)} m")
        m2.metric("🧱 Toplam Alan", f"{round(t_area, 2)} m²")
        m3.metric("🧩 Aks Sayısı", len(results))

        # GÖRSELLEŞTİRME
                st.subheader("🖼️ Geometrik Doğrulama")
        fig, ax = plt.subplots(figsize=(10, 5))
        for r in results:
            p1, p2 = r['path']
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#2e86de", lw=2)
        ax.set_aspect("equal"); ax.axis("off")
        st.pyplot(fig)

        # HAKEDİŞ CETVELİ
        st.subheader("📋 Metraj Cetveli")
        df = pd.DataFrame([{"Sıra": i+1, "Uzunluk (m)": round(r['len'], 3), "Alan (m²)": round(r['len']*h, 2)} for i, r in enumerate(results)])
        st.dataframe(df, use_container_width=True)

        # GÜVENLİ CSV İNDİRME (Excelwriter hatasını önlemek için)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Metraj Cetvelini İndir (CSV/Excel)", data=csv, file_name="metraj_raporu.csv", mime='text/csv')

    else:
        st.warning("Belirtilen katmanda veri bulunamadı.")
    
    os.remove(t_path)
else:
    st.info("👋 Lütfen bir DXF dosyası yükleyerek analizi başlatın.")
