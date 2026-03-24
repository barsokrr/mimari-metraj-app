"""
Mimari Duvar Metraj Uygulaması
Geliştirici: Barış Öker - Fi-le Yazılım A.Ş.
Sürüm: 2.0 - Stabil
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

# CSS Stilleri
st.markdown("""
    <style>
    .profile-card {
        text-align: center;
        padding: 1rem;
        background-color: #262730;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    .profile-img {
        border-radius: 50%;
        width: 80px;
        height: 80px;
        border: 3px solid #FF4B4B;
        margin-bottom: 0.5rem;
    }
    .metric-box {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #FF4B4B;
    }
    </style>
""", unsafe_allow_html=True)

# =============================================================================
# YARDIMCI FONKSİYONLAR
# =============================================================================

def get_layers_from_dxf(doc):
    """DXF dosyasındaki tüm katmanları döndürür."""
    layers = set()
    for entity in doc.modelspace():
        if hasattr(entity.dxf, 'layer'):
            layers.add(entity.dxf.layer)
    return sorted(list(layers))

def calculate_wall_length(doc, target_layers, birim="cm"):
    """
    Belirtilen katmanlardaki LINE ve LWPOLYLINE uzunluklarını hesaplar.
    Çift çizgili duvarlar için toplam uzunluğu 2'ye böler (aks uzunluğu).
    """
    total_raw_length = 0.0
    processed_entities = 0
    
    # Birim çarpanı (metreye çevirmek için)
    birim_carpani = {
        "mm": 1000.0,
        "cm": 100.0,
        "m": 1.0
    }.get(birim, 100.0)
    
    msp = doc.modelspace()
    
    for entity in msp:
        entity_layer = getattr(entity.dxf, 'layer', '').upper()
        
        # Katman filtresi kontrolü
        if target_layers:
            # Virgülle ayrılmış katmanları kontrol et
            layer_match = False
            for target in target_layers:
                if target.upper().strip() in entity_layer:
                    layer_match = True
                    break
            if not layer_match:
                continue
        
        try:
            entity_type = entity.dxftype()
            
            # LINE objesi
            if entity_type == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                length = math.sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)
                total_raw_length += length
                processed_entities += 1
                
            # LWPOLYLINE objesi (kapalı veya açık)
            elif entity_type == "LWPOLYLINE":
                if hasattr(entity, 'get_points'):
                    points = list(entity.get_points('xy'))
                    if len(points) >= 2:
                        # Segment uzunluklarını topla
                        for i in range(len(points)-1):
                            x1, y1 = points[i][0], points[i][1]
                            x2, y2 = points[i+1][0], points[i+1][1]
                            segment = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                            total_raw_length += segment
                        processed_entities += 1
                        
            # Eski POLYLINE formatı (nadiren kullanılır ama destekleyelim)
            elif entity_type == "POLYLINE":
                vertices = []
                for v in entity.vertices:
                    vertices.append((v.dxf.location.x, v.dxf.location.y))
                
                if len(vertices) >= 2:
                    for i in range(len(vertices)-1):
                        x1, y1 = vertices[i]
                        x2, y2 = vertices[i+1]
                        segment = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                        total_raw_length += segment
                    processed_entities += 1
                    
        except Exception as e:
            continue
    
    # Çift çizgili duvar mantığı: Toplam uzunluk / 2 = Aks uzunluğu
    aks_uzunluk = total_raw_length / 2.0 if total_raw_length > 0 else 0.0
    
    # Metreye çevir
    aks_uzunluk_metre = aks_uzunluk / birim_carpani
    toplam_ham_metre = total_raw_length / birim_carpani
    
    return {
        'ham_uzunluk': toplam_ham_metre,
        'aks_uzunluk': aks_uzunluk_metre,
        'entity_sayisi': processed_entities
    }

def draw_wall_preview(doc, target_layers, wall_data):
    """Sadece duvar katmanlarını kırmızı ile vurgulayan plan görseli."""
    fig, ax = plt.subplots(figsize=(12, 10), facecolor='#0e1117')
    ax.set_facecolor('#0e1117')
    
    # Tüm entity'leri çiz (gri arka plan)
    for entity in doc.modelspace():
        try:
            color = "#333333"  # Koyu gri - diğer katmanlar
            linewidth = 0.5
            
            # Hedef katman kontrolü
            entity_layer = getattr(entity.dxf, 'layer', '').upper()
            is_target = False
            for target in target_layers:
                if target.upper().strip() in entity_layer:
                    color = "#FF4B4B"  # Kırmızı - duvarlar
                    linewidth = 2.0
                    is_target = True
                    break
            
            entity_type = entity.dxftype()
            
            if entity_type == "LINE":
                start = entity.dxf.start
                end = entity.dxf.end
                ax.plot([start[0], end[0]], [start[1], end[1]], 
                       color=color, linewidth=linewidth, alpha=0.8)
                       
            elif entity_type == "LWPOLYLINE":
                if hasattr(entity, 'get_points'):
                    pts = list(entity.get_points('xy'))
                    if len(pts) >= 2:
                        xs = [p[0] for p in pts]
                        ys = [p[1] for p in pts]
                        # Kapalıysa ilk noktayı sona ekle
                        if entity.closed:
                            xs.append(xs[0])
                            ys.append(ys[0])
                        ax.plot(xs, ys, color=color, linewidth=linewidth, alpha=0.8)
                        
        except Exception as e:
            continue
    
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(f"Duvar Analizi: {wall_data['entity_sayisi']} obje | "
                f"Aks: {wall_data['aks_uzunluk']:.2f}m", 
                color='white', fontsize=12, pad=20)
    
    plt.tight_layout()
    return fig

# =============================================================================
# GİRİŞ EKRANI
# =============================================================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🏗️ Duvar Metraj Sistemi - Giriş")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login"):
            username = st.text_input("Kullanıcı Adı", value="admin")
            password = st.text_input("Şifre", type="password", value="1234")
            login_btn = st.form_submit_button("Giriş Yap", use_container_width=True)
            
            if login_btn:
                if username == "admin" and password == "1234":
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("❌ Hatalı giriş bilgileri!")
    
    st.markdown("---")
    st.info("💡 **Demo Hesap:** Kullanıcı: `admin` | Şifre: `1234`")

# =============================================================================
# ANA UYGULAMA
# =============================================================================
else:
    # SIDEBAR - PROFİL
    with st.sidebar:
        st.markdown("""
            <div class="profile-card">
                <img src="https://www.w3schools.com/howto/img_avatar.png" class="profile-img">
                <h4 style="color: white; margin: 0;">Barış Öker</h4>
                <p style="color: #888; margin: 0; font-size: 0.9em;">Fi-le Yazılım A.Ş.</p>
            </div>
        """, unsafe_allow_html=True)
        
        st.divider()
        
        # DOSYA YÜKLEME
        uploaded = st.file_uploader("📁 DXF Dosyası", type=["dxf"])
        
        # KATMAN SEÇİMİ (Dosya yüklenince aktif olur)
        katman_secimi = st.text_input(
            "🧱 Duvar Katman(ları)", 
            value="DUVAR",
            help="Virgülle ayrılmış: DUVAR, WALL, A-WALL"
        )
        
        # PARAMETRELER
        kat_yuksekligi = st.number_input(
            "📏 Kat Yüksekliği (m)", 
            min_value=1.0, 
            max_value=20.0, 
            value=2.85, 
            step=0.01
        )
        
        birim = st.selectbox(
            "📐 Çizim Birimi",
            options=["cm", "mm", "m"],
            index=0,
            help="DXF'in çizildiği birim"
        )
        
        st.divider()
        
        # ÇIKIŞ
        if st.button("🚪 Çıkış Yap", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # ANA EKRAN
    st.title("🏗️ Duvar Metraj Analizi")
    
    if uploaded is not None:
        # DXF'i işle
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
                tmp.write(uploaded.getvalue())
                tmp_path = tmp.name
            
            # DXF'i oku
            doc = ezdxf.readfile(tmp_path)
            
            # Katmanları göster (bilgi amaçlı)
            tum_katmanlar = get_layers_from_dxf(doc)
            with st.expander(f"📋 DXF'teki Katmanlar ({len(tum_katmanlar)} adet)"):
                st.write(", ".join(tum_katmanlar))
            
            # Hedef katmanları ayır
            hedef_katmanlar = [k.strip() for k in katmanlar_secimi.split(",") if k.strip()]
            
            # METRAJ HESAPLA
            wall_data = calculate_wall_length(doc, hedef_katmanlar, birim)
            
            if wall_data['entity_sayisi'] == 0:
                st.warning(f"⚠️ '{katman_secimi}' katmanında duvar bulunamadı!")
                st.info(f"💡 Mevcut katmanlar: {', '.join(tum_katmanlar[:10])}...")
            else:
                # Alan hesapla
                toplam_alan = wall_data['aks_uzunluk'] * kat_yuksekligi
                
                # SONUÇLAR
                st.subheader("📊 Hesaplama Sonuçları")
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                        <div class="metric-box">
                            <h4>🧱 Ham Uzunluk</h4>
                            <h2>{wall_data['ham_uzunluk']:.2f} m</h2>
                            <small>Çift çizgiler toplamı</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                        <div class="metric-box">
                            <h4>📐 Aks Uzunluğu</h4>
                            <h2>{wall_data['aks_uzunluk']:.2f} m</h2>
                            <small>Ham / 2</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                        <div class="metric-box">
                            <h4>📏 Kat Yüksekliği</h4>
                            <h2>{kat_yuksekligi:.2f} m</h2>
                            <small>Girdiğiniz değer</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    st.markdown(f"""
                        <div class="metric-box">
                            <h4>🏠 Toplam Alan</h4>
                            <h2 style="color: #FF4B4B;">{toplam_alan:.2f} m²</h2>
                            <small>Aks × Yükseklik</small>
                        </div>
                    """, unsafe_allow_html=True)
                
                # GÖRSELLEŞTİRME
                st.divider()
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("🗺️ Plan Görünümü")
                    fig = draw_wall_preview(doc, hedef_katmanlar, wall_data)
                    st.pyplot(fig, use_container_width=True)
                
                with col2:
                    st.subheader("📋 Rapor")
                    
                    rapor_data = {
                        "Parametre": [
                            "DXF Dosyası",
                            "Duvar Katmanı",
                            "Çizim Birimi",
                            "İşlenen Objeler",
                            "Ham Uzunluk",
                            "Aks Uzunluğu",
                            "Kat Yüksekliği",
                            "Toplam Duvar Alanı"
                        ],
                        "Değer": [
                            uploaded.name,
                            katman_secimi,
                            birim,
                            f"{wall_data['entity_sayisi']} adet",
                            f"{wall_data['ham_uzunluk']:.2f} m",
                            f"{wall_data['aks_uzunluk']:.2f} m",
                            f"{kat_yuksekligi:.2f} m",
                            f"{toplam_alan:.2f} m²"
                        ]
                    }
                    
                    df_rapor = pd.DataFrame(rapor_data)
                    st.table(df_rapor)
                    
                    # CSV İNDİR
                    csv_data = {
                        "Proje": [uploaded.name],
                        "Katman": [katman_secimi],
                        "Birim": [birim],
                        "Aks_Uzunluk_m": [round(wall_data['aks_uzunluk'], 2)],
                        "Kat_Yuksekligi_m": [round(kat_yuksekligi, 2)],
                        "Toplam_Alan_m2": [round(toplam_alan, 2)]
                    }
                    df_export = pd.DataFrame(csv_data)
                    csv = df_export.to_csv(index=False).encode('utf-8')
                    
                    st.download_button(
                        "📥 CSV İndir",
                        data=csv,
                        file_name=f"duvar_metraj_{uploaded.name.replace('.dxf', '')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                    
                    # TXT RAPOR
                    txt_rapor = f"""DUVAR METRAJ RAPORU
==================
Proje: {uploaded.name}
Tarih: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}

PARAMETRELER
-----------
Duvar Katmanı: {katman_secimi}
Çizim Birimi: {birim}
Kat Yüksekliği: {kat_yuksekligi} m

SONUÇLAR
--------
İşlenen Objeler: {wall_data['entity_sayisi']} adet
Ham Toplam Uzunluk: {wall_data['ham_uzunluk']:.2f} m
Aks Uzunluğu (Ham/2): {wall_data['aks_uzunluk']:.2f} m
Toplam Duvar Alanı: {toplam_alan:.2f} m²

Hesaplayan: Barış Öker
Firma: Fi-le Yazılım A.Ş.
"""
                    st.download_button(
                        "📄 TXT Rapor İndir",
                        data=txt_rapor,
                        file_name=f"rapor_{uploaded.name.replace('.dxf', '.txt')}",
                        mime="text/plain",
                        use_container_width=True
                    )
            
            # Temizlik
            doc = None
            try:
                os.remove(tmp_path)
            except:
                pass
                
        except Exception as e:
            st.error(f"❌ DXF işleme hatası: {str(e)}")
            st.info("💡 Olası nedenler: Bozuk DXF, uyumsuz versiyon veya şifreli dosya")
    else:
        st.info("👈 Lütfen sol menüden bir DXF dosyası yükleyin")
        
        # Örnek açıklama
        st.markdown("""
        <div style="background-color: #e8f4f8; padding: 1.5rem; border-radius: 10px; margin-top: 2rem;">
            <h4>💡 Nasıl Kullanılır?</h4>
            <ol>
                <li><strong>DXF Yükleyin:</strong> AutoCAD'de hazırladığınız mimari planı seçin</li>
                <li><strong>Katman Belirtin:</strong> Duvar çizgilerinin olduğu katman adını yazın (örn: "DUVAR")</li>
                <li><strong>Birim Seçin:</strong> Çizimin hangi birimde olduğunu belirtin (cm, mm, m)</li>
                <li><strong>Kat Yüksekliği:</strong> Metraj için kat yüksekliğini girin</li>
                <li><strong>Hesapla:</strong> Sistem otomatik olarak:
                    <ul>
                        <li>Tüm çizgi uzunluklarını toplar</li>
                        <li>2'ye bölerek aks uzunluğunu bulur (çift çizgili duvarlar için)</li>
                        <li>Kat yüksekliği ile çarparak m² hesaplar</li>
                    </ul>
                </li>
            </ol>
        </div>
        """, unsafe_allow_html=True)
