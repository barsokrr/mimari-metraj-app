import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- SAYFA AYARI ---
st.set_page_config(page_title="Barış Öker - AI Metraj Pro", layout="wide")

# --- 1. ROBOFLOW ANALİZ FONKSİYONU ---
def get_ai_predictions(image_bytes):
    try:
        # BURAYI KENDİ BİLGİLERİNLE GÜNCELLE
        rf = Roboflow(api_key="SENIN_API_KEYIN")
        project = rf.workspace("workspace-adın").project("proje-adın")
        model = project.version(1).model 
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            prediction = model.predict(tmp.name, confidence=40).json()
        os.remove(tmp.name)
        return prediction.get('predictions', [])
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

# --- 2. HİBRİT METRAJ MOTORU ---
def calculate_ai_guided_metraj(msp, predictions, img_width, img_height, dxf_bounds, h, div):
    total_wall_m2 = 0
    door_count = 0
    win_count = 0
    min_x, min_y, max_x, max_y = dxf_bounds
    dxf_w = max_x - min_x
    dxf_h = max_y - min_y

    for p in predictions:
        # Koordinat Dönüşümü (Piksel -> DXF)
        p_x = min_x + (p['x'] / img_width) * dxf_w
        p_y = min_y + (1 - (p['y'] / img_height)) * dxf_h
        p_w_dxf = (p['width'] / img_width) * dxf_w
        p_h_dxf = (p['height'] / img_height) * dxf_h

        if p['class'].lower() == 'duvar':
            # AI'nın işaret ettiği bölgedeki çizgileri sorgula
            x_min, x_max = p_x - p_w_dxf/2, p_x + p_w_dxf/2
            lines = msp.query(f'LINE LWPOLYLINE[x > {x_min} and x < {x_max}]')
            segment_len = 0
            for e in lines:
                if e.dxftype() == "LINE":
                    segment_len += math.dist(e.dxf.start, e.dxf.end)
                elif e.dxftype() == "LWPOLYLINE":
                    pts = list(e.get_points())
                    segment_len += sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
            total_wall_m2 += ((segment_len / 2) / div) * h
            
        elif p['class'].lower() == 'kapi':
            door_count += 1
        elif p['class'].lower() == 'pencere':
            win_count += 1
            
    return total_wall_m2, door_count, win_count

# --- 3. ANA ARAYÜZ ---
with st.sidebar:
    st.markdown(f"### Barış Öker\nFi-le Yazılım A.Ş.")
    uploaded = st.file_uploader("DXF Projesi Yükle", type=["dxf"])
    kat_h = st.number_input("Kat Yüksekliği (m)", 2.85)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    div = {"cm": 100, "mm": 1000, "m": 1}[birim]

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        dxf_path = tmp.name
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        
        # --- MANUEL BOUNDING BOX HESABI (ImportError Çözümü) ---
        all_entities = msp.query('LINE LWPOLYLINE')
        if all_entities:
            # Tüm çizgilerin uç noktalarından sınırları kendimiz buluyoruz
            x_coords = []
            y_coords = []
            for e in all_entities:
                if e.dxftype() == "LINE":
                    x_coords.extend([e.dxf.start.x, e.dxf.end.x])
                    y_coords.extend([e.dxf.start.y, e.dxf.end.y])
                else:
                    pts = list(e.get_points())
                    x_coords.extend([p[0] for p in pts])
                    y_coords.extend([p[1] for p in pts])
            dxf_bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
        else:
            dxf_bounds = (0, 0, 100, 100)

        # Çizim
        fig, ax = plt.subplots(figsize=(8, 8), facecolor='#0e1117')
        for e in all_entities:
            pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
            xs, ys = zip(*[(p[0], p[1]) for p in pts])
            ax.plot(xs, ys, color="white", lw=0.7, alpha=0.5)
        ax.set_aspect("equal"); ax.axis("off")
        
        st.pyplot(fig)
        
        if st.button("🚀 Analizi Başlat"):
            img_buf = BytesIO()
            fig.savefig(img_buf, format='png', dpi=100)
            
            with st.spinner("AI ve Vektör Verisi Çakıştırılıyor..."):
                preds = get_ai_predictions(img_buf)
                w_m2, d_c, w_c = calculate_ai_guided_metraj(msp, preds, 800, 800, dxf_bounds, kat_h, div)
                
                st.success("İşlem Başarılı!")
                col1, col2, col3 = st.columns(3)
                col1.metric("Duvar (AI+DXF)", f"{w_m2:.2f} m²")
                col2.metric("Kapı (AI)", d_c)
                col3.metric("Pencere (AI)", w_c)
    
    os.remove(dxf_path)
