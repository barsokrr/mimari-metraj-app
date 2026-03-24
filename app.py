import streamlit as st
import ezdxf
from ezdxf.bbox import Extents # Yeni sürümde bbox yönetimi buradan yapılır
import matplotlib.pyplot as plt
import math
import tempfile
import os
from roboflow import Roboflow
from io import BytesIO

# ... (Roboflow ve Giriş kısımları aynı) ...

if uploaded:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getbuffer())
        doc = ezdxf.readfile(tmp.name)
        msp = doc.modelspace()
        
        # --- HATA DÜZELTME: EXTENTS HESAPLAMA ---
        # ezdxf.get_extents(msp) yerine güncel bbox kullanımı:
        try:
            extents = Extents(msp)
            min_x, min_y, _ = extents.bbox[0] # Sol alt
            max_x, max_y, _ = extents.bbox[1] # Sağ üst
            dxf_bounds = (min_x, min_y, max_x, max_y)
        except Exception as e:
            st.error(f"Sınır hesaplama hatası: {e}. Lütfen DXF dosyasını AutoCAD'de 'Zoom Extents' yapıp kaydedin.")
            dxf_bounds = (0, 0, 100, 100) # Yedek değer

        # --- GÖRSELLEŞTİRME ---
        fig, ax = plt.subplots(figsize=(8, 8), facecolor='#0e1117')
        for e in msp.query('LINE LWPOLYLINE'):
            # Çizgileri AI'nın okuyabileceği netlikte çizdiriyoruz
            pts = [e.dxf.start, e.dxf.end] if e.dxftype() == "LINE" else list(e.get_points())
            xs, ys = zip(*[(p[0], p[1]) for p in pts])
            ax.plot(xs, ys, color="white", lw=1.0) # Siyah arka planda beyaz çizgiler AI için daha iyidir
        
        ax.set_aspect("equal")
        ax.axis("off")
        
        # Resmi belleğe al
        img_buf = BytesIO()
        fig.savefig(img_buf, format='png', dpi=150) # DPI artırıldı, AI daha net görsün
        
        if st.button("🚀 AI Analizini Başlat"):
            # ... AI fonksiyonunu çağır ve sonuçları yazdır ...
            # (Önceki mesajdaki calculate_ai_guided_metraj fonksiyonunu kullanabilirsin)
