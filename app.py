import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math

def read_dxf_geometry(path):
    doc = ezdxf.readfile(path)
    msp = doc.modelspace()
    polygons = []
    lines = []

    for e in msp:
        # LWPOLYLINE modern AutoCAD formatıdır
        if e.dxftype() == "LWPOLYLINE":
            pts = [(p[0], p[1]) for p in e.get_points()]
            if len(pts) > 2:
                # Poligon kapalı mı kontrol et, değilse ilk noktayı sona ekle
                if not e.is_closed:
                    pts.append(pts[0])
                polygons.append(pts)

        # Eski tip POLYLINE
        elif e.dxftype() == "POLYLINE":
            pts = [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
            if len(pts) > 2:
                if not e.is_closed:
                    pts.append(pts[0])
                polygons.append(pts)
                
    return polygons

def polygon_perimeter(poly):
    L = 0
    # i'den i+1'e mesafe (zaten kapalı poligon yaptığımız için tam tur döner)
    for i in range(len(poly) - 1):
        x1, y1 = poly[i]
        x2, y2 = poly[i+1]
        L += math.dist((x1, y1), (x2, y2))
    return L

# --- ARAYÜZ ---
st.set_page_config(page_title="Pro Metraj", layout="wide")
st.title("🏗️ Gelişmiş Mimari Duvar Metrajı")

with st.sidebar:
    st.header("⚙️ Ayarlar")
    uploaded = st.file_uploader("DXF Dosyası Seç", type=["dxf"])
    kat_yuksekligi = st.number_input("Kat Yüksekliği (m)", value=3.0, step=0.1)
    
    # Birim seçimi hatayı önler
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    birim_bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    polygons = read_dxf_geometry(path)

    # GÖRSELLEŞTİRME
    fig, ax = plt.subplots(figsize=(10, 8))
    total_raw_perimeter = 0

    for poly in polygons:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        
        # Duvarları sarı/turuncu arası bir renkle doldur
        ax.fill(xs, ys, color="#FFD700", alpha=0.6, edgecolor="black", linewidth=0.5)
        total_raw_perimeter += polygon_perimeter(poly)

    ax.set_aspect("equal")
    ax.axis("off")
    st.pyplot(fig)
    plt.close(fig) # Bellek temizliği

    # HESAPLAMALAR
    # ÖNEMLİ: Kapalı poligonun çevresi, duvarın hem iç hem dış yüzünü kapsar.
    # Gerçek aks uzunluğu için çevre / 2 yapılması standarttır.
    gercek_uzunluk_birim = total_raw_perimeter / 2
    duvar_m = gercek_uzunluk_birim / birim_bolen
    alan = duvar_m * kat_yuksekligi

    # SONUÇLAR
    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("📏 Toplam Uzunluk", f"{round(duvar_m, 2)} m")
    c2.metric("🧱 Toplam Duvar Alanı", f"{round(alan, 2)} m²")
    c3.metric("📂 Poligon Sayısı", len(polygons))
    
    st.info("💡 Not: Poligon yöntemi, duvarların kapalı alan (hatch/polyline) olarak çizildiği planlarda en doğru sonucu verir.")
else:
    st.warning("Lütfen analiz için bir DXF dosyası yükleyin.")
