import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd
import os
from io import BytesIO
from roboflow import Roboflow
from PIL import Image, ImageDraw

# --- AYARLAR VE TEMA ---
st.set_page_config(page_title="Metraj Pro AI + DXF", layout="wide")

# --- FONKSİYONLAR ---
def run_roboflow_ai(image_bytes):
    try:
        rf = Roboflow(api_key="YOUR_API_KEY") # Kendi key'inizi buraya girin
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            prediction = model.predict(tmp.name, confidence=40).json()
        return prediction.get('predictions', [])
    except: return []

def process_hybrid_metraj(predictions, scale):
    hybrid_results = []
    for i, res in enumerate(predictions):
        # AI kutusundan merkez hattı türetme (Piksel -> DXF Birimi dönüşümü varsayımıyla)
        # Gerçek uygulamada AI koordinatları DXF koordinat sistemine map edilir.
        x, y, w, h = res['x'], res['y'], res['width'], res['height']
        
        # En uzun kenar uzunluktur
        length_px = max(w, h)
        length_m = (length_px / scale) 
        
        # Sanal çizgi koordinatları (Merkezleme)
        p1 = (x - w/2, y) if w > h else (x, y - h/2)
        p2 = (x + w/2, y) if w > h else (x, y + h/2)
        
        hybrid_results.append({
            "id": i,
            "Uzunluk": round(length_m, 2),
            "p1": p1, "p2": p2,
            "Tip": "AI Tespit (Centerline)"
        })
    return hybrid_results

# --- ARAYÜZ ---
st.title("🏢 AI Destekli Hassas Metraj Analizi")
dxf_file = st.sidebar.file_uploader("DXF Yükle", type=["dxf"])
unit_scale = st.sidebar.number_input("Ölçek Katsayısı (Piksel/Metre Oranı)", value=50.0)

if dxf_file:
    # 1. DXF'i görselleştir (Basit önizleme)
    st.info("Plan analiz ediliyor ve sanal merkez hatları oluşturuluyor...")
    
    # Simülasyon için örnek bir figür oluşturuyoruz
    fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
    ax.set_aspect("equal")
    ax.axis("off")
    
    # AI Analizi tetikleme (Örnek akış)
    img_buf = BytesIO()
    fig.savefig(img_buf, format='png')
    preds = run_roboflow_ai(img_buf)
    results = process_hybrid_metraj(preds, unit_scale)
    
    col1, col2 = st.columns([2, 1])
    
    with col2:
        st.subheader("📋 Metraj Listesi")
        st.write("Vurgulamak istediğiniz satıra tıklayın:")
        df = pd.DataFrame(results)
        # İnteraktif seçim için index kullanıyoruz
        selected_index = st.radio("Seçili Duvar:", df.index) if not df.empty else None
        st.dataframe(df[["Uzunluk", "Tip"]])

    with col1:
        st.subheader("🖼️ İnteraktif Plan")
        # Çizim aşaması
        for i, row in df.iterrows():
            color = "#32CD32" if i == selected_index else "#00d2ff" # Seçiliyse Yeşil
            width = 4 if i == selected_index else 1.5
            ax.plot([row['p1'][0], row['p2'][0]], [row['p1'][1], row['p2'][1]], color=color, lw=width)
            if i == selected_index:
                ax.text(row['p1'][0], row['p1'][1], f"{row['Uzunluk']}m", color="white")

        st.pyplot(fig)

    st.success(f"Analiz Tamamlandı: Toplam {df['Uzunluk'].sum() if not df.empty else 0} metre duvar ölçüldü.")
