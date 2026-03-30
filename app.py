"""
Mimari Metraj Pro - Gelişmiş İnşaat Metraj Uygulaması
Version: 2.0
Author: AI Assistant
Description: DXF dosyalarından otomatik metraj çıkarma ve analiz uygulaması
"""

import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.collections import PatchCollection
import pandas as pd
import numpy as np
import math
import tempfile
import os
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional, Union
import json

# =============================================================================
# KONFİGÜRASYON VE SABİTLER
# =============================================================================
st.set_page_config(
    page_title="Mimari Metraj Pro",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Stil özelleştirmeleri
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF4B4B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background-color: #262730;
        border-radius: 10px;
        padding: 15px;
        border-left: 4px solid #FF4B4B;
    }
    .success-msg {
        background-color: #0e4b0e;
        color: #4CAF50;
        padding: 10px;
        border-radius: 5px;
    }
    .stDataFrame {
        font-size: 14px;
    }
</style>
""", unsafe_allow_html=True)

# Kalem tanımlamaları - Katman eşleştirme
KALEMLER = {
    'DUVAR': {
        'renk': '#FF4B4B',
        'katmanlar': ['DUVAR', 'WALL', 'WALLS', 'DUVAR', 'WALL-EXTERNAL', 'WALL-INTERNAL'],
        'tip': 'uzunluk',
        'aciklama': 'Taşıyıcı ve bölmeci duvarlar'
    },
    'PENCERE': {
        'renk': '#00BFFF',
        'katmanlar': ['PENCERE', 'WINDOW', 'WINDOWS', 'PEN', 'WIN', 'CAM'],
        'tip': 'alan',
        'aciklama': 'Pencere açıklıkları'
    },
    'KAPI': {
        'renk': '#FF8C00',
        'katmanlar': ['KAPI', 'DOOR', 'DOORS', 'KAP', 'GIRIS', 'KAPI-IC', 'KAPI-DIS'],
        'tip': 'alan',
        'aciklama': 'Kapı açıklıkları'
    },
    'ZEMIN': {
        'renk': '#32CD32',
        'katmanlar': ['ZEMIN', 'FLOOR', 'FLOORS', 'DOSEME', 'SLAB', 'ZEM'],
        'tip': 'alan',
        'aciklama': 'Zemin/döşeme alanları'
    },
    'TAVAN': {
        'renk': '#9370DB',
        'katmanlar': ['TAVAN', 'CEILING', 'TAV', 'TAVAN-KAPLAMA'],
        'tip': 'alan',
        'aciklama': 'Tavan yüzeyleri'
    },
    'MERDİVEN': {
        'renk': '#FFD700',
        'katmanlar': ['MERDİVEN', 'STAIRS', 'STAIR', 'MER', 'KORKULUK'],
        'tip': 'uzunluk',
        'aciklama': 'Merdiven ve korkuluklar'
    }
}

# Birim dönüşüm faktörleri (DXF genellikle mm'dir)
BIRIM_CEVRIM = {
    'mm': 1.0,
    'cm': 0.1,
    'm': 0.001,
    'inch': 0.0393701
}

# =============================================================================
# VERİ YAPILARI
# =============================================================================
@dataclass
class Geometri:
    """Geometri veri sınıfı"""
    tip: str  # 'line', 'polyline', 'arc', 'circle', 'ellipse'
    noktalar: List[Tuple[float, float]]
    kapali: bool = False
    uzunluk: float = 0.0
    alan: float = 0.0
    
@dataclass
class KalemVerisi:
    """Kalem bazlı veri sınıfı"""
    kalem_adi: str
    geometriler: List[Geometri]
    toplam_uzunluk: float
    toplam_alan: float
    renk: str

@dataclass
class MetrajSonuc:
    """Metraj sonuç sınıfı"""
    kalem: str
    poz_no: str
    aciklama: str
    birim: str
    miktar: float
    birim_fiyat: float = 0.0
    toplam_tutar: float = 0.0
    detay: str = ""

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================
def katman_eslestir(layer_name: str) -> Optional[str]:
    """
    DXF katman adını tanımlı kalemlerle eşleştir
    
    Args:
        layer_name: DXF katman adı
        
    Returns:
        Eşleşen kalem adı veya None
    """
    if not layer_name:
        return None
    
    layer_upper = layer_name.upper().strip()
    
    for kalem_adi, kalem_bilgi in KALEMLER.items():
        for katman_pattern in kalem_bilgi['katmanlar']:
            if katman_pattern.upper() in layer_upper or layer_upper in katman_pattern.upper():
                return kalem_adi
    
    return None

def nokta_uzaklik(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """İki nokta arasındaki öklid mesafesi"""
    return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)

def polyline_uzunluk(noktalar: List[Tuple[float, float]], kapali: bool = False) -> float:
    """Polyline uzunluğu hesapla"""
    if len(noktalar) < 2:
        return 0.0
    
    uzunluk = sum(nokta_uzaklik(noktalar[i], noktalar[i+1]) 
                  for i in range(len(noktalar)-1))
    
    if kapali and len(noktalar) > 2:
        uzunluk += nokta_uzaklik(noktalar[-1], noktalar[0])
    
    return uzunluk

def polygon_alani(noktalar: List[Tuple[float, float]]) -> float:
    """
    Shoelace formülü ile polygon alanı hesapla
    
    Args:
        noktalar: (x, y) koordinat listesi
        
    Returns:
        Alan (pozitif değer)
    """
    if len(noktalar) < 3:
        return 0.0
    
    alan = 0.0
    n = len(noktalar)
    
    for i in range(n):
        j = (i + 1) % n
        alan += noktalar[i][0] * noktalar[j][1]
        alan -= noktalar[j][0] * noktalar[i][1]
    
    return abs(alan) / 2.0

def arc_uzunluk(merkez: Tuple[float, float], yaricap: float, 
                baslangic_aci: float, bitis_aci: float) -> float:
    """Yay uzunluğu hesapla (radyan cinsinden açılar)"""
    aci_farki = abs(bitis_aci - baslangic_aci)
    if aci_farki > 2 * math.pi:
        aci_farki = 2 * math.pi
    return yaricap * aci_farki

def circle_alan(yaricap: float) -> float:
    """Daire alanı"""
    return math.pi * yaricap ** 2

def circle_cevre(yaricap: float) -> float:
    """Daire çevresi"""
    return 2 * math.pi * yaricap

# =============================================================================
# DXF PARSING FONKSİYONLARI
# =============================================================================
def entity_oku(entity, scale: float) -> Optional[Geometri]:
    """
    DXF entity'sini oku ve Geometri nesnesine dönüştür
    
    Args:
        entity: ezdxf entity nesnesi
        scale: Ölçek faktörü
        
    Returns:
        Geometri nesnesi veya None
    """
    try:
        dtype = entity.dxftype()
        
        # LINE
        if dtype == "LINE":
            s = entity.dxf.start
            e = entity.dxf.end
            p1 = (s[0] * scale, s[1] * scale)
            p2 = (e[0] * scale, e[1] * scale)
            uzunluk = nokta_uzaklik(p1, p2)
            
            return Geometri(
                tip='line',
                noktalar=[p1, p2],
                kapali=False,
                uzunluk=uzunluk,
                alan=0.0
            )
        
        # LWPOLYLINE
        elif dtype == "LWPOLYLINE":
            pts = list(entity.get_points('xy'))
            noktalar = [(p[0] * scale, p[1] * scale) for p in pts]
            kapali = entity.closed if hasattr(entity, 'closed') else False
            uzunluk = polyline_uzunluk(noktalar, kapali)
            alan = polygon_alani(noktalar) if kapali and len(noktalar) > 2 else 0.0
            
            return Geometri(
                tip='polyline',
                noktalar=noktalar,
                kapali=kapali,
                uzunluk=uzunluk,
                alan=alan
            )
        
        # POLYLINE (eski format)
        elif dtype == "POLYLINE":
            noktalar = []
            for vertex in entity.vertices:
                noktalar.append((vertex.dxf.location[0] * scale, 
                               vertex.dxf.location[1] * scale))
            
            kapali = entity.is_closed if hasattr(entity, 'is_closed') else False
            uzunluk = polyline_uzunluk(noktalar, kapali)
            alan = polygon_alani(noktalar) if kapali and len(noktalar) > 2 else 0.0
            
            return Geometri(
                tip='polyline',
                noktalar=noktalar,
                kapali=kapali,
                uzunluk=uzunluk,
                alan=alan
            )
        
        # ARC (Yay)
        elif dtype == "ARC":
            merkez = (entity.dxf.center[0] * scale, entity.dxf.center[1] * scale)
            yaricap = entity.dxf.radius * scale
            baslangic = math.radians(entity.dxf.start_angle)
            bitis = math.radians(entity.dxf.end_angle)
            uzunluk = arc_uzunluk(merkez, yaricap, baslangic, bitis)
            
            # Yay noktalarını hesapla (görselleştirme için)
            nokta_sayisi = max(10, int(uzunluk / (yaricap * 0.1)))
            noktalar = []
            for i in range(nokta_sayisi + 1):
                t = i / nokta_sayisi
                aci = baslangic + t * (bitis - baslangic)
                x = merkez[0] + yaricap * math.cos(aci)
                y = merkez[1] + yaricap * math.sin(aci)
                noktalar.append((x, y))
            
            return Geometri(
                tip='arc',
                noktalar=noktalar,
                kapali=False,
                uzunluk=uzunluk,
                alan=0.0
            )
        
        # CIRCLE (Daire)
        elif dtype == "CIRCLE":
            merkez = (entity.dxf.center[0] * scale, entity.dxf.center[1] * scale)
            yaricap = entity.dxf.radius * scale
            cevre = circle_cevre(yaricap)
            alan = circle_alan(yaricap)
            
            # Daire noktalarını hesapla
            nokta_sayisi = 36
            noktalar = []
            for i in range(nokta_sayisi):
                aci = 2 * math.pi * i / nokta_sayisi
                x = merkez[0] + yaricap * math.cos(aci)
                y = merkez[1] + yaricap * math.sin(aci)
                noktalar.append((x, y))
            noktalar.append(noktalar[0])  # Kapat
            
            return Geometri(
                tip='circle',
                noktalar=noktalar,
                kapali=True,
                uzunluk=cevre,
                alan=alan
            )
        
        # ELLIPSE
        elif dtype == "ELLIPSE":
            merkez = (entity.dxf.center[0] * scale, entity.dxf.center[1] * scale)
            major_axis = entity.dxf.major_axis
            yaricap = math.sqrt(major_axis[0]**2 + major_axis[1]**2) * scale
            
            # Yaklaşık çevre hesabı (Ramanujan formülü)
            cevre = 2 * math.pi * yaricap
            alan = math.pi * yaricap * yaricap  # Basitleştirilmiş
            
            nokta_sayisi = 36
            noktalar = []
            for i in range(nokta_sayisi):
                aci = 2 * math.pi * i / nokta_sayisi
                x = merkez[0] + yaricap * math.cos(aci)
                y = merkez[1] + yaricap * math.sin(aci)
                noktalar.append((x, y))
            noktalar.append(noktalar[0])
            
            return Geometri(
                tip='ellipse',
                noktalar=noktalar,
                kapali=True,
                uzunluk=cevre,
                alan=alan
            )
        
        # SPLINE (Basitleştirilmiş)
        elif dtype == "SPLINE":
            kontrol_noktalari = list(entity.control_points)
            if len(kontrol_noktalari) >= 2:
                noktalar = [(p[0] * scale, p[1] * scale) for p in kontrol_noktalari]
                uzunluk = polyline_uzunluk(noktalar, False)
                
                return Geometri(
                    tip='spline',
                    noktalar=noktalar,
                    kapali=entity.closed if hasattr(entity, 'closed') else False,
                    uzunluk=uzunluk,
                    alan=0.0
                )
        
        return None
        
    except Exception as e:
        st.warning(f"Entity okuma hatası ({dtype}): {str(e)}")
        return None

def dxf_oku(doc, birim: str = 'm') -> Dict[str, KalemVerisi]:
    """
    DXF dosyasını oku ve kalem bazlı grupla
    
    Args:
        doc: ezdxf document nesnesi
        birim: Hedef birim ('mm', 'cm', 'm')
        
    Returns:
        Kalem adı -> KalemVerisi sözlüğü
    """
    scale = BIRIM_CEVRIM.get(birim, 0.001)  # Varsayılan mm -> m
    
    veriler = {}
    islenen_entity = 0
    hatali_entity = 0
    
    for entity in doc.modelspace():
        try:
            layer = getattr(entity.dxf, 'layer', '')
            kalem_adi = katman_eslestir(layer)
            
            if not kalem_adi:
                continue
            
            geometri = entity_oku(entity, scale)
            
            if geometri:
                if kalem_adi not in veriler:
                    veriler[kalem_adi] = KalemVerisi(
                        kalem_adi=kalem_adi,
                        geometriler=[],
                        toplam_uzunluk=0.0,
                        toplam_alan=0.0,
                        renk=KALEMLER[kalem_adi]['renk']
                    )
                
                veriler[kalem_adi].geometriler.append(geometri)
                veriler[kalem_adi].toplam_uzunluk += geometri.uzunluk
                veriler[kalem_adi].toplam_alan += geometri.alan
                islenen_entity += 1
            
        except Exception as e:
            hatali_entity += 1
            continue
    
    st.session_state['islenen_entity'] = islenen_entity
    st.session_state['hatali_entity'] = hatali_entity
    
    return veriler

# =============================================================================
# GÖRSELLEŞTİRME FONKSİYONLARI
# =============================================================================
def plan_ciz(veriler: Dict[str, KalemVerisi], 
             secili_kalemler: List[str] = None,
             gosterim_modu: str = '2D') -> plt.Figure:
    """
    Mimari planı çiz
    
    Args:
        veriler: Kalem verileri sözlüğü
        secili_kalemler: Gösterilecek kalemler (None = tümü)
        gosterim_modu: '2D' veya '3D'
        
    Returns:
        matplotlib Figure nesnesi
    """
    if secili_kalemler is None:
        secili_kalemler = list(veriler.keys())
    
    fig, ax = plt.subplots(figsize=(14, 12), facecolor='#1a1a2e')
    ax.set_facecolor('#16213e')
    
    tum_x, tum_y = [], []
    
    for kalem_adi in secili_kalemler:
        if kalem_adi not in veriler:
            continue
        
        kalem = veriler[kalem_adi]
        renk = kalem.renk
        
        for geo in kalem.geometriler:
            if geo.tip in ['line', 'arc', 'spline']:
                if len(geo.noktalar) >= 2:
                    xs, ys = zip(*geo.noktalar)
                    ax.plot(xs, ys, color=renk, linewidth=2.5, alpha=0.9)
                    tum_x.extend(xs)
                    tum_y.extend(ys)
                    
            elif geo.tip in ['polyline', 'circle', 'ellipse']:
                if len(geo.noktalar) >= 2:
                    xs, ys = zip(*geo.noktalar)
                    
                    if geo.kapali:
                        # Kapalı şekilleri doldur
                        ax.fill(xs, ys, color=renk, alpha=0.25, edgecolor=renk, linewidth=2)
                    else:
                        ax.plot(xs, ys, color=renk, linewidth=2.5, alpha=0.9)
                    
                    tum_x.extend(xs)
                    tum_y.extend(ys)
    
    # Görünüm ayarları
    if tum_x and tum_y:
        x_min, x_max = min(tum_x), max(tum_x)
        y_min, y_max = min(tum_y), max(tum_y)
        
        margin_x = (x_max - x_min) * 0.05
        margin_y = (y_max - y_min) * 0.05
        
        ax.set_xlim(x_min - margin_x, x_max + margin_x)
        ax.set_ylim(y_min - margin_y, y_max + margin_y)
    
    ax.set_aspect('equal')
    ax.axis('off')
    ax.grid(True, alpha=0.2, color='white', linestyle='--')
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elemanlari = []
    for kalem_adi in secili_kalemler:
        if kalem_adi in veriler:
            renk = veriler[kalem_adi].renk
            legend_elemanlari.append(
                Line2D([0], [0], color=renk, linewidth=3, 
                       label=f"{kalem_adi} ({len(veriler[kalem_adi].geometriler)} adet)")
            )
    
    if legend_elemanlari:
        ax.legend(handles=legend_elemanlari, loc='upper left', 
                 facecolor='#0f3460', edgecolor='#e94560',
                 labelcolor='white', fontsize=10)
    
    plt.tight_layout()
    return fig

def kalem_istatistikleri(veriler: Dict[str, KalemVerisi]) -> pd.DataFrame:
    """Kalem bazlı istatistikler oluştur"""
    data = []
    for kalem_adi, kalem in veriler.items():
        data.append({
            'Kalem': kalem_adi,
            'Entity Sayısı': len(kalem.geometriler),
            'Toplam Uzunluk (m)': round(kalem.toplam_uzunluk, 2),
            'Toplam Alan (m²)': round(kalem.toplam_alan, 2),
            'Renk': kalem.renk
        })
    
    return pd.DataFrame(data)

# =============================================================================
# METRAJ HESAPLAMA FONKSİYONLARI
# =============================================================================
def metraj_hesapla(veriler: Dict[str, KalemVerisi], 
                   kat_yuksekligi: float,
                   duvar_kalinligi: float,
                   zemin_kalinligi: float = 0.15) -> List[MetrajSonuc]:
    """
    Detaylı metraj hesapla
    
    Args:
        veriler: Kalem verileri
        kat_yuksekligi: Kat yüksekliği (m)
        duvar_kalinligi: Duvar kalınlığı (m)
        zemin_kalinligi: Zemin kalınlığı (m)
        
    Returns:
        MetrajSonuc listesi
    """
    sonuclar = []
    
    # DUVAR METRAJLARI
    if 'DUVAR' in veriler:
        duvar = veriler['DUVAR']
        brut_duvar_alan = duvar.toplam_uzunluk * kat_yuksekligi
        
        # Pencere ve kapı çıkarmaları
        pencere_alani = veriler.get('PENCERE', KalemVerisi('', [], 0, 0, '')).toplam_alan
        kapi_alani = veriler.get('KAPI', KalemVerisi('', [], 0, 0, '')).toplam_alan
        toplam_cikarma = pencere_alani + kapi_alani
        
        # Net duvar alanı
        net_duvar_alani = max(0, brut_duvar_alan - toplam_cikarma)
        
        # Duvar örme (yüzey alanı)
        sonuclar.append(MetrajSonuc(
            kalem='Duvar Örme',
            poz_no='01.001',
            aciklama='İç ve dış duvar örme işleri',
            birim='m²',
            miktar=round(net_duvar_alani, 2),
            detay=f'Brüt: {brut_duvar_alan:.2f}m², Çıkarma: {toplam_cikarma:.2f}m²'
        ))
        
        # Duvar hacmi
        duvar_hacim = net_duvar_alani * duvar_kalinligi
        sonuclar.append(MetrajSonuc(
            kalem='Duvar Hacmi',
            poz_no='01.002',
            aciklama='Tuğla/betonarme duvar hacmi',
            birim='m³',
            miktar=round(duvar_hacim, 2),
            detay=f'{net_duvar_alani:.2f}m² × {duvar_kalinligi}m'
        ))
        
        # İç sıva
        ic_siva = net_duvar_alani * 1.0  # Tek taraf
        sonuclar.append(MetrajSonuc(
            kalem='İç Cephe Sıvası',
            poz_no='02.001',
            aciklama='Duvar iç yüzey sıvası',
            birim='m²',
            miktar=round(ic_siva, 2),
            detay='Net duvar alanı'
        ))
        
        # Dış sıva (varsa)
        dis_siva = net_duvar_alani * 0.5  # Varsayımsal
        sonuclar.append(MetrajSonuc(
            kalem='Dış Cephe Sıvası',
            poz_no='02.002',
            aciklama='Duvar dış yüzey sıvası',
            birim='m²',
            miktar=round(dis_siva, 2),
            detay='Tahmini dış cephe oranı'
        ))
        
        # Boya (2 kat)
        boya_alani = ic_siva + dis_siva
        sonuclar.append(MetrajSonuc(
            kalem='Duvar Boyası',
            poz_no='03.001',
            aciklama='İç ve dış cephe boya işleri',
            birim='m²',
            miktar=round(boya_alani, 2),
            detay='2 kat boya dahil'
        ))
    
    # ZEMİN METRAJLARI
    if 'ZEMIN' in veriler:
        zemin = veriler['ZEMIN']
        zemin_alani = zemin.toplam_alan
        
        sonuclar.append(MetrajSonuc(
            kalem='Zemin Kaplama',
            poz_no='04.001',
            aciklama='Seramik/fayans/mermer kaplama',
            birim='m²',
            miktar=round(zemin_alani, 2),
            detay='Net zemin alanı'
        ))
        
        # Zemin şapı
        sonuclar.append(MetrajSonuc(
            kalem='Zemin Şapı',
            poz_no='04.002',
            aciklama='Çimento şap işleri',
            birim='m²',
            miktar=round(zemin_alani, 2),
            detay=f'{zemin_kalinligi}m kalınlık'
        ))
        
        # Zemin yalıtımı
        sonuclar.append(MetrajSonuc(
            kalem='Zemin Yalıtımı',
            poz_no='04.003',
            aciklama='Su yalıtımı (varsa)',
            birim='m²',
            miktar=round(zemin_alani, 2),
            detay='Zemin üzeri yalıtım'
        ))
    
    # TAVAN METRAJLARI
    if 'TAVAN' in veriler:
        tavan = veriler['TAVAN']
        tavan_alani = tavan.toplam_alan
        
        sonuclar.append(MetrajSonuc(
            kalem='Asma Tavan',
            poz_no='05.001',
            aciklama='Alçıpan/asma tavan işleri',
            birim='m²',
            miktar=round(tavan_alani, 2),
            detay='Net tavan alanı'
        ))
        
        # Tavan boyası
        sonuclar.append(MetrajSonuc(
            kalem='Tavan Boyası',
            poz_no='05.002',
            aciklama='Tavan boya işleri',
            birim='m²',
            miktar=round(tavan_alani, 2),
            detay='2 kat boya'
        ))
    
    # PENCERE METRAJLARI
    if 'PENCERE' in veriler:
        pencere = veriler['PENCERE']
        pencere_alani = pencere.toplam_alan
        pencere_sayisi = len(pencere.geometriler)
        
        sonuclar.append(MetrajSonuc(
            kalem='Pencere Doğraması',
            poz_no='06.001',
            aciklama='PVC/alüminyum pencere doğraması',
            birim='m²',
            miktar=round(pencere_alani, 2),
            detay=f'{pencere_sayisi} adet pencere'
        ))
        
        # Pencere pervazı
        pencere_cevre = sum(geo.uzunluk for geo in pencere.geometriler if geo.kapali)
        sonuclar.append(MetrajSonuc(
            kalem='Pencere Pervazı',
            poz_no='06.002',
            aciklama='İç/dış pencere pervazı',
            birim='m',
            miktar=round(pencere_cevre, 2),
            detay='Pencere çevresi'
        ))
        
        # Cam
        sonuclar.append(MetrajSonuc(
            kalem='Pencere Camı',
            poz_no='06.003',
            aciklama='Çift cam panel',
            birim='m²',
            miktar=round(pencere_alani, 2),
            detay='Isı yalıtımlı cam'
        ))
    
    # KAPI METRAJLARI
    if 'KAPI' in veriler:
        kapi = veriler['KAPI']
        kapi_alani = kapi.toplam_alan
        kapi_sayisi = len(kapi.geometriler)
        
        sonuclar.append(MetrajSonuc(
            kalem='Kapı Doğraması',
            poz_no='07.001',
            aciklama='Ahşap/çelik kapı doğraması',
            birim='m²',
            miktar=round(kapi_alani, 2),
            detay=f'{kapi_sayisi} adet kapı'
        ))
        
        # Kapı pervazı
        kapi_cevre = sum(geo.uzunluk for geo in kapi.geometriler if geo.kapali)
        sonuclar.append(MetrajSonuc(
            kalem='Kapı Pervazı',
            poz_no='07.002',
            aciklama='Kapı pervazı',
            birim='m',
            miktar=round(kapi_cevre, 2),
            detay='Kapı çevresi'
        ))
        
        # Kapı kanadı
        sonuclar.append(MetrajSonuc(
            kalem='Kapı Kanadı',
            poz_no='07.003',
            aciklama='Kapı kanadı (ahşap/çelik)',
            birim='adet',
            miktar=kapi_sayisi,
            detay=f'Toplam {kapi_sayisi} adet'
        ))
    
    # MERDİVEN METRAJLARI
    if 'MERDİVEN' in veriler:
        merdiven = veriler['MERDİVEN']
        merdiven_uzunluk = merdiven.toplam_uzunluk
        
        sonuclar.append(MetrajSonuc(
            kalem='Merdiven İşleri',
            poz_no='08.001',
            aciklama='Betonarme/çelik merdiven',
            birim='m',
            miktar=round(merdiven_uzunluk, 2),
            detay='Merdiven projeksiyon uzunluğu'
        ))
        
        # Korkuluk
        sonuclar.append(MetrajSonuc(
            kalem='Merdiven Korkuluğu',
            poz_no='08.002',
            aciklama='Paslanmaz çelik korkuluk',
            birim='m',
            miktar=round(merdiven_uzunluk, 2),
            detay='Merdiven korkuluk uzunluğu'
        ))
    
    return sonuclar

def metraj_tablosu(sonuclar: List[MetrajSonuc]) -> pd.DataFrame:
    """Metraj sonuçlarını DataFrame'e dönüştür"""
    data = []
    for s in sonuclar:
        data.append({
            'Poz No': s.poz_no,
            'Kalem': s.kalem,
            'Açıklama': s.aciklama,
            'Birim': s.birim,
            'Miktar': s.miktar,
            'Detay': s.detay
        })
    
    return pd.DataFrame(data)

# =============================================================================
# RAPORLAMA FONKSİYONLARI
# =============================================================================
def excel_raporu_olustur(sonuclar: List[MetrajSonuc], 
                         veriler: Dict[str, KalemVerisi],
                         dosya_adi: str) -> bytes:
    """Excel formatında rapor oluştur"""
    import io
    
    output = io.BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Metraj tablosu
        df_metraj = metraj_tablosu(sonuclar)
        df_metraj.to_excel(writer, sheet_name='Metraj', index=False)
        
        # Kalem istatistikleri
        df_istatistik = kalem_istatistikleri(veriler)
        df_istatistik.to_excel(writer, sheet_name='Kalem İstatistikleri', index=False)
        
        # Özet bilgiler
        ozet_data = {
            'Rapor Tarihi': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            'Toplam Poz': [len(sonuclar)],
            'Toplam Kalem': [len(veriler)]
        }
        df_ozet = pd.DataFrame(ozet_data)
        df_ozet.to_excel(writer, sheet_name='Özet', index=False)
    
    output.seek(0)
    return output.getvalue()

def csv_raporu(sonuclar: List[MetrajSonuc]) -> str:
    """CSV formatında rapor"""
    df = metraj_tablosu(sonuclar)
    return df.to_csv(index=False, encoding='utf-8-sig')

def json_raporu(sonuclar: List[MetrajSonuc], veriler: Dict[str, KalemVerisi]) -> str:
    """JSON formatında rapor"""
    rapor = {
        'tarih': datetime.now().isoformat(),
        'metraj': [
            {
                'poz_no': s.poz_no,
                'kalem': s.kalem,
                'aciklama': s.aciklama,
                'birim': s.birim,
                'miktar': s.miktar,
                'detay': s.detay
            }
            for s in sonuclar
        ],
        'kalem_istatistikleri': {
            k: {
                'entity_sayisi': len(v.geometriler),
                'toplam_uzunluk': v.toplam_uzunluk,
                'toplam_alan': v.toplam_alan
            }
            for k, v in veriler.items()
        }
    }
    
    return json.dumps(rapor, ensure_ascii=False, indent=2)

# =============================================================================
# GİRİŞ / KİMLİK DOĞRULAMA
# =============================================================================
def giris_formu():
    """Kullanıcı giriş formu"""
    st.markdown('<h1 class="main-header">🏗️ Mimari Metraj Pro</h1>', 
                unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 20px; background-color: #262730; 
                    border-radius: 10px; margin-bottom: 20px;'>
            <h3>Profesyonel Metraj Analizi</h3>
            <p>DXF dosyalarınızdan otomatik metraj çıkarın</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("login_form"):
            kullanici = st.text_input("Kullanıcı Adı", value="admin")
            sifre = st.text_input("Şifre", type="password", value="1234")
            
            submitted = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if submitted:
                if kullanici == "admin" and sifre == "1234":
                    st.session_state.logged_in = True
                    st.session_state.kullanici = kullanici
                    st.success("✅ Giriş başarılı!")
                    st.rerun()
                else:
                    st.error("❌ Kullanıcı adı veya şifre hatalı!")

# =============================================================================
# ANA UYGULAMA
# =============================================================================
def ana_uygulama():
    """Ana uygulama arayüzü"""
    
    # Header
    st.markdown('<h1 class="main-header">🏗️ Mimari Metraj Pro</h1>', 
                unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.write(f"### 👤 {st.session_state.get('kullanici', 'Kullanıcı')}")
        
        st.divider()
        
        # Dosya yükleme
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle", type=["dxf"])
        
        st.divider()
        
        # Ayarlar
        st.write("### ⚙️ Ayarlar")
        
        birim = st.selectbox(
            "Ölçü Birimi",
            options=["mm", "cm", "m"],
            index=2,
            help="DXF dosyasındaki ölçü birimi"
        )
        
        kat_yuk = st.number_input(
            "Kat Yüksekliği (m)",
            min_value=1.0,
            max_value=10.0,
            value=2.85,
            step=0.05,
            help="Metraj hesaplamaları için kat yüksekliği"
        )
        
        duvar_kal = st.number_input(
            "Duvar Kalınlığı (m)",
            min_value=0.05,
            max_value=1.0,
            value=0.20,
            step=0.01,
            help="Duvar hacim hesaplamaları için"
        )
        
        zemin_kal = st.number_input(
            "Zemin Kalınlığı (m)",
            min_value=0.05,
            max_value=0.50,
            value=0.15,
            step=0.01,
            help="Zemin şap kalınlığı"
        )
        
        st.divider()
        
        # Görselleştirme ayarları
        st.write("### 👁️ Görünüm")
        gosterim_modu = st.radio(
            "Görünüm Modu",
            options=['2D Plan', 'Katmanlar'],
            index=0
        )
        
        st.divider()
        
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()
    
    # Ana içerik
    if not uploaded:
        st.info("👈 Lütfen sol panelden bir DXF dosyası yükleyin")
        
        # Örnek bilgi kartları
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("""
            <div class='metric-card'>
                <h4>📐 Otomatik Metraj</h4>
                <p>DXF dosyalarınızdan otomatik olarak duvar, zemin, 
                tavan, pencere ve kapı metrajları çıkarın.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown("""
            <div class='metric-card'>
                <h4>📊 Detaylı Raporlama</h4>
                <p>Excel, CSV ve JSON formatlarında detaylı metraj 
                raporları oluşturun.</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown("""
            <div class='metric-card'>
                <h4>🎨 Görsel Analiz</h4>
                <p>Katman bazlı renklendirilmiş plan görünümü ile 
                projelerinizi analiz edin.</p>
            </div>
            """, unsafe_allow_html=True)
        
        st.stop()
    
    # DXF İşleme
    with st.spinner("DXF dosyası işleniyor..."):
        tmp_path = None
        try:
            # Geçici dosya oluştur
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            
            # DXF oku
            doc = ezdxf.readfile(tmp_path)
            veriler = dxf_oku(doc, birim)
            
            if not veriler:
                st.warning("⚠️ DXF dosyasında tanımlı kalem bulunamadı!")
                st.info("Desteklenen katmanlar: " + 
                       ", ".join([f"{k}: {v['katmanlar']}" 
                                  for k, v in KALEMLER.items()]))
                st.stop()
            
            # Başarı mesajı
            islenen = st.session_state.get('islenen_entity', 0)
            hatali = st.session_state.get('hatali_entity', 0)
            
            st.success(f"✅ {islenen} entity başarıyla işlendi" + 
                      (f" ({hatali} hatalı atlandı)" if hatali > 0 else ""))
            
            # Sekmeler
            tab_plan, tab_metraj, tab_istatistik, tab_rapor = st.tabs([
                "📐 Plan Görünümü", "📊 Metraj", "📈 İstatistikler", "📄 Rapor"
            ])
            
            # === PLAN GÖRÜNÜMÜ ===
            with tab_plan:
                col1, col2 = st.columns([3, 1])
                
                with col2:
                    st.write("### 🎨 Katmanlar")
                    secili_kalemler = []
                    for kalem_adi in veriler.keys():
                        kalem = veriler[kalem_adi]
                        if st.checkbox(
                            f"{kalem_adi} ({len(kalem.geometriler)})",
                            value=True,
                            key=f"chk_{kalem_adi}"
                        ):
                            secili_kalemler.append(kalem_adi)
                    
                    st.divider()
                    
                    # Zoom kontrolü
                    st.write("### 🔍 Zoom")
                    zoom_level = st.slider("Yakınlaştırma", 0.5, 3.0, 1.0, 0.1)
                
                with col1:
                    if secili_kalemler:
                        fig = plan_ciz(veriler, secili_kalemler)
                        st.pyplot(fig, use_container_width=True)
                    else:
                        st.info("En az bir katman seçin")
            
            # === METRAJ ===
            with tab_metraj:
                sonuclar = metraj_hesapla(veriler, kat_yuk, duvar_kal, zemin_kal)
                
                if sonuclar:
                    df_metraj = metraj_tablosu(sonuclar)
                    
                    # Özet metrikler
                    cols = st.columns(4)
                    
                    toplam_duvar = sum(s.miktar for s in sonuclar if 'Duvar' in s.kalem and s.birim == 'm²')
                    toplam_zemin = sum(s.miktar for s in sonuclar if 'Zemin' in s.kalem and s.birim == 'm²')
                    toplam_tavan = sum(s.miktar for s in sonuclar if 'Tavan' in s.kalem and s.birim == 'm²')
                    toplam_hacim = sum(s.miktar for s in sonuclar if s.birim == 'm³')
                    
                    with cols[0]:
                        st.metric("Toplam Duvar", f"{toplam_duvar:.2f} m²")
                    with cols[1]:
                        st.metric("Toplam Zemin", f"{toplam_zemin:.2f} m²")
                    with cols[2]:
                        st.metric("Toplam Tavan", f"{toplam_tavan:.2f} m²")
                    with cols[3]:
                        st.metric("Toplam Hacim", f"{toplam_hacim:.2f} m³")
                    
                    st.divider()
                    
                    # Metraj tablosu
                    st.dataframe(
                        df_metraj,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Poz No': st.column_config.TextColumn('Poz No', width='small'),
                            'Kalem': st.column_config.TextColumn('Kalem', width='medium'),
                            'Açıklama': st.column_config.TextColumn('Açıklama', width='large'),
                            'Birim': st.column_config.TextColumn('Birim', width='small'),
                            'Miktar': st.column_config.NumberColumn('Miktar', format='%.2f'),
                            'Detay': st.column_config.TextColumn('Detay', width='large')
                        }
                    )
                else:
                    st.info("Metraj hesaplanacak veri bulunamadı")
            
            # === İSTATİSTİKLER ===
            with tab_istatistik:
                df_istatistik = kalem_istatistikleri(veriler)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("### 📊 Kalem Dağılımı")
                    st.dataframe(df_istatistik, use_container_width=True, hide_index=True)
                
                with col2:
                    st.write("### 📈 Entity Grafiği")
                    
                    # Pasta grafiği
                    fig, ax = plt.subplots(figsize=(8, 6), facecolor='#1a1a2e')
                    ax.set_facecolor('#1a1a2e')
                    
                    labels = df_istatistik['Kalem']
                    sizes = df_istatistik['Entity Sayısı']
                    colors = df_istatistik['Renk']
                    
                    wedges, texts, autotexts = ax.pie(
                        sizes, labels=labels, colors=colors,
                        autopct='%1.1f%%', startangle=90,
                        textprops={'color': 'white'}
                    )
                    
                    ax.axis('equal')
                    plt.tight_layout()
                    st.pyplot(fig, use_container_width=True)
                
                # Alan dağılımı
                st.write("### 📊 Alan Dağılımı")
                fig2, ax2 = plt.subplots(figsize=(10, 5), facecolor='#1a1a2e')
                ax2.set_facecolor('#16213e')
                
                x_pos = range(len(df_istatistik))
                ax2.bar(x_pos, df_istatistik['Toplam Alan (m²)'], 
                       color=df_istatistik['Renk'], alpha=0.8)
                ax2.set_xticks(x_pos)
                ax2.set_xticklabels(df_istatistik['Kalem'], rotation=45, ha='right')
                ax2.set_ylabel('Alan (m²)', color='white')
                ax2.set_title('Kalem Bazlı Alan Dağılımı', color='white', fontsize=14)
                ax2.tick_params(colors='white')
                ax2.spines['bottom'].set_color('white')
                ax2.spines['left'].set_color('white')
                ax2.grid(True, alpha=0.2, color='white')
                
                plt.tight_layout()
                st.pyplot(fig2, use_container_width=True)
            
            # === RAPOR ===
            with tab_rapor:
                st.write("### 📄 Rapor İndir")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Excel
                    if sonuclar:
                        excel_data = excel_raporu_olustur(sonuclar, veriler, uploaded.name)
                        st.download_button(
                            label="📥 Excel İndir",
                            data=excel_data,
                            file_name=f"{uploaded.name.replace('.dxf', '')}_metraj.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                
                with col2:
                    # CSV
                    if sonuclar:
                        csv_data = csv_raporu(sonuclar)
                        st.download_button(
                            label="📄 CSV İndir",
                            data=csv_data,
                            file_name=f"{uploaded.name.replace('.dxf', '')}_metraj.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                
                with col3:
                    # JSON
                    if sonuclar:
                        json_data = json_raporu(sonuclar, veriler)
                        st.download_button(
                            label="📋 JSON İndir",
                            data=json_data,
                            file_name=f"{uploaded.name.replace('.dxf', '')}_metraj.json",
                            mime="application/json",
                            use_container_width=True
                        )
                
                st.divider()
                
                # Önizleme
                st.write("### 👁️ Rapor Önizleme")
                if sonuclar:
                    st.json(json_raporu(sonuclar, veriler))
        
        except Exception as e:
            st.error(f"❌ Hata oluştu: {str(e)}")
            st.exception(e)
        
        finally:
            # Temizlik
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except:
                    pass

# =============================================================================
# UYGULAMA BAŞLANGICI
# =============================================================================
def main():
    """Uygulama giriş noktası"""
    
    # Session state başlatma
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    # Giriş kontrolü
    if not st.session_state.logged_in:
        giris_formu()
    else:
        ana_uygulama()

if __name__ == "__main__":
    main()
