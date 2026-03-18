import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os

# --- 1. VERİ YÜKLEME (CSV) ---
def load_construction_items():
    # Yüklediğin dosyayı okuyoruz
    try:
        df_items = pd.read_csv("İNŞAAT YAPI İŞLERİ.xlsx - YAP.İŞLER-İNŞ.csv")
        # Sadece anlamlı sütunları alalım (Poz ve İmalat Adı)
        df_items = df_items.dropna(subset=['İMALATIN ADI'])
        return df_items
    except:
        return pd.DataFrame({"İMALATIN ADI": ["Duvar İmalatı", "Sıva İmalatı", "Boya İmalatı"]})

# --- 2. DXF ANALİZ ---
def get_dxf_geometry(dxf_path, scale):
    try:
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        lines = []
        # Tüm görünür çizgileri çekiyoruz (Filtreleme artık kullanıcı seçimine göre görsel yapılacak)
        for e in msp.query('LINE LWPOLYLINE'):
            if e.dxftype() == "LINE":
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            else:
                pts = [(p[0], p[1]) for p in e.get_points()]
            
            for i in range(len(pts)-1):
                ln = math.dist(pts[i], pts[i+1]) / scale
                lines.append({"p1": pts[i], "p2": pts[i+1], "Uzunluk": round(ln, 2)})
        return lines
    except: return []

# --- 3. ARAYÜZ ---
st.set_page_config(layout="wide")
st.title("🏗️ İnşaat İmalat Metraj Paneli")

# İnşaat kalemlerini yükle
items_df = load_construction_items()

st.sidebar.title("🚧 İmalat Seçimi")
# Kullanıcı listeden imalat kalemini seçer
selected_item = st.sidebar.selectbox("Yapılacak İmalatı Seçin:", items_df['İMALATIN ADI'].unique())

dxf_file = st.sidebar.file_uploader("Mimari Planı (DXF) Yükleyin", type=["dxf"])
unit = st.sidebar.selectbox("Çizim Birimi", ["cm", "mm", "m"])
scale = 100 if unit == "cm" else (1000 if unit == "mm" else 1)

if dxf_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(dxf_file.getbuffer())
        tmp_path = tmp.name

    geometry = get_dxf_geometry(tmp_path, scale)
    df_geom = pd.DataFrame(geometry)

    if not df_geom.empty:
        col1, col2 = st.columns([2, 1])

        with col2:
            st.info(f"📍 Seçili Poz: {selected_item}")
            st.subheader("📊 Metraj Sonuçları")
            
            # Toplam hesaplama
            total_m = df_geom["Uzunluk"].sum()
            st.metric(label="Toplam Metraj (L)", value=f"{total_m:.2f} m")
            
            # Veri tablosu
            st.dataframe(df_geom[["Uzunluk"]], use_container_width=True)
            
            st.success("✅ Seçilen kalem için metraj cetveli hazırlandı.")

        with col1:
            st.subheader("🖼️ Plan Üzerinde İmalat Takibi")
            fig, ax = plt.subplots(figsize=(10, 8), facecolor='#0e1117')
            
            # Çizim
            for i, row in df_geom.iterrows():
                # Şimdilik tüm çizgileri bu imalat için varsayıyoruz (Manuel eşleşme geliştirilebilir)
                ax.plot([row['p1'][0], row['p2'][0]], [row['p1'][1], row['p2'][1]], 
                        color="#FFD700", lw=1.5, alpha=0.8) # İmalat rengi (Altın)

            ax.set_aspect("equal")
            ax.axis("off")
            st.pyplot(fig)
    
    os.remove(tmp_path)
