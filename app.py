"""
Mimari Duvar Metraj Uygulaması v4.0 - Çoklu Kalem Analizi
Geliştirici: Barış Öker - Fi-le Yazılım 
Sürüm: 4.0 - Multi-Kalem Metraj
"""
import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import math
import tempfile
import os
import io
import numpy as np

# =============================================================================
# KALEM YAPILANDIRMASI
# =============================================================================
KALEM_RENKLERI = {
    'DUVAR': {
        'renk': '#FF4B4B',      # Kırmızı
        'katmanlar': ['DUVAR', 'WALL', 'DUVAR', 'WALLS', 'DUWAR'],
        'tip': 'cizgi',
        'kalinlik': 2.0
    },
    'BETONARME': {
        'renk': '#4B9FFF',      # Mavi
        'katmanlar': ['BETON', 'BETONARME', 'CONCRETE', 'KIRIS', 'KOLON', 'BEAM', 'COLUMN'],
        'tip': 'cizgi',
        'kalinlik': 2.5
    },
    'SIVA': {
        'renk': '#4BFF88',      # Yeşil
        'katmanlar': ['SIVA', 'SIVAMA', 'PLASTER', 'RENDER'],
        'tip': 'alan',
        'kalinlik': 1.5
    },
    'ZEMIN': {
        'renk': '#FFD700',      # Altın sarı
        'katmanlar': ['ZEMIN', 'FLOOR', 'YER', 'DOSEME', 'GROUND'],
        'tip': 'alan',
        'kalinlik': 2.0
    },
    'DEMIR': {
        'renk': '#9B4BFF',      # Mor
        'katmanlar': ['DEMIR', 'DEMIR_HASIR', 'REBAR', 'CELİK', 'STEEL', 'IRON'],
        'tip': 'nokta',
        'kalinlik': 1.0
    },
    'PENCERE': {
        'renk': '#00FFFF',      # Cyan
        'katmanlar': ['PENCERE', 'WINDOW', 'CAM', 'WIN', 'PEN'],
        'tip': 'bosluk',
        'kalinlik': 1.5
    },
    'KAPI': {
        'renk': '#FF8C00',      # Turuncu
        'katmanlar': ['KAPI', 'DOOR', 'KAP', 'DOORS', 'GATE'],
        'tip': 'bosluk',
        'kalinlik': 1.5
    }
}

# =============================================================================
# SAYFA KONFİGÜRASYONU
# =============================================================================
st.set_page_config(page_title="Çoklu Kalem Metraj Analizi", layout="wide")

st.markdown("""
    <style>
    .profile-card { text-align: center; padding: 1rem; background-color: #262730; border-radius: 10px; margin-bottom: 1rem; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
    .metric-box { background-color: #f0f2f6; padding: 1.5rem; border-radius: 10px; border-left: 5px solid #FF4B4B; }
    .kalem-badge { display: inline-block; padding: 4px 8px; border-radius: 4px; color: white; font-size: 0.8em; margin: 2px; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# GİRİŞ EKRANI
# =============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ Çoklu Kalem Metraj Analizi")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            username = st.text_input("Kullanıcı Adı")
            password = st.text_input("Şifre", type="password")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                if username == "admin" and password == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı giriş!")
    st.stop()

# =============================================================================
# ANALİZ FONKSİYONLARI
# =============================================================================
def analiz_tum_kalemler(doc, birim_scale):
    """Tüm kalemleri ayrı ayrı analiz eder."""
    sonuclar = {}
    
    for kalem_adi, config in KALEM_RENKLERI.items():
        bulunan_katman = None
        geometriler = []
        toplam_uzunluk = 0.0
        toplam_alan = 0.0
        obje_sayisi = 0
        
        # Katman ara
        for entity in doc.modelspace():
            try:
                layer = getattr(entity.dxf, 'layer', '').upper()
                if any(k.upper() in layer for k in config['katmanlar']):
                    bulunan_katman = entity.dxf.layer
                    break
            except:
                continue
        
        # Geometri topla
        for entity in doc.modelspace():
            try:
                layer = getattr(entity.dxf, 'layer', '').upper()
                if not any(k.upper() in layer for k in config['katmanlar']):
                    continue
                
                dtype = entity.dxftype()
                
                if dtype == "LINE":
                    s, e = entity.dxf.start, entity.dxf.end
                    uzunluk = math.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2) / birim_scale
                    geometriler.append({
                        'tip': 'line',
                        'x1': s[0]/birim_scale, 'y1': s[1]/birim_scale,
                        'x2': e[0]/birim_scale, 'y2': e[1]/birim_scale,
                        'uzunluk': uzunluk
                    })
                    toplam_uzunluk += uzunluk
                    obje_sayisi += 1
                    
                elif dtype == "LWPOLYLINE":
                    pts = list(entity.get_points('xy'))
                    noktalar = [(p[0]/birim_scale, p[1]/birim_scale) for p in pts]
                    
                    # Uzunluk hesapla
                    uzunluk = 0
                    for i in range(len(noktalar)-1):
                        x1, y1 = noktalar[i]
                        x2, y2 = noktalar[i+1]
                        uzunluk += math.sqrt((x2-x1)**2 + (y2-y1)**2)
                    
                    # Alan hesapla (kapalı ise)
                    alan = 0
                    is_closed = entity.closed or (len(noktalar) > 2 and 
                                                  abs(noktalar[0][0] - noktalar[-1][0]) < 0.001 and
                                                  abs(noktalar[0][1] - noktalar[-1][1]) < 0.001)
                    if is_closed:
                        for i in range(len(noktalar)-1):
                            j = (i + 1) % (len(noktalar)-1)
                            alan += noktalar[i][0] * noktalar[j][1]
                            alan -= noktalar[j][0] * noktalar[i][1]
                        alan = abs(alan) / 2
                    
                    geometriler.append({
                        'tip': 'polyline',
                        'noktalar': noktalar,
                        'uzunluk': uzunluk,
                        'alan': alan,
                        'kapali': is_closed
                    })
                    toplam_uzunluk += uzunluk
                    toplam_alan += alan
                    obje_sayisi += 1
                    
                elif dtype == "CIRCLE":
                    c = entity.dxf.center
                    r = entity.dxf.radius / birim_scale
                    alan = math.pi * r * r
                    geometriler.append({
                        'tip': 'circle',
                        'x': c[0]/birim_scale, 'y': c[1]/birim_scale,
                        'r': r,
                        'alan': alan,
                        'cevre': 2 * math.pi * r
                    })
                    toplam_alan += alan
                    obje_sayisi += 1
                    
                elif dtype == "ARC":
                    c = entity.dxf.center
                    r = entity.dxf.radius / birim_scale
                    start_angle = math.radians(entity.dxf.start_angle)
                    end_angle = math.radians(entity.dxf.end_angle)
                    
                    # Yay uzunluğu
                    if end_angle < start_angle:
                        end_angle += 2 * math.pi
                    arc_length = r * (end_angle - start_angle)
                    
                    geometriler.append({
                        'tip': 'arc',
                        'x': c[0]/birim_scale, 'y': c[1]/birim_scale,
                        'r': r,
                        'start_angle': entity.dxf.start_angle,
                        'end_angle': entity.dxf.end_angle,
                        'uzunluk': arc_length
                    })
                    toplam_uzunluk += arc_length
                    obje_sayisi += 1
                    
            except Exception as e:
                continue
        
        sonuclar[kalem_adi] = {
            'bulundu': bulunan_katman is not None,
            'katman_adi': bulunan_katman,
            'geometriler': geometriler,
            'toplam_uzunluk': toplam_uzunluk,
            'toplam_alan': toplam_alan,
            'obje_sayisi': obje_sayisi,
            'renk': config['renk'],
            'tip': config['tip']
        }
    
    return sonuclar

def ciz_tum_kalemler(analiz_sonuclari, secili_kalemler=None):
    """Tüm kalemleri aynı figürde, ayrı renklerde çizer."""
    if secili_kalemler is None:
        secili_kalemler = list(KALEM_RENKLERI.keys())
    
    fig, ax = plt.subplots(figsize=(16, 14), facecolor='#0e1117')
    ax.set_facecolor('#0e1117')
    
    # Sınırları bul
    tum_x, tum_y = [], []
    
    for kalem_adi, veri in analiz_sonuclari.items():
        if kalem_adi not in secili_kalemler:
            continue
        for geo in veri['geometriler']:
            if geo['tip'] == 'line':
                tum_x.extend([geo['x1'], geo['x2']])
                tum_y.extend([geo['y1'], geo['y2']])
            elif geo['tip'] == 'polyline':
                if geo['noktalar']:
                    xs, ys = zip(*geo['noktalar'])
                    tum_x.extend(xs)
                    tum_y.extend(ys)
            elif geo['tip'] in ['circle', 'arc']:
                tum_x.extend([geo['x'] - geo['r'], geo['x'] + geo['r']])
                tum_y.extend([geo['y'] - geo['r'], geo['y'] + geo['r']])
    
    # Çizim
    for kalem_adi, veri in analiz_sonuclari.items():
        if kalem_adi not in secili_kalemler or not veri['geometriler']:
            continue
            
        renk = veri['renk']
        config = KALEM_RENKLERI[kalem_adi]
        
        for geo in veri['geometriler']:
            if geo['tip'] == 'line':
                ax.plot([geo['x1'], geo['x2']], [geo['y1'], geo['y2']], 
                       color=renk, lw=config['kalinlik'], alpha=0.9)
                       
            elif geo['tip'] == 'polyline':
                xs, ys = zip(*geo['noktalar'])
                if config['tip'] == 'alan' and geo.get('kapali'):
                    ax.fill(xs, ys, color=renk, alpha=0.25)
                    ax.plot(xs, ys, color=renk, lw=config['kalinlik'])
                else:
                    ax.plot(xs, ys, color=renk, lw=config['kalinlik'])
                    
            elif geo['tip'] == 'circle':
                circle = plt.Circle((geo['x'], geo['y']), geo['r'], 
                                  color=renk, fill=config['tip']=='alan', 
                                  alpha=0.3 if config['tip']=='alan' else 0.9,
                                  lw=config['kalinlik'])
                ax.add_patch(circle)
                
            elif geo['tip'] == 'arc':
                # Yay çizimi
                arc = mpatches.Arc((geo['x'], geo['y']), geo['r']*2, geo['r']*2,
                                  angle=0, theta1=geo['start_angle'], theta2=geo['end_angle'],
                                  color=renk, lw=config['kalinlik'])
                ax.add_patch(arc)
    
    # Zoom ayarı
    if tum_x and tum_y:
        margin = max(max(tum_x) - min(tum_x), max(tum_y) - min(tum_y)) * 0.05
        ax.set_xlim(min(tum_x) - margin, max(tum_x) + margin)
        ax.set_ylim(min(tum_y) - margin, max(tum_y) + margin)
    
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Legend
    legend_elements = []
    for kalem in secili_kalemler:
        if analiz_sonuclari[kalem]['geometriler']:
            legend_elements.append(
                plt.Line2D([0], [0], color=KALEM_RENKLERI[kalem]['renk'], 
                          lw=4, label=f"{kalem} ({analiz_sonuclari[kalem]['obje_sayisi']})")
            )
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper left', 
                 facecolor='#262730', edgecolor='white', 
                 labelcolor='white', fontsize=9, framealpha=0.9)
    
    return fig

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("""
        <div class="profile-card">
            <img src="https://www.w3schools.com/howto/img_avatar.png" class="profile-img">
            <h4 style="color: white; margin: 0;">Admin Kullanıcı</h4>
            <p style="color: #888; margin: 0; font-size: 0.9em;">Fi-le Yazılım</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    uploaded = st.file_uploader("📁 DXF Dosyası", type=["dxf"])
    birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    
    st.divider()
    st.subheader("⚙️ Hesaplama Parametreleri")
    kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01, min_value=0.1)
    duvar_kalinlik = st.number_input("🧱 Duvar Kalınlığı (m)", value=0.20, step=0.01, min_value=0.05)
    siva_kalinlik = st.number_input("🎨 Sıva Kalınlığı (m)", value=0.02, step=0.005, min_value=0.0)
    beton_orani = st.slider("🏗️ Beton Oranı (%)", 5, 30, 15) / 100
    demir_orani = st.number_input("⚙️ Demir (kg/m³ beton)", value=100, step=10)
    
    st.divider()
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# =============================================================================
# ANA UYGULAMA
# =============================================================================
st.title("🏗️ Çoklu Kalem Metraj Analizi v4.0")

if uploaded is None:
    st.info("👈 Lütfen sol menüden DXF dosyası yükleyin")
    
    # Örnek gösterim
    st.divider()
    st.subheader("📋 Nasıl Çalışır?")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
        **1. DXF Yükle**
        - AutoCAD'den export edilmiş .dxf
        - Her kalem ayrı katmanda olmalı
        """)
    with col2:
        st.markdown("""
        **2. Otomatik Analiz**
        - Sistem tüm katmanları tarar
        - Her kalem için metraj hesaplar
        """)
    with col3:
        st.markdown("""
        **3. Görsel + Rapor**
        - Renkli teknik plan
        - Detaylı metraj tablosu
        - Excel export
        """)
    st.stop()

# DXF İŞLEME
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    
    doc = ezdxf.readfile(tmp_path)
    birim_carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
    
    # === TÜM KALEMLERİ ANALİZ ET ===
    with st.spinner("🔍 Tüm kalemler analiz ediliyor..."):
        tum_analizler = analiz_tum_kalemler(doc, birim_carpani)
    
    # === SIDEBAR: KALEM SEÇİMİ ===
    with st.sidebar:
        st.divider()
        st.subheader("🎨 Görünüm Katmanları")
        
        secili_kalemler = []
        for kalem_adi, veri in tum_analizler.items():
            if not veri['geometriler']:
                continue
                
            col1, col2 = st.columns([0.15, 0.85])
            with col1:
                st.markdown(
                    f"<div style='width:20px;height:20px;background:{veri['renk']};"
                    f"border-radius:3px;margin-top:3px;border:1px solid #555;'></div>", 
                    unsafe_allow_html=True
                )
            with col2:
                default_checked = kalem_adi in ['DUVAR', 'PENCERE', 'KAPI']
                if st.checkbox(
                    f"**{kalem_adi}** ({veri['obje_sayisi']} obje)", 
                    value=default_checked, 
                    key=f"chk_{kalem_adi}"
                ):
                    secili_kalemler.append(kalem_adi)
    
    # === BULUNAN KALEMLER ÖZETİ ===
    bulunan_kalemler = [k for k, v in tum_analizler.items() if v['geometriler']]
    if bulunan_kalemler:
        st.success(f"✅ **{len(bulunan_kalemler)} kalem** tespit edildi: {', '.join(bulunan_kalemler)}")
    else:
        st.warning("⚠️ Hiç kalem bulunamadı. DXF katman adlarını kontrol edin.")
    
    # === ANA GÖRSELLEŞTİRME ===
    if secili_kalemler:
        st.subheader("📐 Teknik Plan Görünümü")
        
        fig = ciz_tum_kalemler(tum_analizler, secili_kalemler)
        st.pyplot(fig, use_container_width=True)
        
        # Görsel indirme
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', 
                   facecolor='#0e1117', edgecolor='none')
        buf.seek(0)
        st.download_button("📥 Plan Görseli İndir (PNG)", buf, 
                        f"plan_{uploaded.name.replace('.dxf', '')}.png")
    else:
        st.info("👈 Soldan görüntülemek istediğiniz kalemleri seçin")
    
    # === HER KALEM İÇİN AYRı METRAJ ===
    st.subheader("📊 Kalem Bazlı Metrajlar")
    
    metraj_tablosu = []
    
    # Önce temel değerleri hesapla
    duvar_alan = 0
    duvar_hacim = 0
    
    for kalem_adi in secili_kalemler:
        veri = tum_analizler[kalem_adi]
        if not veri['geometriler']:
            continue
            
        config = KALEM_RENKLERI[kalem_adi]
        
        if kalem_adi == 'DUVAR':
            # Duvar: Uzunluk × Yükseklik
            alan = veri['toplam_uzunluk'] * kat_yuksekligi
            hacim = alan * duvar_kalinlik
            duvar_alan = alan
            duvar_hacim = hacim
            
            metraj_tablosu.extend([
                {
                    'Kalem': 'Duvar Örme',
                    'Katman': veri['katman_adi'] or 'DUVAR',
                    'Birim': 'm²',
                    'Miktar': round(alan, 2),
                    'Birim Fiyat': '',
                    'Tutar': '',
                    'Açıklama': f'Aks: {veri["toplam_uzunluk"]:.2f}m × Yükseklik: {kat_yuksekligi}m'
                },
                {
                    'Kalem': 'Duvar Hacmi',
                    'Katman': '-',
                    'Birim': 'm³',
                    'Miktar': round(hacim, 2),
                    'Birim Fiyat': '',
                    'Tutar': '',
                    'Açıklama': f'{alan:.2f}m² × {duvar_kalinlik}m kalınlık'
                }
            ])
            
        elif kalem_adi == 'SIVA':
            # Sıva: Duvar alanının 2 tarafı
            siva_alan = duvar_alan * 2  # İç + dış
            siva_hacim = siva_alan * siva_kalinlik
            
            metraj_tablosu.extend([
                {
                    'Kalem': 'İç Cephe Sıvası',
                    'Katman': veri['katman_adi'] or 'SIVA',
                    'Birim': 'm²',
                    'Miktar': round(duvar_alan, 2),
                    'Birim Fiyat': '',
                    'Tutar': '',
                    'Açıklama': 'Duvar alanının iç tarafı'
                },
                {
                    'Kalem': 'Dış Cephe Sıvası',
                    'Katman': veri['katman_adi'] or 'SIVA',
                    'Birim': 'm²',
                    'Miktar': round(duvar_alan, 2),
                    'Birim Fiyat': '',
                    'Tutar': '',
                    'Açıklama': 'Duvar alanının dış tarafı'
                }
            ])
            if siva_kalinlik > 0:
                metraj_tablosu.append({
                    'Kalem': 'Sıva Hacmi',
                    'Katman': '-',
                    'Birim': 'm³',
                    'Miktar': round(siva_hacim, 2),
                    'Birim Fiyat': '',
                    'Tutar': '',
                    'Açıklama': f'{siva_alan:.2f}m² × {siva_kalinlik}m kalınlık'
                })
            
        elif kalem_adi == 'BETONARME':
            # Betonarme: Duvar hacminin %'si
            beton_hacim = duvar_hacim * beton_orani
            
            metraj_tablosu.append({
                'Kalem': 'Betonarme',
                'Katman': veri['katman_adi'] or 'BETON',
                'Birim': 'm³',
                'Miktar': round(beton_hacim, 2),
                'Birim Fiyat': '',
                'Tutar': '',
                'Açıklama': f'Duvar hacminin %{int(beton_orani*100)}'
            })
            
        elif kalem_adi == 'DEMIR':
            # Demir: Beton hacmi × kg/m3
            beton_m3 = duvar_hacim * beton_orani
            demir_kg = beton_m3 * demir_orani
            
            metraj_tablosu.append({
                'Kalem': 'İnşaat Demiri',
                'Katman': veri['katman_adi'] or 'DEMIR',
                'Birim': 'kg',
                'Miktar': round(demir_kg, 2),
                'Birim Fiyat': '',
                'Tutar': '',
                'Açıklama': f'{beton_m3:.2f}m³ × {demir_orani}kg/m³'
            })
            
        elif kalem_adi == 'ZEMIN':
            # Zemin: DXF'deki alan
            zemin_alan = veri['toplam_alan'] or 0
            
            metraj_tablosu.append({
                'Kalem': 'Zemin Döşeme',
                'Katman': veri['katman_adi'] or 'ZEMIN',
                'Birim': 'm²',
                'Miktar': round(zemin_alan, 2),
                'Birim Fiyat': '',
                'Tutar': '',
                'Açıklama': 'Kapalı zemin alanı'
            })
            
        elif kalem_adi in ['PENCERE', 'KAPI']:
            # Boşluklar: Çıkarma (negatif)
            bosluk_alan = veri['toplam_alan']
            
            metraj_tablosu.append({
                'Kalem': f'{kalem_adi.title()} Çıkarması',
                'Katman': veri['katman_adi'] or kalem_adi,
                'Birim': 'm²',
                'Miktar': round(-bosluk_alan, 2),
                'Birim Fiyat': '',
                'Tutar': '',
                'Açıklama': 'Duvar örmesinden düşülür'
            })
    
    # === TABLO GÖSTERİM ===
    if metraj_tablosu:
        df_metraj = pd.DataFrame(metraj_tablosu)
        
        # Renklendirme
        def renk_satir(row):
            if 'Çıkarma' in row['Kalem']:
                return ['background-color: #ffcccc; color: #990000'] * len(row)
            elif 'Hacmi' in row['Kalem']:
                return ['background-color: #fff4e6'] * len(row)
            elif row['Kalem'] in ['Duvar Örme', 'Betonarme']:
                return ['background-color: #e6f3ff; font-weight: bold'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            df_metraj.style.apply(renk_satir, axis=1), 
            use_container_width=True,
            height=min(400, len(df_metraj) * 35 + 50)
        )
        
        # === ÖZET METRIKLER ===
        st.subheader("📈 Özet")
        
        toplam_pozitif = sum([m['Miktar'] for m in metraj_tablosu if m['Miktar'] > 0])
        toplam_cikarma = sum([abs(m['Miktar']) for m in metraj_tablosu if m['Miktar'] < 0])
        net_metraj = toplam_pozitif - toplam_cikarma
        
        # Kalem bazlı özet
        cols = st.columns(min(4, len([m for m in metraj_tablosu if m['Miktar'] > 0])))
        idx = 0
        for m in metraj_tablosu:
            if m['Miktar'] > 0 and idx < 4:
                with cols[idx]:
                    st.metric(
                        m['Kalem'], 
                        f"{m['Miktar']:.2f} {m['Birim']}",
                        help=m['Açıklama']
                    )
                idx += 1
        
        st.divider()
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Pozitif", f"{toplam_pozitif:.2f} birim")
        col2.metric("Toplam Çıkarma", f"-{toplam_cikarma:.2f} birim", delta_color="inverse")
        col3.metric("Net Metraj", f"{net_metraj:.2f} birim", delta=f"{net_metraj:.2f}")
        
        # === EXPORT ===
        st.divider()
        st.subheader("📥 Rapor İndir")
        
        col_dl1, col_dl2 = st.columns(2)
        
        with col_dl1:
            csv = df_metraj.to_csv(index=False)
            st.download_button(
                "📄 CSV İndir", 
                csv, 
                f"metraj_{uploaded.name.replace('.dxf', '')}.csv",
                use_container_width=True
            )
        
        with col_dl2:
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                # Metraj sayfası
                df_metraj.to_excel(writer, sheet_name='Metraj', index=False)
                
                # Özet sayfası
                ozet_data = {
                    'Parametre': ['Dosya Adı', 'Kat Yüksekliği', 'Duvar Kalınlığı', 
                                 'Sıva Kalınlığı', 'Beton Oranı', 'Demir Oranı',
                                 'Toplam Pozitif', 'Toplam Çıkarma', 'Net Metraj'],
                    'Değer': [uploaded.name, f"{kat_yuksekligi} m", f"{duvar_kalinlik} m",
                             f"{siva_kalinlik} m", f"%{int(beton_orani*100)}", f"{demir_orani} kg/m³",
                             f"{toplam_pozitif:.2f}", f"{toplam_cikarma:.2f}", f"{net_metraj:.2f}"]
                }
                pd.DataFrame(ozet_data).to_excel(writer, sheet_name='Özet', index=False)
                
                # Kalem listesi sayfası
                kalem_data = []
                for k, v in tum_analizler.items():
                    if v['geometriler']:
                        kalem_data.append({
                            'Kalem': k,
                            'Katman Adı': v['katman_adi'],
                            'Obje Sayısı': v['obje_sayisi'],
                            'Toplam Uzunluk (m)': round(v['toplam_uzunluk'], 2),
                            'Toplam Alan (m²)': round(v['toplam_alan'], 2),
                            'Renk Kodu': v['renk']
                        })
                pd.DataFrame(kalem_data).to_excel(writer, sheet_name='Kalemler', index=False)
            
            st.download_button(
                "📊 Excel İndir (3 Sayfa)", 
                excel_buffer.getvalue(), 
                f"metraj_{uploaded.name.replace('.dxf', '')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    else:
        st.info("👈 Görüntülemek için kalem seçin")
    
    # Temizlik
    del doc
    os.remove(tmp_path)
    
except Exception as e:
    st.error(f"❌ Hata oluştu: {str(e)}")
    import traceback
    with st.expander("Detaylı Hata Bilgisi (Teknik)"):
        st.code(traceback.format_exc())
