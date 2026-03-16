import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# --- 1. KURUMSAL TEMA VE SAYFA AYARI ---
st.set_page_config(page_title="Metraj Pro | Barış Öker", layout="wide", page_icon="🏢")

# CSS: Metrikleri ve kartları SİYAH yapmak için en agresif stil
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    /* Beyaz kartların içindeki her şeyi (etiket, değer) siyah yapar */
    [data-testid="stMetric"], 
    [data-testid="stMetricValue"] div, 
    [data-testid="stMetricLabel"] div {
        color: #000000 !important;
        font-weight: 800 !important;
    }
    
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #ffffff;
        padding: 15px;
        border-radius: 10px;
    }
    
    /* Diğer başlıklar beyaz kalsın */
    h1, h2, h3, p { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# --- 2. GİRİŞ EKRANI ---
if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 1.2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🏢 Metraj Pro Giriş")
        with st.form("login_form"):
            user_input = st.text_input("Kullanıcı", placeholder="Kullanıcı adınızı girin")
            pass_input = st.text_input("Şifre", type="password", placeholder="••••••••")
            if st.form_submit_button("Sistemi Başlat"):
                if user_input == "admin" and pass_input == "123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Giriş bilgileri hatalı!")
    st.stop()

# --- 3. ANALİZ MOTORU ---
def get_p2l_dist(p, line):
    p1, p2 = np.array(line[0]), np.array(line[1])
    p3 = np.array(p)
    if np.array_equal(p1, p2): return np.linalg.norm(p3-p1)
    return np.abs(np.cross(p2-p1, p1-p3)) / np.linalg.norm(p2-p1)

def autonomous_engine(path, scale, layers):
    MIN_L = 0.25 
    GAP_TOL = 0.35 
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        segments = []
        targets = [l.upper().strip() for l in layers.split(",") if l.strip()]

        for e in msp.query('LINE LWPOLYLINE POLYLINE INSERT'):
            if targets and not any(t in e.dxf.layer.upper() for t in targets): continue
            
            temp_pts = []
            if e.dxftype() == "INSERT":
                for sub in e.virtual_entities():
                    if sub.dxftype() == "LINE":
                        temp_pts.append(((sub.dxf.start.x, sub.dxf.start.y), (sub.dxf.end.x, sub.dxf.end.y)))
            elif e.dxftype() == "LINE":
                temp_pts.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = list(e.get_points())
                for i in range(len(pts)-1):
                    temp_pts.append(((pts[i][0], pts[i][1]), (pts[i+1][0], pts[i+1][1])))

            for s in temp_pts:
                p1, p2 = (s[0][0]/scale, s[0][1]/scale), (s[1][0]/scale, s[1][1]/scale)
                ln = math.dist(p1, p2)
                if ln >= MIN_L:
                    segments.append({'path': (p1, p2), 'len': ln, 'active': True})

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
    except: return []

# --- 4. ANA PANEL ---
st.sidebar.title("📊 Metraj Kontrol Paneli")
with st.sidebar:
    st.success("👤 Kullanıcı Adı: Barış Öker")
    dxf_up = st.file_uploader("DXF Dosyası Seçin", type=["dxf"])
    layer_sel = st.text_input("1. Katman (Layer)", "DUVAR")
    unit_sel = st.selectbox("2. Çizim Birimi", ["cm", "mm", "m"], index=0)
    h_sel = st.number_input("3. Yükseklik (m)", value=2.85, step=0.01)
    
    st.divider()
    if st.button("Güvenli Çıkış"):
        st.session_state.logged_in = False
        st.rerun()

if dxf_up:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_up.getbuffer())
        t_path = tmp.name

    sc = 100 if unit_sel == "cm" else (1000 if unit_sel == "mm" else 1)
    res = autonomous_engine(t_path, sc, layer_sel)

    if res:
        total_l = sum(r['len'] for r in res)
        st.subheader("🚀 Analiz Raporu")
        
        c1, c2, c3 = st.columns(3)
        # Metriklerin yazıları CSS ile siyah yapıldı
        c1.metric("Net Uzunluk", f"{round(total_l, 2)} m")
        c2.metric("Toplam Alan", f"{round(total_l * h_sel, 2)} m²")
        c3.metric("Aks Sayısı", len(res))

        st.subheader("🖼️ Analiz Önizleme (Orijinal vs. Aks)")
        v1, v2 = st.columns(2)
        
        with v1:
            st.markdown("<p style='text-align: center;'>📍 Orijinal Plan (Tam Detaylı)</p>", unsafe_allow_html=True)
            fig1, ax1 = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            doc = ezdxf.readfile(t_path)
            msp = doc.modelspace()
            for e in msp.query('LINE LWPOLYLINE POLYLINE INSERT ARC CIRCLE'):
                try:
                    objs = e.virtual_entities() if e.dxftype() == "INSERT" else [e]
                    for obj in objs:
                        if obj.dxftype() == 'LINE':
                            ax1.plot([obj.dxf.start.x, obj.dxf.end.x], [obj.dxf.start.y, obj.dxf.end.y], color="#454d55", lw=0.5, alpha=0.6)
                        elif obj.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                            pts = list(obj.get_points())
                            if len(pts) > 1:
                                ax1.plot([p[0] for p in pts], [p[1] for p in pts], color="#454d55", lw=0.5, alpha=0.6)
                except: continue
            ax1.set_aspect("equal"); ax1.axis("off")
            st.pyplot(fig1)

        with v2:
            st.markdown("<p style='text-align: center;'>🎯 Analiz Edilen Akslar</p>", unsafe_allow_html=True)
            fig2, ax2 = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            for r in res:
                p1, p2 = r['path']
                ax2.plot([p1[0]*sc, p2[0]*sc], [p1[1]*sc, p2[1]*sc], color="#00d2ff", lw=2)
            ax2.set_aspect("equal"); ax2.axis("off")
            st.pyplot(fig2)
        
        st.subheader("📋 Metraj Detay Listesi")
        df_data = [{"No": i+1, "Uzunluk (m)": round(r['len'], 2), "Alan (m²)": round(r['len']*h_sel, 2)} for i, r in enumerate(res)]
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)

        # Hata veren motor (xlsxwriter) yerine openpyxl kullanarak Excel oluşturma
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        excel_val = output.getvalue()

        st.download_button(
            label="📊 Metraj Listesini Excel Olarak İndir",
            data=excel_val,
            file_name=f"Metraj_Raporu_{dxf_up.name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    os.remove(t_path)
