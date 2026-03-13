import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pdfplumber  # PDF analizi için eklendi
from fpdf import FPDF # Raporlama için eklendi

# --- FONKSİYONLAR ---

def read_dxf_geometry(path, target_layers):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    polygons = []

    # Blokları (INSERT) patlatıp içindekileri okumak için msp.query('INSERT') eklenebilir
    # Ama mevcut yapıyı stabilize edelim
    for e in msp:
        layer_name = e.dxf.layer.upper()
        is_target_layer = any(t.upper() in layer_name for t in target_layers)

        if is_target_layer:
            if e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                if e.dxftype() == "LWPOLYLINE":
                    pts = [(p[0], p[1]) for p in e.get_points()]
                else:
                    pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]

                if len(pts) > 1:
                    if pts[0] != pts[-1]:
                        pts.append(pts[0]) 
                    polygons.append(pts)
            
            elif e.dxftype() == "LINE":
                p1 = e.dxf.start
                p2 = e.dxf.end
                polygons.append([(p1[0], p1[1]), (p2[0], p2[1]), (p1[0], p1[1])])
    return polygons

def read_pdf_geometry(path):
    """PDF içindeki vektörel çizgileri bulmaya çalışır."""
    polygons = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            # PDF içindeki 'line' ve 'rect' objelerini poligon gibi al
            for line in page.lines:
                polygons.append([(line["x0"], line["y0"]), (line["x1"], line["y1"]), (line["x0"], line["y0"])])
    return polygons

def polygon_perimeter(poly):
    L = 0
    for i in range(len(poly) - 1):
        L += math.dist(poly[i], poly[i+1])
    return L

def create_pdf_report(uzunluk, alan, kat_yuk):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Mimari Metraj Raporu", ln=True, align='C')
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt=f"Toplam Duvar Uzunlugu: {uzunluk} m", ln=True)
    pdf.cell(200, 10, txt=f"Kat Yuksekligi: {kat_yuk} m", ln=True)
    pdf.cell(200, 10, txt=f"Toplam Duvar Alani: {alan} m2", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- ARAYÜZ ---
st.set_page_config(page_title="Pro Metraj v5", layout="wide")
st.title("🏗️ Akıllı Duvar Metrajı (DXF & PDF Destekli)")

with st.sidebar:
    st.header("⚙️ Analiz Ayarları")
    uploaded = st.file_uploader("Plan Yükle (DXF veya PDF)", type=["dxf", "pdf"])
    kat_yuksekligi = st.number_input("Kat Yüksekliği (m)", value=3.0)
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    katman_input = st.text_input("Duvar Katmanları (Sadece DXF için)", "DUVAR, WALL, MIM_DUVAR")
    target_layers = [x.strip() for x in katman_input.split(",")]

if uploaded:
    birim_bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
    polygons = []
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    if uploaded.name.endswith(".dxf"):
        polygons = read_dxf_geometry(path, target_layers)
    elif uploaded.name.endswith(".pdf"):
        st.warning("⚠️ PDF'den metraj alma deneyseldir ve ölçek hatası içerebilir.")
        polygons = read_pdf_geometry(path)

    if not polygons:
        st.error("Seçilen dosyada uygun obje bulunamadı.")
    else:
        fig, ax = plt.subplots(figsize=(12, 10))
        total_raw_perimeter = 0

        for poly in polygons:
            xs = [p[0] for p in poly]
            ys = [p[1] for p in poly]
            ax.fill(xs, ys, color="#3498db", alpha=0.6, edgecolor="black", linewidth=0.8)
            total_raw_perimeter += polygon_perimeter(poly)

        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)
        plt.close(fig)

        # Hesaplamalar
        duvar_m = (total_raw_perimeter / 2) / birim_bolen
        alan = duvar_m * kat_yuksekligi

        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("📏 Toplam Duvar Uzunluğu", f"{round(duvar_m, 2)} m")
        col2.metric("🧱 Toplam Duvar Alanı", f"{round(alan, 2)} m²")
        
        # PDF RAPOR İNDİRME
        report_data = create_pdf_report(round(duvar_m, 2), round(alan, 2), kat_yuksekligi)
        st.download_button(
            label="📄 Metraj Raporunu İndir (PDF)",
            data=report_data,
            file_name="metraj_raporu.pdf",
            mime="application/pdf"
        )
        st.success("Analiz tamamlandı.")
