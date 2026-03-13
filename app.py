import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pdfplumber
from fpdf import FPDF

# --- YARDIMCI FONKSİYONLAR ---

def read_dxf_geometry(path, target_layers):
    """DXF dosyasından katman odaklı geometri okur."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        polygons = []

        for e in msp:
            layer_name = e.dxf.layer.upper()
            is_target_layer = any(t.upper() in layer_name for t in target_layers) if target_layers else True

            if is_target_layer:
                if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                    pts = [(p[0], p[1]) for p in e.get_points()]
                    if len(pts) > 1:
                        polygons.append(pts)
                elif e.dxftype() == "LINE":
                    p1, p2 = e.dxf.start, e.dxf.end
                    polygons.append([(p1[0], p1[1]), (p2[0], p2[1])])
        return polygons
    except:
        return []

def read_pdf_geometry(path):
    """PDF içindeki vektörel çizgileri ayıklar."""
    lines = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                # Vektörel çizgileri (lines) ve dikdörtgenleri (rects) al
                for line in page.lines:
                    lines.append([(float(line["x0"]), float(line["y0"])), (float(line["x1"]), float(line["y1"]))])
                for rect in page.rects:
                    lines.append([(float(rect["x0"]), float(rect["y0"])), (float(rect["x1"]), float(rect["y0"]))])
    except:
        pass
    return lines

def calculate_total_length(geometries):
    total = 0
    for geo in geometries:
        for i in range(len(geo) - 1):
            total += math.dist(geo[i], geo[i+1])
    return total

# --- ARAYÜZ ---
st.set_page_config(page_title="Mimari Metraj Pro", layout="wide")
st.title("🏗️ ELİFİM İÇİN DUVAR METRAJI")

with st.sidebar:
    st.header("⚙️ Analiz Ayarları")
    uploaded = st.file_uploader("Dosya Seç (DXF veya PDF)", type=["dxf", "pdf"])
    
    tab_dxf, tab_pdf = st.tabs(["DXF Ayarları", "PDF Ayarları"])
    
    with tab_dxf:
        birim = st.selectbox("DXF Birimi", ["cm", "mm", "m"], index=0)
        katmanlar = st.text_input("Katman Filtresi", "DUVAR, WALL")
        
    with tab_pdf:
        st.info("PDF birimleri standart değildir. Lütfen ölçeği manuel kalibre edin.")
        pdf_skala = st.number_input("PDF Ölçek Çarpanı (Düzeltme)", value=0.01, format="%.4f")

    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=3.0)

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp:
        tmp.write(uploaded.read())
        file_path = tmp.name

    geos = []
    is_pdf = uploaded.name.endswith(".pdf")

    if is_pdf:
        geos = read_pdf_geometry(file_path)
        raw_len = calculate_total_length(geos)
        # PDF'de genellikle her çizgi tekil olduğu için /2 yapmaya gerek olmayabilir 
        # (Çizim tekniğine bağlıdır)
        final_uzunluk = raw_len * pdf_skala 
    else:
        target_layers = [x.strip() for x in katmanlar.split(",")] if katmanlar else []
        geos = read_dxf_geometry(file_path, target_layers)
        raw_len = calculate_total_length(geos)
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        # DXF'de duvarlar genelde çift çizgi olduğu için /2 kuralı uygulanır
        final_uzunluk = (raw_len / 2) / bolen

    if geos:
        # Görselleştirme
        fig, ax = plt.subplots(figsize=(10, 6))
        for g in geos:
            xs, ys = zip(*g)
            ax.plot(xs, ys, color="#e67e22", linewidth=0.5)
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)

        # Sonuçlar
        st.divider()
        c1, c2 = st.columns(2)
        c1.metric("📏 Hesaplanan Uzunluk", f"{round(final_uzunluk, 2)} m")
        c2.metric("🧱 Duvar Alanı", f"{round(final_uzunluk * kat_yuk, 2)} m²")
        
        if is_pdf:
            st.caption("💡 İpucu: Sonuç yanlışsa 'PDF Ölçek Çarpanı' değerini değiştirerek kalibre edin.")
    else:
        st.error("Dosyada işlenebilir vektörel veri bulunamadı.")


