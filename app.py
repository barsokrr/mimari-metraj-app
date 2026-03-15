import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# --- 1. SİSTEM VE GÖRÜNÜM AYARLARI ---
st.set_page_config(page_title="SaaS Metraj Pro", layout="wide", page_icon="🏢")

# Kartlardaki metinleri siyah yapan ve arayüzü düzelten CSS
st.markdown("""
    <style>
    .main { background-color: #f4f7f6; }
    /* Metrik değerlerini ve etiketlerini siyah yap */
    [data-testid="stMetricValue"], [data-testid="stMetricLabel"], .stMarkdown p {
        color: #000000 !important;
    }
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #dcdde1;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. GİRİŞ PANELİ ---
if not st.session_state.logged_in:
    _, center_col, _ = st.columns([1, 1.5, 1])
    with center_col:
        st.title("🏢 Metraj Pro Giriş")
        with st.form("auth_gate"):
            u = st.text_input("Kullanıcı")
            p = st.text_input("Şifre", type="password")
            if st.form_submit_button("Sistemi Başlat"):
                if u == "admin" and p == "123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı Giriş!")
    st.stop()

# --- 3. GEOMETRİ ANALİZ MOTORU (AR-GE) ---
def get_p2l_dist(p, line):
    p1, p2 = np.array(line[0]), np.array(line[1])
    p3 = np.array(p)
    if np.array_equal(p1, p2): return np.linalg.norm(p3-p1)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def run_analysis(path, scale, layers):
    # Otonom Filtreler
    MIN_LENGTH = 0.20 
    GAP_TOLERANCE = 0.35 

    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        segments = []
        target_layers = [l.upper().strip() for l in layers.split(",") if l.strip()]

        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        for e in entities:
            if target_layers and not any(t in e.dxf.layer.upper() for t in target_layers):
                continue
            
            temp_list = []
            if e.dxftype() == "INSERT":
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE":
                        temp_list.append(((sub.dxf.start.x, sub.dxf.start.y), (sub.dxf.end.x, sub.dxf.end.y)))
            elif e.dxftype() == "LINE":
                temp_list.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    temp_list.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))

            for s in temp_list:
                p1, p2 = (s[0][0]/scale, s[0][1]/scale), (s[1][0]/scale, s[1][1]/scale)
                dist = math.dist(p1, p2)
                if dist >= MIN_LENGTH:
                    segments.append({'path': (p1, p2), 'len': dist, 'active': True})

        segments.sort(key=lambda x: x['len'], reverse=True)
        final_list = []
        for i in range(len(segments)):
            if not segments[i]['active']: continue
            base = segments[i]
            base['active'] = False
            final_list.append(base)
            for j in range(i + 1, len(segments)):
                if not segments[j]['active']: continue
                if get_p2l_dist(segments[j]['path'][0], base['path']) < GAP_TOLERANCE:
                    segments[j]['active'] = False
        return final_list
    except:
        return []

# --- 4. ANA EKRAN ---
st.sidebar.title("🛠️ Ayarlar")
with st.sidebar:
    dxf_file = st.file_uploader("DXF Dosyası", type=["dxf"])
    unit_opt = st.selectbox("Birim", ["cm", "mm", "m"], index=0)
    layer_name = st.text_input("Katman (Layer)", "DUVAR")
    h_val = st.number_input("Yükseklik (m)", value=2.85)
    if st.button("Çıkış"):
        st.session_state.logged_in = False
        st.rerun()

if dxf_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_file.getbuffer())
        t_path = tmp.name

    sc_factor = 100 if unit_opt == "cm" else (1000 if unit_opt == "mm" else 1)
    results = run_analysis(t_path, sc_factor, layer_name)

    if results:
        total_m = sum(r['len'] for r in results)
        total_m2 = total_m * h_val

        st.success("✅ Analiz Başarıyla Tamamlandı")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Net Uzunluk", f"{round(total_m, 2)} m")
        c2.metric("Toplam Alan", f"{round(total_m2, 2)} m²")
        c3.metric("Aks Sayısı", len(results))

        
        st.subheader("🖼️ Geometrik Doğrulama")
        fig, ax = plt.subplots(figsize=(10, 4))
        for r in results:
            p1, p2 = r['path']
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color="#2ecc71", lw=2)
        ax.set_aspect("equal"); ax.axis("off")
        st.pyplot(fig)

        st.subheader("📋 Metraj Listesi")
        df_list = pd.DataFrame([{"Sıra": i+1, "Uzunluk (m)": round(r['len'], 3), "Alan (m²)": round(r['len']*h_val, 2)} for i, r in enumerate(results)])
        st.dataframe(df_list, use_container_width=True)
        
        csv_data = df_list.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Listeyi İndir (CSV)", data=csv_data, file_name="metraj.csv")
    else:
        st.error("Uygun veri bulunamadı.")
    os.remove(t_path)
else:
    st.info("👋 Lütfen dosya yükleyin.")
