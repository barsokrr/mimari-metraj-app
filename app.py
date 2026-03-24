"""
Mimari Duvar Metraj Uygulaması
Geliştirici: Barış Öker - Fi-le Yazılım A.Ş.
Sürüm: 3.1 - Stabil & Minimal (Revize)
"""
import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os

# =============================================================================
# SAYFA KONFİGÜRASYONU
# =============================================================================
st.set_page_config(page_title="Duvar Metraj Pro", layout="wide")

st.markdown("""
    <style>
    .profile-card { text-align: center; padding: 1rem; background-color: #262730; border-radius: 10px; margin-bottom: 1rem; }
    .profile-img { border-radius: 50%; width: 80px; height: 80px; border: 3px solid #FF4B4B; margin-bottom: 0.5rem; }
    .metric-box { background-color: #f0f2f6; padding: 1.5rem; border-radius: 10px; border-left: 5px solid #FF4B4B; text-align: center; }
    .big-number { font-size: 2rem; font-weight: bold; color: #FF4B4B; }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# GİRİŞ EKRANI
# =============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ Duvar Metraj Sistemi")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            username = st.text_input("Kullanıcı Adı", value="admin")
            password = st.text_input("Şifre", type="password", value="1234")
            if st.form_submit_button("Giriş Yap", use_container_width=True):
                if username == "admin" and password == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Hatalı giriş!")
    st.stop()

# =============================================================================
# SIDEBAR
# =============================================================================
with st.sidebar:
    st.markdown("""
        <div class="profile-card">
            <img src="https://www.w3schools.com/howto/img_avatar.png" class="profile-img">
            <h4 style="color: white; margin: 0;">Barış Öker</h4>
            <p style="color: #888; margin: 0; font-size: 0.9em;">Fi-le Yazılım A.Ş.</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.divider()
    
    uploaded = st.file_uploader("📁 DXF Dosyası", type=["dxf"])
    katman_secimi = st.text_input("🧱 Duvar Katmanı", value="DUVAR")
    kat_yuksekligi = st.number_input("📏 Kat Yüksekliği (m)", value=2.85, step=0.01)
    birim = st.selectbox("📐 Çizim Birimi", ["cm", "mm", "m"], index=0)
    
    st.divider()
    if st.button("🚪 Çıkış Yap", use_container_width=True):
        st.session_state.logged_in = False
        st.rerun()

# =============================================================================
# ANA UYGULAMA
# =============================================================================
st.title("🏗️ Duvar Metraj Analizi")

if uploaded is None:
    st.info("👈 Lütfen sol menüden DXF dosyası yükleyin")
    st.stop()

# DXF İŞLEME
try:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    
    doc = ezdxf.readfile(tmp_path)
    
    # HESAPLAMA
    birim_carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
    hedef_katman = katman_secimi.strip().upper()
    
    total_length = 0.0
    entity_count = 0
    
    for entity in doc.modelspace():
        try:
            layer = getattr(entity.dxf, 'layer', '').upper()
            if hedef_katman not in layer:
                continue
                
            dtype = entity.dxftype()
            
            if dtype == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                total_length += math.sqrt((e[0]-s[0])**2 + (e[1]-s[1])**2)
                entity_count += 1
                
            elif dtype == "LWPOLYLINE":
                pts = list(entity.get_points('xy'))
                for i in range(len(pts)-1):
                    x1, y1 = pts[i][0], pts[i][1]
                    x2, y2 = pts[i+1][0], pts[i+1][1]
                    total_length += math.sqrt((x2-x1)**2 + (y2-y1)**2)
                entity_count += 1
                
        except:
            continue
    
    # SONUÇLAR (Geliştirilmiş Görünüm)
    ham_uzunluk = total_length / birim_carpani
    aks_uzunluk = ham_uzunluk / 2.0
    toplam_alan = aks_uzunluk * kat_yuksekligi
    
    st.success(f"✅ {entity_count} duvar çizgisi işlendi | {uploaded.name}")
    
    # METRİK KARTLARI
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
            <div class="metric-box">
                <p>Ham Uzunluk</p>
                <p class="big-number">{ham_uzunluk:,.2f}</p>
                <small>m</small>
            </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
            <div class="metric-box">
                <p>🔥 Aks Uzunluğu</p>
                <p class="big-number">{aks_uzunluk:,.2f}</p>
                <small>m (Ham/2)</small>
            </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
            <div class="metric-box">
                <p>Kat Yüksekliği</p>
                <p class="big-number">{kat_yuksekligi:,.2f}</p>
                <small>m</small>
            </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
            <div class="metric-box">
                <p>🎯 Toplam Alan</p>
                <p class="big-number">{toplam_alan:,.2f}</p>
                <small>m²</small>
            </div>
        """, unsafe_allow_html=True)
    
    # GÖRSELLEŞTİRME
    st.divider()
    fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
    ax.set_facecolor('#0e1117')
    
    for entity in doc.modelspace():
        try:
            color = "#333333"
            lw = 0.5
            if hedef_katman in getattr(entity.dxf, 'layer', '').upper():
                color = "#FF4B4B"
                lw = 2.0
            
            if entity.dxftype() == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                ax.plot([s[0], e[0]], [s[1], e[1]], color=color, lw=lw)
            elif entity.dxftype() == "LWPOLYLINE":
                pts = list(entity.get_points('xy'))
                xs, ys = zip(*pts)
                ax.plot(xs, ys, color=color, lw=lw)
        except:
            continue
    
    ax.set_aspect('equal')
    ax.axis('off')
    st.pyplot(fig, use_container_width=True)
    
    # DETAYLI RAPOR
    st.divider()
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📋 Hesaplama Detayı")
        
        detay_data = {
            'Parametre': [
                'DXF Dosyası',
                'Duvar Katmanı',
                'Çizim Birimi',
                'İşlenen Çizgi',
                'Ham Uzunluk',
                'Aks Uzunluğu (÷2)',
                'Kat Yüksekliği',
                'Toplam Duvar Alanı'
            ],
            'Değer': [
                uploaded.name,
                katman_secimi,
                birim,
                f"{entity_count} adet",
                f"{ham_uzunluk:,.2f} m",
                f"{aks_uzunluk:,.2f} m",
                f"{kat_yuksekligi} m",
                f"{toplam_alan:,.2f} m²"
            ]
        }
        
        st.table(pd.DataFrame(detay_data))
    
    with col2:
        st.subheader("💾 Rapor İndir")
        
        # CSV
        csv = f"""Parametre,Değer
Proje,{uploaded.name}
Katman,{katman_secimi}
Birim,{birim}
Entity Sayisi,{entity_count}
Ham Uzunluk (m),{ham_uzunluk:.2f}
Aks Uzunlugu (m),{aks_uzunluk:.2f}
Kat Yuksekligi (m),{kat_yuksekligi}
Duvar Alani (m2),{toplam_alan:.2f}
"""
        
        st.download_button("📥 CSV İndir", csv, 
                          f"metraj_{uploaded.name.replace('.dxf', '')}.csv",
                          use_container_width=True)
        
        # TXT
        txt = f"""DUVAR METRAJ RAPORU
====================
Proje: {uploaded.name}
Tarih: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

PARAMETRELER
-----------
Duvar Katmani: {katman_secimi}
Cizim Birimi: {birim}
Kat Yuksekligi: {kat_yuksekligi} m

SONUCLAR
--------
Islenen Cizgi: {entity_count} adet
Ham Uzunluk: {ham_uzunluk:.2f} m
Aks Uzunlugu: {aks_uzunluk:.2f} m
Toplam Duvar Alani: {toplam_alan:.2f} m2

Hesaplayan: Baris Oker
Firma: Fi-le Yazilim A.S.
"""
        
        st.download_button("📄 TXT Rapor", txt,
                          f"rapor_{uploaded.name.replace('.dxf', '.txt')}",
                          use_container_width=True)
        
        st.info(f"""
        **Formül:**
        Aks = {ham_uzunluk:.2f} ÷ 2 = **{aks_uzunluk:.2f} m**
        
        Alan = {aks_uzunluk:.2f} × {kat_yuksekligi} = **{toplam_alan:.2f} m²**
        """)
    
    # TEMİZLİK
    del doc
    try:
        os.remove(tmp_path)
    except:
        pass
    
except Exception as e:
    st.error(f"❌ Hata: {str(e)}")
    st.info("💡 Kontrol edin: DXF bozuk olabilir veya katman adı yanlış")
