import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math

def get_length(e):
    """Koordinat hatasını çözen güvenli uzunluk hesaplayıcı."""
    try:
        if e.dxftype() == 'LINE':
            # Yeni ezdxf versiyonlarında start/end birer tuple'dır
            p1 = e.dxf.start
            p2 = e.dxf.end
            return math.dist((p1[0], p1[1]), (p2[0], p2[1]))
        
        elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
            points = list(e.get_points())
            L = 0
            for i in range(len(points) - 1):
                p1, p2 = points[i], points[i+1]
                L += math.dist((p1[0], p1[1]), (p2[0], p2[1]))
            if e.is_closed:
                p1, p2 = points[-1], points[0]
                L += math.dist((p1[0], p1[1]), (p2[0], p2[1]))
            return L
    except Exception:
        return 0
    return 0

def process_entities(entities, target_layers, plot_list):
    """Objeleri filtreleyip uzunluklarını toplar."""
    sub_total = 0
    for e in entities:
        layer = e.dxf.layer.upper()
        # Katman filtresi boşsa hepsini al, doluysa sadece hedefi al
        if not target_layers or any(t.upper() in layer for t in target_layers):
            length = get_length(e)
            if length > 0:
                sub_total += length
                # Çizim datası hazırla
                if e.dxftype() == 'LINE':
                    plot_list.append(([e.dxf.start[0], e.dxf.end[0]], [e.dxf.start[1], e.dxf.end[1]]))
                elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    pts = list(e.get_points())
                    plot_list.append(([p[0] for p in pts], [p[1] for p in pts]))
    return sub_total

# --- UI KISMI ---
st.set_page_config(page_title="Hassas Metraj v3", layout="wide")
st.title("🏗️ Akıllı Mimari Metraj Sistemi")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("DXF Dosyası", type=["dxf"])
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=3.0)
    katman_input = st.text_input("Duvar Katmanları (Virgülle ayır)", "DUVAR, WALL, MIM_DUVAR")
    target_layers = [x.strip() for x in katman_input.split(",")] if katman_input else []

if uploaded:
    # Birim dönüştürücü
    bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        
        plot_data = []
        # 1. Ana plandaki çizgiler
        total_raw_len = process_entities(msp, target_layers, plot_data)
        
        # 2. Blokların (Block) içindeki çizgileri patlat ve oku
        for insert in msp.query('INSERT'):
            try:
                block = doc.blocks[insert.dxf.name]
                total_raw_len += process_entities(block, target_layers, plot_data)
            except:
                continue

        # GÖRSELLEŞTİRME
        fig, ax = plt.subplots(figsize=(10, 8))
        for xs, ys in plot_data:
            ax.plot(xs, ys, color="#e74c3c", linewidth=0.8) # Kırmızı çizgiler
        
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)

        # HESAPLAMA (Çift çizgi prensibi: Toplam / 2)
        final_uzunluk = (total_raw_len / 2) / bolen
        final_alan = final_uzunluk * kat_yuk

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("📏 Hesaplanan Uzunluk", f"{round(final_uzunluk, 2)} m")
        c2.metric("🧱 Duvar Alanı", f"{round(final_alan, 2)} m²")
        c3.info(f"Hedef: 58.08 m\nSapma: {round(final_uzunluk - 58.08, 2)} m")

    except Exception as e:
        st.error(f"Dosya işlenirken hata oluştu: {e}")
