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

# --- 1. SAYFA VE TEMA AYARLARI ---
st.set_page_config(page_title="Metraj Pro AI + DXF", layout="wide", page_icon="🏢")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    [data-testid="stMetric"] { background-color: #1f2937 !important; border-radius: 12px; padding: 15px; border: 1px solid #374151; }
    [data-testid="stMetricValue"] > div { color: #00d2ff !important; }
    h1, h2, h3, p, span { color: #ffffff !important; }
    .stDataFrame { background-color: #1f2937; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. YARDIMCI FONKSİYONLAR ---

def get_all_layers(path):
    """DXF içindeki tüm katman isimlerini çeker."""
    try:
        doc = ezdxf.readfile(path)
        return sorted([layer.dxf.name for layer in doc.layers])
    except:
        return ["0"]

def run_roboflow_ai(image_bytes):
    """Görseli Roboflow AI modeline gönderir."""
    try:
        rf = Roboflow(api_key="my238ZSyFyxbwEVQHISP") 
        project = rf.workspace("bars-workspace").project("mimari_duvar_tespiti-2")
        model = project.version(8).model
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            tmp.write(image_bytes.getvalue())
            prediction = model.predict(tmp.name, confidence=40).json()
        os.remove(tmp.name)
        return prediction.get('predictions', [])
    except Exception as e:
        st.error(f"AI Hatası: {e}")
        return []

def get_dxf_data(path, target_layer, scale):
    """Seçilen katmandaki çizgileri DXF'den çeker."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        walls = []
        # Çizgi ve Polylineları sorgula
        for e in msp.query('LINE LWPOLYLINE POLYLINE'):
            if e.dxf.layer == target_layer:
                # Koordinatları al
                if e.dxftype() == "LINE":
                    pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
                else:
                    pts = [(p[0], p[1]) for p in e.get_points()]
                
                for i in range(len(pts)-1):
                    length = math.dist(pts[i], pts[i+1]) / scale
                    if length > 0.05:
                        walls.append({
                            "p1": pts[i], "p2": pts[i+1],
                            "Uzunluk": round(length, 2),
                            "Layer": e.dxf.layer
                        })
        return walls
    except:
        return []

# --- 3. SIDEBAR (KONTROL PANELİ) ---
st.sidebar.title("⚙️ Mühendislik Paneli")
dxf_file = st.sidebar.file_uploader("DXF Dosyasını Yükleyin", type=["dxf"])

if dxf_file:
    # Geçici dosya oluştur
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp_dxf:
        tmp_dxf.write(dxf_file.getbuffer())
        temp_path = tmp_dxf.name

    # Katman Seçimi (Dinamik Buton Mantığı)
    all_layers = get_all_layers(temp_path)
    st.sidebar.subheader("📍 Katman Seçimi")
    selected_layer = st.sidebar.selectbox("Analiz Edilecek Katman:", all_layers, index=all_layers.index("DUVAR") if "DUVAR" in all_layers else 0)
    
    unit_opt = st.sidebar.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    scale_val = 100 if unit_opt == "cm" else (1000 if unit_opt == "mm" else 1)
    wall_height = st.sidebar.number_input("Duvar Yüksekliği (m)", value=2.80)

    # Verileri Çek
    data = get_dxf_data(temp_path, selected_layer, scale_val)
    df = pd.DataFrame(data)

    # --- 4. ANA EKRAN VE GÖRSELLEŞTİRME ---
    st.title("🏢 Akıllı Metraj Analiz Sistemi")
    
    if not df.empty:
        # Metrikler
        m1, m2, m3 = st.columns(3)
        total_l = df["Uzunluk"].sum()
        m1.metric("Toplam Uzunluk", f"{total_l:.2f} m")
        m2.metric("Duvar Alanı (Net)", f"{total_l * wall_height:.2f} m²")
        m3.metric("Segment Sayısı", len(df))

        col_plan, col_list = st.columns([2, 1])

        with col_list:
            st.subheader("📋 Metraj Detayı")
            selected_idx = st.radio("Planda Görmek İçin Seçin:", df.index)
            st.dataframe(df[["Uzunluk", "Layer"]], use_container_width=True)

        with col_plan:
            st.subheader("🖼️ İnteraktif Plan Analizi")
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            
            # Tüm çizgileri çiz
            for i, row in df.iterrows():
                is_selected = (i == selected_idx)
                color = "#32CD32" if is_selected else "#4b5563" # Seçili Yeşil, Diğerleri Gri
                width = 5 if is_selected else 1.2
                ax.plot([row['p1'][0], row['p2'][0]], [row['p1'][1], row['p2'][1]], 
                        color=color, lw=width, zorder=2 if is_selected else 1)
                
                if is_selected:
                    ax.text(row['p1'][0], row['p1'][1], f" {row['Uzunluk']}m", color="white", fontsize=12, fontweight='bold')

            ax.set_aspect("equal")
            ax.axis("off")
            
            # AI Analiz Butonu
            if st.button("🤖 AI İle Alanı Doğrula"):
                img_buf = BytesIO()
                plt.savefig(img_buf, format='png', bbox_inches='tight')
                preds = run_roboflow_ai(img_buf)
                st.toast(f"{len(preds)} adet yapı elemanı AI tarafından doğrulandı!")
            
            st.pyplot(fig)
    else:
        st.warning(f"'{selected_layer}' katmanında çizim bulunamadı. Lütfen başka bir katman seçin.")

else:
    st.info("Başlamak için sol taraftan bir DXF mimari planı yükleyin.")
