import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import pandas as pd
import os
from io import BytesIO
from roboflow import Roboflow
from PIL import Image

# --- 1. SAYFA AYARLARI ---
st.set_page_config(page_title="Metraj Pro AI + DXF", layout="wide", page_icon="🏢")

# --- 2. FONKSİYONLAR ---

def run_roboflow_ai(image_bytes):
    try:
        # NOT: API Key'inizi buraya girin
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            tmp_path = tmp.name
        
        prediction = model.predict(tmp_path, confidence=40).json()
        os.remove(tmp_path)
        return prediction.get('predictions', [])
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

def process_hybrid_metraj(predictions, scale):
    hybrid_results = []
    for i, res in enumerate(predictions):
        x, y, w, h = res['x'], res['y'], res['width'], res['height']
        
        # Centerline Mantığı: En uzun kenar uzunluktur
        length_px = max(w, h)
        length_m = length_px / scale
        
        # Sanal Çizgi Koordinatları (Görselleştirme için)
        if w > h: # Yatay duvar
            p1, p2 = (x - w/2, y), (x + w/2, y)
        else: # Dikey duvar
            p1, p2 = (x, y - h/2), (x, y + h/2)
            
        hybrid_results.append({
            "ID": i,
            "Uzunluk": round(length_m, 2),
            "p1": p1, "p2": p2,
            "Tip": "AI Duvar Aksı"
        })
    return hybrid_results

# --- 3. ARAYÜZ (SIDEBAR) ---
st.sidebar.title("⚙️ Ayarlar")
dxf_file = st.sidebar.file_uploader("DXF Planını Yükleyin", type=["dxf"])
unit_scale = st.sidebar.number_input("Ölçek (Piksel/Metre Oranı)", value=50.0, help="Plandaki 1 metrenin kaç piksele denk geldiğini ayarlar.")

# --- 4. ANA PANEL ---
st.title("🏢 Akıllı Metraj ve Plan Analizi")

if dxf_file:
    # Boş bir figür hazırlıyoruz (Plan Görseli İçin)
    fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
    ax.set_aspect("equal")
    ax.axis("off")

    # Geçici DXF görselleştirme (Simülasyon)
    img_buf = BytesIO()
    fig.savefig(img_buf, format='png', bbox_inches='tight')
    
    # AI Analizini Başlat
    with st.spinner("AI Duvarları Tespit Ediyor..."):
        preds = run_roboflow_ai(img_buf)
        results = process_hybrid_metraj(preds, unit_scale)
        df = pd.DataFrame(results)

    col_left, col_right = st.columns([2, 1])

    with col_right:
        st.subheader("📋 Metraj Listesi")
        if not df.empty:
            selected_index = st.radio("Vurgulanacak Segmenti Seçin:", df.index)
            st.dataframe(df[["Uzunluk", "Tip"]], use_container_width=True)
            st.metric("Toplam Uzunluk", f"{df['Uzunluk'].sum():.2f} m")
        else:
            st.warning("Henüz duvar tespit edilemedi.")
            selected_index = None

    with col_left:
        st.subheader("🖼️ İnteraktif Plan")
        if not df.empty:
            for i, row in df.iterrows():
                is_sel = (i == selected_index)
                color = "#32CD32" if is_sel else "#00d2ff" # Seçiliyse Yeşil
                width = 6 if is_sel else 2
                
                ax.plot([row['p1'][0], row['p2'][0]], [row['p1'][1], row['p2'][1]], 
                        color=color, lw=width, solid_capstyle='round')
                
                if is_sel:
                    ax.text(row['p1'][0], row['p1'][1], f" {row['Uzunluk']}m", 
                            color="white", fontsize=14, fontweight='bold')
        
        st.pyplot(fig)
else:
    st.info("Lütfen soldaki menüden bir DXF dosyası yükleyerek analizi başlatın.")
