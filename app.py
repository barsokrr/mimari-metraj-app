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

# Roboflow İstemcisi
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key=ROBO_API_KEY
)

# --- FONKSİYONLAR ---

def read_dxf_geometry(path, target_layers):
    """DXF dosyasından blokları patlatarak ve koordinat hatasız geometri okur."""
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        polygons = []

        # Blok içindeki objeleri de okumak için patlatma işlemi
        entities = list(msp.query('LINE LWPOLYLINE POLYLINE'))
        for insert in msp.query('INSERT'):
            try:
                entities.extend(insert.explode())
            except:
                continue

        for e in entities:
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
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}")
        return []

def run_roboflow_ai(file_path):
    """Roboflow API kullanarak plandaki nesneleri tespit eder."""
    try:
        result = CLIENT.infer(file_path, model_id=MODEL_ID)
        return result.get('predictions', [])
    except Exception as e:
        st.warning(f"AI Analizi şu an yapılamıyor: {e}")
        return []

def calculate_total_length(geometries):
    total = 0
    for geo in geometries:
        for i in range(len(geo) - 1):
            total += math.dist(geo[i], geo[i+1])
    return total

# --- ARAYÜZ (STREAMLIT) ---
st.set_page_config(page_title="Elifim Metraj Pro", layout="wide", page_icon="🏗️")
st.title("🏗️ DUVAR METRAJ PANELİ")

with st.sidebar:
    st.header("⚙️ Analiz Ayarları")
    uploaded = st.file_uploader("Dosya Seç (DXF, PDF veya Görsel)", type=["dxf", "pdf", "jpg", "png", "jpeg"])
    
    st.divider()
    kat_yuk = st.number_input("Kat Yüksekliği (m)", value=3.0, step=0.1)
    birim = st.selectbox("Çizim Birimi (DXF)", ["cm", "mm", "m"], index=0)
    katmanlar = st.text_input("DXF Katman Filtresi", "DUVAR, WALL, MIM_DUVAR")
    
    st.divider()
    st.info("💡 Roboflow AI modülü aktiftir. Görsel analizlerde otomatik nesne tespiti yapar.")

if uploaded:
    # Dosyayı geçici olarak kaydet
    suffix = f".{uploaded.name.split('.')[-1]}"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getbuffer())
        file_path = tmp.name

    is_dxf = uploaded.name.lower().endswith(".dxf")
    is_img = uploaded.name.lower().endswith((".jpg", ".png", ".jpeg"))

    geos = []
    ai_preds = []
    final_uzunluk = 0

    # --- İŞLEME MANTIĞI ---
    if is_dxf:
        target_layers = [x.strip() for x in katmanlar.split(",")] if katmanlar else []
        geos = read_dxf_geometry(file_path, target_layers)
        raw_len = calculate_total_length(geos)
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        # Mimari çift çizgi mantığı (Aks uzunluğu tahmini için /2)
        final_uzunluk = (raw_len / 2) / bolen
    
    if is_img:
        st.info("Yapay Zeka nesne tespiti yapılıyor...")
        ai_preds = run_roboflow_ai(file_path)

    # --- GÖRSELLEŞTİRME VE SONUÇLAR ---
    if geos or ai_preds:
        c1, c2 = st.columns([2, 1])

        with c1:
            st.subheader("🔍 Plan Analiz Görünümü")
            
            # Matplotlib temizleme ve figür oluşturma
            plt.clf() 
            fig, ax = plt.subplots(figsize=(12, 10))
            
            if geos:
                # DXF Çizgilerini Çiz
                for g in geos:
                    xs, ys = zip(*g)
                    ax.plot(xs, ys, color="#e67e22", linewidth=0.8)
                
                # Görüntü bozulmasını engelleyen kritik ayarlar
                ax.set_aspect("equal", adjustable="datalim")
            
            # Eğer resim yüklenmişse ve AI sonuçları varsa onları da çiz
            if is_img:
                img = cv2.imread(file_path)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                ax.imshow(img)
            
            ax.axis("off")
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig) # Belleği boşalt

        with c2:
            st.subheader("📊 Metraj Sonuçları")
            if is_dxf:
                st.metric("📏 Toplam Uzunluk", f"{round(final_uzunluk, 2)} m")
                st.metric("🧱 Duvar Alanı", f"{round(final_uzunluk * kat_yuk, 2)} m²")
                
                # Hedef karşılaştırma (58.08 m referansı)
                sapma = final_uzunluk - 58.08
                color = "normal" if abs(sapma) < 1 else "inverse"
                st.metric("🎯 Referans Sapması", f"{round(sapma, 2)} m", delta_color=color)
            
            if ai_preds:
                st.divider()
                st.write("🤖 **AI Tespit Edilen Nesneler:**")
                for p in ai_preds:
                    st.write(f"✅ {p['class']} - Güven: %{round(p['confidence']*100, 1)}")

    else:
        st.error("Analiz edilecek veri bulunamadı. Lütfen katman ayarlarını kontrol edin.")

else:
    st.info("Lütfen sol panelden bir DXF veya Plan Görseli yükleyin.")
