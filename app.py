"""
Mimari Duvar Metraj Uygulaması v4.1 - Stabil Versiyon
Geliştirici: Barış Öker - Fi-le Yazılım 
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
        'renk': '#FF4B4B',
        'katmanlar': ['DUVAR', 'WALL', 'WALLS', 'DUWAR'],
        'tip': 'cizgi',
        'kalinlik': 2.0
    },
    'BETONARME': {
        'renk': '#4B9FFF',
        'katmanlar': ['BETON', 'BETONARME', 'CONCRETE', 'KIRIS', 'KOLON', 'BEAM', 'COLUMN'],
        'tip': 'cizgi',
        'kalinlik': 2.5
    },
    'SIVA': {
        'renk': '#4BFF88',
        'katmanlar': ['SIVA', 'SIVAMA', 'PLASTER', 'RENDER'],
        'tip': 'alan',
        'kalinlik': 1.5
    },
    'ZEMIN': {
        'renk': '#FFD700',
        'katmanlar': ['ZEMIN', 'FLOOR', 'YER', 'DOSEME', 'GROUND'],
        'tip': 'alan',
        'kalinlik': 2.0
    },
    'DEMIR': {
        'renk': '#9B4BFF',
        'katmanlar': ['DEMIR', 'DEMIR_HASIR', 'REBAR', 'CELIK', 'STEEL', 'IRON'],
        'tip': 'nokta',
        'kalinlik': 1.0
    },
    'PENCERE': {
        'renk': '#00FFFF',
        'katmanlar': ['PENCERE', 'WINDOW', 'CAM', 'WIN', 'PEN'],
        'tip': 'bosluk',
        'kalinlik': 1.5
    },
    'KAPI': {
        'renk': '#FF8C00',
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
                    if len(pts) < 2:
                        continue
                    noktalar = [(p[0]/birim_scale, p[1]/birim_scale) for p in pts]
                    
                    # Uzunluk hesapla
                    uzunluk = 0
                    for i in range(len(noktalar)-1):
                        x1, y1 = noktalar[i]
                        x2, y2 = noktalar[i+1]
                        uzunluk += math.sqrt((x2-x1)**2 + (y2-y1)**2)
                    
                    # Alan hesapla (kapalı ise)
                    alan = 0
                    is_closed = entity.closed
                    if is_closed and len(noktalar) > 2:
                        for i in range(len(noktalar)):
                            j = (i + 1) % len(noktalar)
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
    """Tüm kalemleri aynı figürde çizer."""
    if secili_kalemler is None:
        secili_kalemler = list(KALEM_RENKLERI.keys())
    
    fig, ax = plt.subplots(figsize=(14, 12), facecolor='#0e1117')
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
            elif geo['tip'] == 'polyline' and geo['noktalar']:
                xs, ys = zip(*geo['noktalar'])
                tum_x.extend(xs)
                tum_y.extend(ys)
            elif geo['tip'] in ['circle']:
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
                    
            elif geo['tip'] == 'circle':
                circle = plt.Circle((geo['x'], geo['y']), geo['r'], 
                                  color=renk, fill=False, lw=config['kalinlik'])
                ax.add_patch(circle)
    
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
                          lw=3, label=f"{kalem} ({analiz_sonuclari[kalem]['obje_sayisi']})")
            )
    
    if legend_elements:
        ax.legend(handles=legend_elements, loc='upper left', 
                 facecolor='#262730', edgecolor='white', 
                 labelcolor='white', fontsize=9)
    
    return fig

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("""
        <div class="profile-card">
            <img src="https://www.w3schools.com/howto/img_avatar.png" class="profile-img">
            <h4 style="color: white; margin: 0;">Admin</h4>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    # DOSYA YÜKLEME - BASİT VE STABİL
    uploaded = st.file_uploader("📁 DXF Dosyası", type=["dxf"])
    
    birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    
    st.divider()
    st.subheader("⚙️ Parametreler")
    kat_yuksekligi = st.number_input("Kat Yüksekliği (m)", value=2.85, step=0.01)
    duvar_kalinlik = st.number_input("Duvar Kalınlığı (m)", value=0.20, step=0.01)
    
    st.divider()
    if st.button("🚪 Çıkış", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# =============================================================================
# ANA UYGULAMA
# =============================================================================
st.title("🏗️ Çoklu Kalem Metraj Analizi")

if uploaded is None:
    st.info("👈 Lütfen sol menüden DXF dosyası yükleyin")
    st.stop()

# DXF İŞLEME
tmp_path = None
try:
    # Geçici dosya oluştur
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    
    st.success(f"✅ Dosya yüklendi: {uploaded.name}")
    
    # DXF oku
    doc = ezdxf.readfile(tmp_path)
    birim_carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
    
    # Analiz
    with st.spinner("🔍 Analiz ediliyor..."):
        tum_analizler = analiz_tum_kalemler(doc, birim_carpani)
    
    # Bulunan kalemler
    bulunan = [k for k, v in tum_analizler.items() if v['geometriler']]
    if bulunan:
        st.write(f"**{len(bulunan)} kalem bulundu:** {', '.join(bulunan)}")
    
    # Kalem seçimi
    st.sidebar.divider()
    st.sidebar.subheader("🎨 Katmanlar")
    
    secili_kalemler = []
    for kalem_adi, veri in tum_analizler.items():
        if not veri['geometriler']:
            continue
        if st.sidebar.checkbox(f"{kalem_adi} ({veri['obje_sayisi']})", 
                              value=True, key=f"chk_{kalem_adi}"):
            secili_kalemler.append(kalem_adi)
    
    # Görselleştirme
    if secili_kalemler:
        st.subheader("📐 Teknik Plan")
        fig = ciz_tum_kalemler(tum_analizler, secili_kalemler)
        st.pyplot(fig, use_container_width=True)
    
    # Metraj tablosu
    st.subheader("📊 Metrajlar")
    metraj_tablosu = []
    
    duvar_alan = 0
    
    for kalem_adi in secili_kalemler:
        veri = tum_analizler[kalem_adi]
        if not veri['geometriler']:
            continue
        
        if kalem_adi == 'DUVAR':
            alan = veri['toplam_uzunluk'] * kat_yuksekligi
            hacim = alan * duvar_kalinlik
            duvar_alan = alan
            
            metraj_tablosu.append({
                'Kalem': 'Duvar Örme',
                'Birim': 'm²',
                'Miktar': round(alan, 2),
                'Açıklama': f'Uzunluk: {veri["toplam_uzunluk"]:.2f}m'
            })
            
        elif kalem_adi == 'PENCERE':
            metraj_tablosu.append({
                'Kalem': 'Pencere Çıkarma',
                'Birim': 'm²',
                'Miktar': round(-veri['toplam_alan'], 2),
                'Açıklama': 'Duvaradan düşülür'
            })
            
        elif kalem_adi == 'KAPI':
            metraj_tablosu.append({
                'Kalem': 'Kapı Çıkarma',
                'Birim': 'm²',
                'Miktar': round(-veri['toplam_alan'], 2),
                'Açıklama': 'Duvaradan düşülür'
            })
    
    if metraj_tablosu:
        df = pd.DataFrame(metraj_tablosu)
        st.dataframe(df, use_container_width=True)
        
        # CSV indir
        csv = df.to_csv(index=False)
        st.download_button("📥 CSV İndir", csv, "metraj.csv")
    
    # Temizlik
    del doc
    
except Exception as e:
    st.error(f"❌ Hata: {str(e)}")
    import traceback
    st.code(traceback.format_exc())
    
finally:
    # Temizlik - her durumda çalışır
    if tmp_path and os.path.exists(tmp_path):
        try:
            os.remove(tmp_path)
        except:
            pass
