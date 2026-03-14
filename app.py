import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import cv2
import numpy as np
from inference_sdk import InferenceHTTPClient

# --- YAPILANDIRMA ---
ROBO_API_KEY = "my238ZSyFyxbwEVQHISP" 
MODEL_ID = "mimari_duvar_tespiti-2/8" 

CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key=ROBO_API_KEY
)

# --- FONKSİYONLAR ---

def read_dxf_geometry(path, target_layers):
    """DXF'den duvar çizgilerini okur ve blokları patlatır."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        polygons = []

        # Sadece belirli tipleri sorgula
        entities = list(msp.query('LINE LWPOLYLINE POLYLINE'))
        
        # Blokları (kapı, pencere vb. içindeki çizgileri) patlatarak ekle
        for insert in msp.query('INSERT'):
            try:
                entities.extend(insert.explode())
            except:
                continue

        for e in entities:
            layer_name = e.dxf.layer.upper()
            # Katman filtresi boşsa hepsini al, doluysa kontrol et
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
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}")
        return []

def calculate_total_length(geometries):
    """Çizgilerin toplam uzunluğunu hesaplar."""
    total = 0
    for geo in geometries:
        for i in range(len(geo) - 1):
            total += math.dist(geo[i], geo[i+1])
    return total

# --- ARAYÜZ (STREAMLIT) ---
st.set_page_config(page_title="İnşaat Metraj Hesabı", layout="wide", page_icon="🏗️")
st.title("🏗️ DUVAR METRAJ PANELİ")

# Sidebar Ayarları
with st.sidebar:
    st.header("⚙️ Analiz Ayarları")
    uploaded = st.file_uploader("Dosya Seç (DXF veya Görsel)", type=["dxf", "jpg", "png", "jpeg"])
    
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01)
    birim = st.selectbox("Çizim Birimi (DXF)", ["cm", "mm", "m"], index=0)
    katmanlar = st.text_input("DXF Katman Filtresi", "DUVAR, WALL, MIM_DUVAR")

if uploaded:
    # Geçici dosya oluşturma
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded.name.split('.')[-1]}") as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    is_dxf = uploaded.name.lower().endswith(".dxf")
    
    geos = []
    final_uzunluk = 0

    if is_dxf:
        # Katmanları temizle ve listele
        target_layers = [x.strip() for x in katmanlar.split(",")] if katmanlar else []
        geos = read_dxf_geometry(file_path, target_layers)
        
        if geos:
            raw_len = calculate_total_length(geos)
            # Birim dönüştürme
            bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
            # Mimari çift çizgi (iç-dış) düzeltmesi için /2
            final_uzunluk = (raw_len / 2) / bolen

    # Analiz Sonuçlarını Görüntüle
    if geos:
        c1, c2 = st.columns([2, 1])

        with c1:
            st.subheader("🔍 Plan Analiz Görünümü")
            plt.clf()
            fig, ax = plt.subplots(figsize=(12, 10)) # Boyut optimize edildi
            
            all_x, all_y = [], []
            for g in geos:
                xs, ys = zip(*g)
                all_x.extend(xs)
                all_y.extend(ys)
                # Planı çiz (Turuncu tonlarında net görünüm)
                ax.plot(xs, ys, color="#e67e22", linewidth=0.8, alpha=0.8)

            # --- GELİŞMİŞ ODAKLANMA (AUTO-ZOOM) ---
            if all_x and all_y:
                # Koordinatların %1 ve %99'luk dilimlerini alarak 'hayalet' uzak noktaları dışarıda bırakıyoruz
                x_min, x_max = np.percentile(all_x, [1, 99])
                y_min, y_max = np.percentile(all_y, [1, 99])
                
                # Planın etrafına %5'lik bir beyaz boşluk (padding) ekle
                pad_x = (x_max - x_min) * 0.05
                pad_y = (y_max - y_min) * 0.05
                
                ax.set_xlim(x_min - pad_x, x_max + pad_x)
                ax.set_ylim(y_min - pad_y, y_max + pad_y)

            ax.set_aspect("equal", adjustable="box")
            ax.axis("off") # Eksenleri gizle
            
            # Arkaplanı temizle ve Streamlit'e gönder
            fig.patch.set_facecolor('white')
            st.pyplot(fig)
            plt.close(fig)

        with c2:
            st.subheader("📊 Metraj Sonuçları")
            st.metric("📏 Toplam Uzunluk", f"{round(final_uzunluk, 2)} m")
            st.metric("🧱 Duvar Alanı", f"{round(final_uzunluk * kat_yuk, 2)} m²")
            
            # Referans sapma göstergesi (58.08 m referansına göre)
            referans_deger = 58.08
            sapma = final_uzunluk - referans_deger
            st.metric("🎯 Referans Sapması", 
                      f"{round(sapma, 2)} m", 
                      delta=f"{round(sapma, 2)} m", 
                      delta_color="inverse")
            
            st.info(f"ℹ️ Hesaplama {birim} birimi üzerinden yapılmıştır.")

    else:
        st.warning("⚠️ Belirtilen katmanlarda çizim bulunamadı. Lütfen 'DXF Katman Filtresi' alanını kontrol edin veya katman isminin doğru yazıldığından emin olun.")

else:
    # Dosya yüklenmediğinde karşılama ekranı
    st.info("👋 Başlamak için lütfen sol taraftan bir DXF plan dosyası yükleyin.")

