import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
import numpy as np
from io import BytesIO
from roboflow import Roboflow
from PIL import Image

# --- 1. KURUMSAL TEMA VE GELİŞMİŞ CSS ---
st.set_page_config(page_title="Metraj Pro | AI Destekli Analiz", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    
    /* Metrik Kutuları Görünürlük Ayarı */
    [data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 2px solid #e0e0e0;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    [data-testid="stMetricValue"] > div, [data-testid="stMetricLabel"] > div {
        color: #000000 !important;
        font-weight: bold !important;
    }

    h1, h2, h3, p, span { color: #ffffff !important; }
    .stDataFrame { background-color: #1a1c23; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. SESSION STATE & LOGIN ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    _, col_mid, _ = st.columns([1, 1.2, 1])
    with col_mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.title("🏢 Metraj Pro Giriş")
        with st.form("login_form"):
            user_input = st.text_input("Kullanıcı", value="admin")
            pass_input = st.text_input("Şifre", type="password", value="123")
            if st.form_submit_button("Sistemi Başlat"):
                if user_input == "admin" and pass_input == "123":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Giriş bilgileri hatalı!")
    st.stop()

# --- 3. ANALİZ FONKSİYONLARI ---

def get_refined_segments(path, scale, layers):
    """DXF dosyasından duvar segmentlerini ID ile birlikte çeker."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        walls = []
        targets = [l.upper().strip() for l in layers.split(",") if l.strip()]
        counter = 1

        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if targets and not any(t in e.dxf.layer.upper() for t in targets): continue
            
            pts = []
            if e.dxftype() == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            else:
                pts = [(p[0], p[1]) for p in e.get_points()]

            for i in range(len(pts)-1):
                p1, p2 = (pts[i][0]/scale, pts[i][1]/scale), (pts[i+1][0]/scale, pts[i+1][1]/scale)
                ln = math.dist(p1, p2)
                if ln > 0.20:
                    walls.append({
                        "ID": f"D-{counter:03d}",
                        "p1": p1, "p2": p2, "Metraj (m)": round(ln, 2),
                        "Layer": e.dxf.layer
                    })
                    counter += 1
        return walls
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}")
        return []

def run_roboflow_ai(image_path):
    """Roboflow API üzerinden görsel analiz yapar."""
    # NOT: Kendi API Key ve Proje bilgilerinizi buraya girin
    try:
        rf = Roboflow(api_key="SENIN_API_KEYIN")
        project = rf.workspace().project("duvar-tespit-modeli")
        model = project.version(1).model
        prediction = model.predict(image_path, confidence=40).json()
        return prediction['predictions']
    except:
        return []

# --- 4. YAN PANEL (SIDEBAR) ---
st.sidebar.title("📊 Metraj Kontrol Paneli")
with st.sidebar:
    st.info(f"👤 Kullanıcı: Barış Öker")
    dxf_up = st.file_uploader("DXF Dosyası Seçin", type=["dxf"])
    layer_sel = st.text_input("Katman (Layer)", "DUVAR")
    unit_sel = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    h_sel = st.number_input("Yükseklik (m)", value=2.85, step=0.01)
    
    st.divider()
    if st.button("Güvenli Çıkış"):
        st.session_state.logged_in = False
        st.rerun()

# --- 5. ANA EKRAN VE ANALİZ ---
if dxf_up:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_up.getbuffer())
        t_path = tmp.name

    sc = 100 if unit_sel == "cm" else (1000 if unit_sel == "mm" else 1)
    walls = get_refined_segments(t_path, sc, layer_sel)

    if walls:
        df = pd.DataFrame(walls)
        total_l = df["Metraj (m)"].sum()

        st.subheader("🚀 Analiz Raporu")
        c1, c2, c3 = st.columns(3)
        c1.metric("Net Uzunluk", f"{total_l:.2f} m")
        c2.metric("Toplam Alan", f"{(total_l * h_sel):.2f} m²")
        c3.metric("Aks Sayısı", len(walls))

        st.divider()
        
        # --- İNTERAKTİF ÇİZİM VE TABLO ---
        col_list, col_map = st.columns([1, 1.5])
        
        with col_list:
            st.subheader("📋 Metraj Detay Listesi")
            selected_indices = st.dataframe(
                df[["ID", "Metraj (m)", "Layer"]],
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row"
            )

        selected_wall_id = None
        if len(selected_indices.selection.rows) > 0:
            selected_wall_id = df.iloc[selected_indices.selection.rows[0]]["ID"]

        with col_map:
            st.subheader("🖼️ Analiz Önizleme")
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            
            # Tüm Duvarları Çiz
            for _, w in df.iterrows():
                is_selected = selected_wall_id and w["ID"] == selected_wall_id
                ax.plot([w["p1"][0]*sc, w["p2"][0]*sc], [w["p1"][1]*sc, w["p2"][1]*sc], 
                        color="#FFFF00" if is_selected else "#00d2ff", 
                        lw=4 if is_selected else 1.5,
                        zorder=2 if is_selected else 1)

            ax.set_aspect("equal")
            ax.axis("off")
            st.pyplot(fig)

        # --- AI ANALİZ BUTONU ---
        if st.button("🤖 Roboflow AI Analizini Çalıştır"):
            st.warning("AI Entegrasyonu için API Key gereklidir. Girdiğinizde bu bölüm aktifleşecektir.")
            # Burada yukarıdaki run_roboflow_ai fonksiyonu çağrılır.

        # --- EXCEL ÇIKTISI ---
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df[["ID", "Metraj (m)", "Layer"]].to_excel(writer, index=False)
        
        st.download_button(
            label="📊 Excel Raporu İndir",
            data=output.getvalue(),
            file_name=f"Metraj_{dxf_up.name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    os.remove(t_path)
