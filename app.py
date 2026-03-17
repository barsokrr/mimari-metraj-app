import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO

# Roboflow ve diğer bağımlılıkları güvenli içe aktarma
try:
    from roboflow import Roboflow
except ImportError:
    st.error("Kütüphane hatası: Lütfen terminale 'pip install roboflow python-dotenv openpyxl' yazın.")

# --- 1. KURUMSAL TEMA VE CSS ---
st.set_page_config(page_title="Metraj Pro | AI Destekli Analiz", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 2px solid #e0e0e0;
        padding: 20px;
        border-radius: 15px;
    }
    [data-testid="stMetricValue"] > div, [data-testid="stMetricLabel"] > div {
        color: #000000 !important;
        font-weight: bold !important;
    }
    h1, h2, h3, p, span { color: #ffffff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE & LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 1.2, 1])
    with col_mid:
        st.title("🏢 Metraj Pro Giriş")
        with st.form("login_form"):
            user_input = st.text_input("Kullanıcı", value="admin")
            pass_input = st.text_input("Şifre", type="password", value="123")
            if st.form_submit_button("Sistemi Başlat"):
                if user_input == "admin" and pass_input == "123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı giriş!")
    st.stop()

# --- 3. ANALİZ FONKSİYONLARI ---

def get_refined_segments(path, scale, layers):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        walls = []
        targets = [l.upper().strip() for l in layers.split(",") if l.strip()]
        counter = 1
        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if targets and not any(t in e.dxf.layer.upper() for t in targets): continue
            pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)] if e.dxftype() == "LINE" else [(p[0], p[1]) for p in e.get_points()]
            for i in range(len(pts)-1):
                p1, p2 = (pts[i][0]/scale, pts[i][1]/scale), (pts[i+1][0]/scale, pts[i+1][1]/scale)
                ln = math.dist(p1, p2)
                if ln > 0.10:
                    walls.append({"ID": f"D-{counter:03d}", "p1": p1, "p2": p2, "Metraj (m)": round(ln, 2), "Layer": e.dxf.layer})
                    counter += 1
        return walls
    except Exception as e:
        st.error(f"DXF Hatası: {e}")
        return []

def run_roboflow_ai(image_path):
    try:
        # image_03b0be.jpg dosyasından alınan gerçek Private API Key 
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        # image_041220.jpg dosyasından alınan proje ve versiyon bilgileri 
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        prediction = model.predict(image_path, confidence=50).json()
        return prediction['predictions']
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

# --- 4. ARAYÜZ VE AKIŞ ---
st.sidebar.title("📊 Metraj Kontrol Paneli")
with st.sidebar:
    dxf_up = st.file_uploader("DXF Dosyası Seçin", type=["dxf"])
    layer_sel = st.text_input("Katman (Layer)", "DUVAR")
    unit_sel = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    h_sel = st.number_input("Yükseklik (m)", value=2.85)

if dxf_up:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_up.getbuffer())
        t_path = tmp.name

    sc = 100 if unit_sel == "cm" else (1000 if unit_sel == "mm" else 1)
    walls = get_refined_segments(t_path, sc, layer_sel)

    if walls:
        df = pd.DataFrame(walls)
        st.subheader("🚀 Analiz Raporu")
        c1, c2, c3 = st.columns(3)
        total_l = df["Metraj (m)"].sum()
        c1.metric("Net Uzunluk", f"{total_l:.2f} m")
        c2.metric("Toplam Alan", f"{(total_l * h_sel):.2f} m²")
        c3.metric("Aks Sayısı", len(walls))

        col_list, col_map = st.columns([1, 1.5])
        with col_list:
            st.dataframe(df[["ID", "Metraj (m)"]], use_container_width=True, hide_index=True)

        with col_map:
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            for _, w in df.iterrows():
                ax.plot([w["p1"][0]*sc, w["p2"][0]*sc], [w["p1"][1]*sc, w["p2"][1]*sc], color="#00d2ff", lw=1.5)
            ax.set_aspect("equal")
            ax.axis("off")
            st.pyplot(fig)

        if st.button("🤖 AI Analizini Başlat"):
            temp_img = "ai_temp.png"
            fig.savefig(temp_img, bbox_inches='tight', pad_inches=0)
            results = run_roboflow_ai(temp_img)
            if results:
                st.success(f"{len(results)} bölge tespit edildi.")
                for r in results:
                    st.write(f"📍 {r['class']} (%{r['confidence']*100:.1f})")

        # Excel Çıktısı - openpyxl hatasını önlemek için güvenli blok
        try:
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📊 Excel İndir", output.getvalue(), f"Metraj_{dxf_up.name}.xlsx")
        except Exception as e:
            st.warning("Excel oluşturulamadı, lütfen 'openpyxl' kütüphanesini yükleyin.")

    os.remove(t_path)
