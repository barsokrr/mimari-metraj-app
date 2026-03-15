import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import tempfile
import math
import pandas as pd

# --- 2. GELİŞMİŞ VE TEMİZLEYİCİ DXF OKUMA ---
def get_dxf_geometry(path, target_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        
        # Filtreleme: Boşlukları ve büyük/küçük harfi önemseme
        target_layers = [t.upper().strip() for t in target_layers] if target_layers else None
        
        # Sadece LINE ve POLYLINE değil, Blokları (INSERT) da tarayalım
        entities = msp.query('LINE LWPOLYLINE POLYLINE INSERT')
        
        for e in entities:
            # Katman Kontrolü
            if target_layers and e.dxf.layer.upper() not in target_layers:
                continue
                
            pts = []
            if e.dxftype() == "INSERT": # Blokların içini patlat
                for sub in e.virtual_entities():
                    if sub.dxftype() in ("LINE", "LWPOLYLINE", "POLYLINE"):
                        pts = [(p[0], p[1]) for p in sub.get_points()] if hasattr(sub, 'get_points') else [(sub.dxf.start[0], sub.dxf.start[1]), (sub.dxf.end[0], sub.dxf.end[1])]
            elif e.dxftype() in ("LWPOLYLINE", "POLYLINE"):
                pts = [(p[0], p[1]) for p in e.get_points()]
            elif e.dxftype() == "LINE":
                pts = [(e.dxf.start[0], e.dxf.start[1]), (e.dxf.end[0], e.dxf.end[1])]
            
            # --- HATA ÖNLEME: ÇOK KISA ÇİZGİLERİ ELE (Örn: 0.1 birimden küçükler) ---
            if len(pts) > 1:
                dist = sum(math.dist(pts[i], pts[i+1]) for i in range(len(pts)-1))
                if dist > 0.05: # 5 cm altındaki çizgileri "çöp veri" kabul et
                    geometries.append(pts)
                    
        return geometries
    except Exception as e:
        st.error(f"DXF Okuma Hatası: {e}")
        return []

# --- 3. ANA ANALİZ (HESAPLAMA DÜZELTMESİ) ---
# ... (Üst kısımlar aynı kalacak) ...

if uploaded:
    # ... (Dosya yükleme kısmı) ...
    wall_analysis = get_dxf_geometry(file_path, target_list)

    if wall_analysis:
        # Toplam ham uzunluk
        raw_len = sum(math.dist(g[i], g[i+1]) for g in wall_analysis for i in range(len(g)-1))
        
        # Ölçekleme
        bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
        
        # KRİTİK DÜZELTME: 
        # Çizimin mimari (çift çizgi) mi yoksa statik/aks (tek çizgi) mi olduğunu kullanıcıya soralım veya
        # Varsayılan olarak bölme işlemini kontrollü yapalım.
        net_uzunluk = raw_len / bolen 
        
        # Eğer plan çift çizgiyse bu checkbox'ı manuel ekleyebilirsin:
        cift_cizgi = st.sidebar.checkbox("Çizim Çift Çizgi (Duvar Kalınlığı Var)", value=True)
        if cift_cizgi:
            net_uzunluk = net_uzunluk / 2

        st.success(f"🔍 Toplam {len(wall_analysis)} çizgi segmenti bulundu.")
