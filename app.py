import streamlit as st
import ezdxf
from ezdxf.bbox import Extents
import matplotlib.pyplot as plt
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# --- SAYFA AYARI ---
st.set_page_config(page_title="Barış Öker - AI Metraj", layout="wide")

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

# --- 2. HİBRİT METRAJ HESAPLAMA ---
def calculate_ai_guided_metraj(msp, predictions, img_width, img_height, dxf_bounds, h, div):
    total_wall_m2 = 0
    door_count = 0
    win_count = 0
    min_x, min_y, max_x, max_y = dxf_bounds
    dxf_w = max_x - min_x
    dxf_h = max_y - min_y

    for p in predictions:
        # Koordinat Dönüşümü
        p_x = min_x + (p['x'] / img_width) * dxf_w
        p_y = min_y + (1 - (p['y'] / img_height)) * dxf_h
        p_w_dxf = (p['width'] / img_width) * dxf_w
        p_h_dxf = (p['height'] / img_height) * dxf_h

        if p['class'].lower() == 'duvar':
            # AI'nın bulduğu kutu içindeki çizgileri tara
            lines = msp.query(f'LINE LWPOLYLINE[x > {p_x - p_w_dxf/2} and x < {p_x + p_w_dxf/2}]')
            segment_len = 0
            for e in lines:
                if e.dxftype() == "LINE":
                    segment_len += math.dist(e.dxf.start, e.dxf.end)
                else:
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
        
        # Sınırları hesapla (Extents hatası düzeltildi)
        try:
            ext_obj = Extents(msp)
            b_min, b_max = ext_obj.bbox[0], ext_obj.bbox[1]
            dxf_bounds = (b_min[0], b_min[1], b_max[0], b_max[1])
        except:
            dxf_bounds = (0, 0, 1000, 1000)

        # Çizim ve Görselleştirme
        fig, ax = plt.subplots(figsize=(8, 8), facecolor='#0e1117')
        for e in msp.query('LINE LWPOLYLINE'):
            pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
            xs, ys = zip(*[(p[0], p[1]) for p in pts])
            ax.plot(xs, ys, color="white", lw=0.8, alpha=0.6)
        ax.set_aspect("equal"); ax.axis("off")
        
        st.pyplot(fig)
        
        # Analiz Butonu
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
else:
    st.info("Lütfen sol menüden bir DXF dosyası yükleyerek başlayın.")
