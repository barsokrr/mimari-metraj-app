import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math

def get_entity_length(e):
    """Objelerin uzunluğunu koordinat hatası almadan hesaplar."""
    try:
        if e.dxftype() == 'LINE':
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
    except:
        return 0
    return 0

def process_entities(entities, target_layers, plot_list):
    """Belirli katmanlardaki objeleri tarar ve uzunluk döner."""
    length_accumulator = 0
    for e in entities:
        # Katman filtresi (Büyük/küçük harf duyarsız)
        layer = e.dxf.layer.upper()
        if not target_layers or any(t.upper() in layer for t in target_layers):
            length = get_entity_length(e)
            if length > 0:
                length_accumulator += length
                # Görselleştirme verisi
                if e.dxftype() == 'LINE':
                    plot_list.append(([e.dxf.start[0], e.dxf.end[0]], [e.dxf.start[1], e.dxf.end[1]]))
                elif e.dxftype() in ('LWPOLYLINE', 'POLYLINE'):
                    pts = list(e.get_points())
                    plot_list.append(([p[0] for p in pts], [p[1] for p in pts]))
    return length_accumulator

# --- ARAYÜZ YAPILANDIRMASI ---
st.set_page_config(page_title="Pro Metraj AI", layout="wide")
st.title("🏗️ Akıllı Mimari Metraj Analizi")

with st.sidebar:
    st.header("⚙️ Parametreler")
    uploaded = st.file_uploader("DXF Planını Yükle", type=["dxf"])
    birim = st.selectbox("Çizim Birimi", ["cm", "mm", "m"], index=0)
    kat_yuk = st.number_input("Kat Yüksekliği (Net m)", value=3.0)
    katman_input = st.text_input("Duvar Katmanları (Virgülle ayırın)", "DUVAR, WALL, MIM_DUVAR")
    target_layers = [x.strip() for x in katman_input.split(",")] if katman_input else []

if uploaded:
    # Birim katsayısı (m'ye çevrim için)
    katsayi = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.read())
        path = tmp.name

    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        plot_data = []

        # 1. Ana Modelspace Analizi
        toplam_ham_uzunluk = process_entities(msp, target_layers, plot_data)

        # 2. Blok (INSERT) İçindeki Duvarları Analiz Et (58m için kritik adım)
        for insert in msp.query('INSERT'):
            try:
                block = doc.blocks[insert.dxf.name]
                toplam_ham_uzunluk += process_entities(block, target_layers, plot_data)
            except:
                continue

        # GÖRSELLEŞTİRME (Harita Çizimi)
        fig, ax = plt.subplots(figsize=(10, 10))
        for xs, ys in plot_data:
            ax.plot(xs, ys, color="#2c3e50", linewidth=0.7, alpha=0.8)
        
        ax.set_aspect("equal")
        ax.axis("off")
        st.pyplot(fig)
        plt.close(fig)

        # HESAPLAMALAR
        # Mimari planlarda duvarlar çift çizgi (iç-dış) olduğu için toplam/2 yapıyoruz
        aks_uzunlugu_m = (toplam_ham_uzunluk / 2) / katsayi
        toplam_alan_m2 = aks_uzunlugu_m * kat_yuk

        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("📏 Toplam Metraj (L)", f"{round(aks_uzunlugu_m, 2)} m")
        c2.metric("🧱 Duvar Yüzey Alanı", f"{round(toplam_alan_m2, 2)} m²")
        
        # Manuel hesaplama karşılaştırması
        fark = aks_uzunlugu_m - 58.08
        c3.info(f"Hedef: 58.08 m\nSapma: {round(fark, 2)} m")

        if abs(fark) < 2:
            st.success("Sonuç manuel ölçümle %95+ uyumlu!")
        else:
            st.warning("Sapma yüksekse lütfen 'Katman İsimlerini' veya 'Çizim Birimini' kontrol edin.")

    except Exception as e:
        st.error(f"Hata oluştu: {str(e)}")

else:
    st.info("Analize başlamak için sol menüden bir DXF dosyası yükleyin.")
