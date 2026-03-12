import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math

def get_entity_length(e):
    """Farklı DXF objelerinin uzunluğunu hesaplar."""
    if e.dxftype() == 'LINE':
        return math.dist(e.dxf.start[:2], e.dxf.end[:2])
    elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
        points = list(e.get_points())
        length = 0
        for i in range(len(points) - 1):
            length += math.dist(points[i][:2], points[i+1][:2])
        if e.is_closed:
            length += math.dist(points[-1][:2], points[0][:2])
        return length
    return 0

def process_entities(entities, target_layers):
    """Objeleri tarar ve uzunluk ile görsel veriyi döner."""
    total_len = 0
    plot_data = []
    
    for e in entities:
        layer = e.dxf.layer.upper()
        # Katman kontrolü (Boş bırakılırsa tüm katmanları alır)
        if not target_layers or any(t.upper() in layer for t in target_layers):
            length = get_entity_length(e)
            if length > 0:
                total_len += length
                # Görselleştirme için koordinatları sakla
                if e.dxftype() == 'LINE':
                    plot_data.append(([e.dxf.start[0], e.dxf.end[0]], [e.dxf.start[1], e.dxf.end[1]]))
                elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    pts = list(e.get_points())
                    plot_data.append(([p[0] for p in pts], [p[1] for p in pts]))
    return total_len, plot_data

# --- ARAYÜZ ---
st.set_page_config(page_title="Hassas Metraj", layout="wide")
st.title("🏗️ Profesyonel Mimari Metraj (Derin Analiz)")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("DXF Dosyası", type=["dxf"])
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=3.0)
    katman_input = st.text_input("Katman Filtresi (Boş bırakırsanız hepsini sayar)", "DUVAR, WALL")
    target_layers = [x.strip() for x in katman_input.split(",")] if katman_input else []

if uploaded:
    birim_bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    
    # 1. Modelspace içindeki ana objeleri tara
    total_raw_len, plot_info = process_entities(msp, target_layers)
    
    # 2. BLOKLARIN İÇİNE GİR (En kritik kısım)
    # Planda 'Insert' olarak duran her şeyin içine bakıyoruz
    for insert in msp.query('INSERT'):
        block = doc.blocks[insert.dxf.name]
        b_len, b_plot = process_entities(block, target_layers)
        total_raw_len += b_len
        # Blok içindeki çizimleri de ekrana ekle (basit gösterim)
        plot_info.extend(b_plot)

    # GÖRSELLEŞTİRME
    fig, ax = plt.subplots(figsize=(12, 10))
    for x_coords, y_coords in plot_info:
        ax.plot(x_coords, y_coords, color="red", linewidth=1.2, alpha=0.8)
    
    ax.set_aspect("equal")
    ax.axis("off")
    st.pyplot(fig)

    # HESAPLAMA (Eğer duvarlar çift çizgiyse /2 yapmalıyız, tek çizgiyse direkt almalıyız)
    # Genelde mimari planlar çift çizgidir.
    duvar_m = (total_raw_len / 2)
