def get_dxf_geometry(path, target_layers=None):
    try:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        geometries = []
        
        # Filtreleme
        if target_layers:
            target_layers = [t.upper().strip() for t in target_layers]

        # Hassas Sorgu
        entities = msp.query('LINE LWPOLYLINE POLYLINE')
        
        for e in entities:
            if target_layers and e.dxf.layer.upper() not in target_layers:
                continue
            
            pts = []
            if e.dxftype() == "LINE":
                # Başlangıç ve bitiş koordinatlarını net al
                pts = [(e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)]
            else:
                # Polylineler için sadece köşe noktalarını (vertex) al
                pts = [(p[0], p[1]) for p in e.get_points()]
            
            # Eğer nokta varsa listeye ekle
            if len(pts) > 1:
                geometries.append(pts)
        return geometries
    except Exception as e:
        return []

# --- HESAPLAMA MANTIĞI GÜNCELLEMESİ ---
if wall_analysis:
    toplam_ham_uzunluk = 0
    for g in wall_analysis:
        segment_uzunlugu = 0
        for i in range(len(g) - 1):
            # Öklid mesafesini daha temiz hesapla
            d = math.sqrt((g[i+1][0] - g[i][0])**2 + (g[i+1][1] - g[i][1])**2)
            segment_uzunlugu += d
        toplam_ham_uzunluk += segment_uzunlugu

    # BİRİM DÜZELTMESİ (Örn: Çizim cm ise 250 birim / 100 = 2.5m)
    bolen = 100 if birim == "cm" else (1000 if birim == "mm" else 1)
    
    # ÇİFT ÇİZGİ KONTROLÜ (Kritik nokta!)
    # Planda 1 duvar var ama 2 çizgi (iç-dış yüz) varsa 2'ye böl. 
    # Ama tek aks çizgisi ise bölme!
    net_uzunluk = (toplam_ham_uzunluk / bolen) / 2  # Mimari planlar genelde çift çizgidir
