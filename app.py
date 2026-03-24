import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- PROFIL ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

st.set_page_config(page_title="Barış Öker - AI Metraj", layout="wide")

# --- 1. ROBOFLOW ANALİZİ ---
def get_ai_predictions(image_bytes):
    # BURAYI KENDİ BİLGİLERİNLE DOLDUR
    rf = Roboflow(api_key="SENIN_API_KEYIN")
    project = rf.workspace("workspace-adın").project("proje-adın")
    model = project.version(1).model # Versiyon numaranı kontrol et
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        tmp.write(image_bytes.getvalue())
        prediction = model.predict(tmp.name, confidence=40).json()
    os.remove(tmp.name)
    return prediction.get('predictions', [])

# --- 2. DXF VE AI ÇAKIŞTIRMA MOTORU ---
def calculate_ai_guided_metraj(msp, predictions, img_width, img_height, dxf_bounds, h, div):
    total_wall_m2 = 0
    door_count = 0
    win_count = 0
    
    # DXF sınırlarını al (Koordinat eşleme için)
    min_x, min_y, max_x, max_y = dxf_bounds
    dxf_w = max_x - min_x
    dxf_h = max_y - min_y

    for p in predictions:
        # AI'dan gelen box koordinatlarını DXF koordinatına çevir
        # Not: AI koordinatları genelde merkez (x,y) ve w,h olarak gelir
        p_x = min_x + (p['x'] / img_width) * dxf_w
        p_y = min_y + (1 - (p['y'] / img_height)) * dxf_h # Y ekseni genelde terstir
        p_w_dxf = (p['width'] / img_width) * dxf_w
        p_h_dxf = (p['height'] / img_height) * dxf_h

        if p['class'] == 'duvar':
            # Bu bölgedeki çizgileri DXF'den sorgula
            lines = msp.query(f'LINE LWPOLYLINE[x > {p_x - p_w_dxf/2} and x < {p_x + p_w_dxf/2}]')
            segment_len = 0
            for e in lines:
                if e.dxftype() == "LINE":
                    segment_len += math.dist(e.dxf.start, e.dxf.end)
                else:
                    pts = list(e.get_points())
                    segment_len += sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
            
            total_wall_m2 += ((segment_len / 2) / div) * h
            
        elif p['class'] == 'kapi':
            door_count += 1
        elif p['class'] == 'pencere':
            win_count += 1
            
    return total_wall_m2, door_count, win_count

# --- 3. ARAYÜZ VE AKIŞ ---
if st.session_state.logged_in or True: # Test için True, deployda kaldır
    with st.sidebar:
        st.write(f"**Kullanıcı:** Barış Öker")
        uploaded = st.file_uploader("DXF Yükle", type=["dxf"])
        kat_h = st.number_input("Kat Yüksekliği", 2.85)
        birim = st.selectbox("Birim", ["cm", "mm", "m"])
        div = {"cm": 100, "mm": 1000, "m": 1}[birim]

    if uploaded:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
            tmp.write(uploaded.getbuffer())
            doc = ezdxf.readfile(tmp.name)
            msp = doc.modelspace()
            
            # DXF Sınırlarını Bul
            extents = ezdxf.get_extents(msp)
            dxf_bounds = (extents.min.x, extents.min.y, extents.max.x, extents.max.y)

            # Görselleştir ve AI'ya gönder
            fig, ax = plt.subplots(figsize=(8, 8))
            for e in msp.query('LINE LWPOLYLINE'):
                pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
                xs, ys = zip(*[(p[0], p[1]) for p in pts])
                ax.plot(xs, ys, color="black", lw=0.5)
            ax.set_aspect("equal"); ax.axis("off")
            
            img_buf = BytesIO()
            fig.savefig(img_buf, format='png', dpi=100)
            
            if st.button("🚀 AI ve DXF Analizini Başlat"):
                with st.spinner("Yapay zeka duvarları tespit ediyor ve ölçüyor..."):
                    preds = get_ai_predictions(img_buf)
                    w_m2, d_c, w_c = calculate_ai_guided_metraj(msp, preds, 800, 800, dxf_bounds, kat_h, div)
                    
                    st.success("Analiz Tamamlandı!")
                    col1, col2, col3 = st.columns(3)
                    col1.metric("Duvar Alanı", f"{w_m2:.2f} m²")
                    col2.metric("Kapı Adedi", d_c)
                    col3.metric("Pencere Adedi", w_c)
            
            st.pyplot(fig)
