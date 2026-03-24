"""
Mimari Metraj Uygulaması
Geliştirici: Barış Öker - Fi-le Yazılım A.Ş.
Kütüphaneler: Streamlit, ezdxf, matplotlib, numpy
"""

import streamlit as st
import ezdxf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Arc as MatplotlibArc
import numpy as np
from pathlib import Path
import math

# =============================================================================
# SAYFA KONFİGÜRASYONU
# =============================================================================
st.set_page_config(
    page_title="Mimari Metraj Sistemi",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS Stilleri
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .profile-card {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 2rem;
    }
    .success-box {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #28a745;
    }
    .error-box {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 5px;
        border-left: 5px solid #dc3545;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# PROFİL BİLGİLERİ (SOL MENÜ)
# =============================================================================
def render_sidebar_profile():
    """Sol menüde profil bilgilerini gösterir."""
    with st.sidebar:
        st.markdown("""
        <div class="profile-card">
            <h3>👤 Profil</h3>
            <hr>
            <p><strong>İsim:</strong><br>Barış Öker</p>
            <p><strong>Firma:</strong><br>Fi-le Yazılım A.Ş.</p>
            <p><strong>Uygulama:</strong><br>Mimari Metraj Sistemi v1.0</p>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# DXF YÜKLEME VE KATMAN LİSTESİ
# =============================================================================
@st.cache_data
def load_dxf_file(file_content):
    """
    DXF dosyasını yükler ve katman listesini çıkarır.
    ezdxf 1.1+ uyumlu, stabil yükleme.
    """
    try:
        # BytesIO'dan geçici dosya oluştur
        import tempfile
        import os
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.dxf') as tmp_file:
            tmp_file.write(file_content)
            tmp_path = tmp_file.name
        
        # DXF dosyasını yükle (herhangi bir version)
        try:
            doc = ezdxf.readfile(tmp_path)
        except ezdxf.DXFError:
            # Eğer hata verirse recover modunda dene
            doc = ezdxf.recover.readfile(tmp_path)
        
        # Tüm katmanları topla
        layers = set()
        for entity in doc.modelspace():
            if hasattr(entity, 'dxf') and hasattr(entity.dxf, 'layer'):
                layers.add(entity.dxf.layer)
        
        # Temizlik
        os.unlink(tmp_path)
        
        return doc, sorted(list(layers))
    
    except Exception as e:
        st.error(f"DXF yükleme hatası: {str(e)}")
        return None, []

# =============================================================================
# KOORDİNAT HESAPLAMA (Manuel - BBOX hatalarını önler)
# =============================================================================
def get_entity_bounds(entity):
    """
    Entity'nin sınırlarını manuel hesaplar.
    ezdxf 1.1+'da get_bbox() hatalarını önlemek için.
    """
    points = []
    
    try:
        entity_type = entity.dxftype()
        
        if entity_type == 'LINE':
            points = [entity.dxf.start, entity.dxf.end]
            
        elif entity_type in ['LWPOLYLINE', 'POLYLINE']:
            # Tüm vertex'leri al
            if hasattr(entity, 'get_points'):
                pts = entity.get_points('xy')
                points = [(p[0], p[1]) for p in pts]
            elif hasattr(entity, 'vertices'):
                for v in entity.vertices:
                    points.append((v.dxf.location.x, v.dxf.location.y))
                    
        elif entity_type == 'ARC':
            # Yay'ın sınırlarını hesapla
            center = entity.dxf.center
            radius = entity.dxf.radius
            start_angle = math.radians(entity.dxf.start_angle)
            end_angle = math.radians(entity.dxf.end_angle)
            
            # Yay üzerinde örnek noktalar
            angles = np.linspace(start_angle, end_angle, 20)
            for angle in angles:
                x = center[0] + radius * math.cos(angle)
                y = center[1] + radius * math.sin(angle)
                points.append((x, y))
                
        elif entity_type == 'CIRCLE':
            center = entity.dxf.center
            radius = entity.dxf.radius
            points = [
                (center[0] - radius, center[1] - radius),
                (center[0] + radius, center[1] + radius)
            ]
            
        elif entity_type == 'TEXT' or entity_type == 'MTEXT':
            if hasattr(entity.dxf, 'insert'):
                points = [entity.dxf.insert]
                
    except Exception as e:
        pass
    
    if not points:
        return None
    
    x_coords = [p[0] for p in points]
    y_coords = [p[1] for p in points]
    
    return {
        'min_x': min(x_coords),
        'max_x': max(x_coords),
        'min_y': min(y_coords),
        'max_y': max(y_coords)
    }

# =============================================================================
# DUVAR METRAJI HESAPLAMA
# =============================================================================
def calculate_wall_metrics(doc, layer_name, floor_height=3.0):
    """
    Seçilen katmandaki LINE ve LWPOLYLINE uzunluklarını hesaplar.
    Toplam uzunluğu 2'ye bölerek aks uzunluğunu bulur, kat yüksekliği ile çarpar.
    """
    total_length = 0.0
    entity_count = 0
    
    for entity in doc.modelspace():
        if hasattr(entity, 'dxf') and entity.dxf.layer == layer_name:
            entity_type = entity.dxftype()
            
            try:
                if entity_type == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    length = math.sqrt((end[0]-start[0])**2 + (end[1]-start[1])**2)
                    total_length += length
                    entity_count += 1
                    
                elif entity_type == 'LWPOLYLINE':
                    # Polyline uzunluğu
                    if hasattr(entity, 'get_points'):
                        pts = entity.get_points('xy')
                        for i in range(len(pts)-1):
                            x1, y1 = pts[i][0], pts[i][1]
                            x2, y2 = pts[i+1][0], pts[i+1][1]
                            length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
                            total_length += length
                        entity_count += 1
                        
            except Exception as e:
                continue
    
    # Aks uzunluğu = Toplam uzunluk / 2 (çift çizgili duvarlar için)
    axis_length = total_length / 2 if total_length > 0 else 0
    
    # Duvar alanı = Aks uzunluğu × Kat yüksekliği
    wall_area = axis_length * floor_height
    
    return {
        'total_length': total_length,
        'axis_length': axis_length,
        'wall_area': wall_area,
        'entity_count': entity_count
    }

# =============================================================================
# KAPI SAYIMI (ARC OBJELERI)
# =============================================================================
def count_doors(doc):
    """
    Modelspacedeki tüm ARC objelerini sayar (her ARC bir kapı açılışı).
    """
    arc_count = 0
    arc_details = []
    
    for entity in doc.modelspace():
        if entity.dxftype() == 'ARC':
            try:
                arc_count += 1
                arc_details.append({
                    'center': entity.dxf.center,
                    'radius': entity.dxf.radius,
                    'start_angle': entity.dxf.start_angle,
                    'end_angle': entity.dxf.end_angle
                })
            except Exception as e:
                continue
    
    return arc_count, arc_details

# =============================================================================
# ZEMIN METRAJI (KAPALI LWPOLYLINE ALANLARI)
# =============================================================================
def calculate_floor_area(doc, layer_name):
    """
    Seçilen katmandaki kapalı LWPOLYLINE objelerinin alanını hesaplar.
    Shoelace algoritması kullanır.
    """
    total_area = 0.0
    room_count = 0
    room_areas = []
    
    for entity in doc.modelspace():
        if hasattr(entity, 'dxf') and entity.dxf.layer == layer_name:
            if entity.dxftype() == 'LWPOLYLINE':
                try:
                    # Kapalı polyline kontrolü
                    is_closed = False
                    if hasattr(entity.dxf, 'flags'):
                        is_closed = bool(entity.dxf.flags & 1)
                    elif hasattr(entity, 'closed'):
                        is_closed = entity.closed
                    elif hasattr(entity.dxf, 'closed'):
                        is_closed = entity.dxf.closed
                    
                    # Noktaları al
                    if hasattr(entity, 'get_points'):
                        pts = entity.get_points('xy')
                        
                        # Alan hesaplama (Shoelace formülü)
                        area = 0.0
                        n = len(pts)
                        for i in range(n):
                            j = (i + 1) % n
                            area += pts[i][0] * pts[j][1]
                            area -= pts[j][0] * pts[i][1]
                        area = abs(area) / 2.0
                        
                        if area > 0:
                            total_area += area
                            room_count += 1
                            room_areas.append({
                                'area': area,
                                'is_closed': is_closed,
                                'vertices': len(pts)
                            })
                            
                except Exception as e:
                    continue
    
    return {
        'total_area': total_area,
        'room_count': room_count,
        'room_details': room_areas
    }

# =============================================================================
# SHOELACE ALGORITMASI (Yedek alan hesaplama)
# =============================================================================
def shoelace_area(points):
    """Shoelace formülü ile poligon alanı hesaplar."""
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0

# =============================================================================
# MATPLOTLIB GÖRSELLEŞTİRME
# =============================================================================
def create_dxf_preview(doc, wall_layer=None, floor_layer=None, highlight_arcs=True):
    """
    DXF planının matplotlib önizlemesini oluşturur.
    """
    fig, ax = plt.subplots(figsize=(12, 10))
    
    all_x = []
    all_y = []
    
    # Renk haritası
    colors = {
        'wall': '#FF6B6B',      # Kırmızı tonu - duvarlar
        'floor': '#4ECDC4',     # Turkuaz - zeminler
        'arc': '#FFE66D',       # Sarı - kapılar (ARC)
        'other': '#95A5A6'      # Gri - diğer
    }
    
    arc_count = 0
    
    for entity in doc.modelspace():
        try:
            entity_type = entity.dxftype()
            layer = getattr(entity.dxf, 'layer', '0')
            
            # Renk belirleme
            color = colors['other']
            linewidth = 0.8
            alpha = 0.6
            
            if layer == wall_layer:
                color = colors['wall']
                linewidth = 1.5
                alpha = 0.9
            elif layer == floor_layer:
                color = colors['floor']
                linewidth = 2.0
                alpha = 0.7
            elif entity_type == 'ARC' and highlight_arcs:
                color = colors['arc']
                linewidth = 2.5
                alpha = 1.0
            
            # Çizim
            if entity_type == 'LINE':
                start = entity.dxf.start
                end = entity.dxf.end
                ax.plot([start[0], end[0]], [start[1], end[1]], 
                       color=color, linewidth=linewidth, alpha=alpha)
                all_x.extend([start[0], end[0]])
                all_y.extend([start[1], end[1]])
                
            elif entity_type == 'LWPOLYLINE':
                if hasattr(entity, 'get_points'):
                    pts = entity.get_points('xy')
                    x = [p[0] for p in pts]
                    y = [p[1] for p in pts]
                    
                    # Kapalıysa dolgu, değilse çizgi
                    is_closed = False
                    if hasattr(entity.dxf, 'flags'):
                        is_closed = bool(entity.dxf.flags & 1)
                    
                    if is_closed and layer == floor_layer:
                        ax.fill(x, y, color=color, alpha=0.3)
                    else:
                        ax.plot(x + [x[0]] if is_closed else x, 
                               y + [y[0]] if is_closed else y, 
                               color=color, linewidth=linewidth, alpha=alpha)
                    
                    all_x.extend(x)
                    all_y.extend(y)
                    
            elif entity_type == 'ARC' and highlight_arcs:
                center = entity.dxf.center
                radius = entity.dxf.radius
                start_angle = entity.dxf.start_angle
                end_angle = entity.dxf.end_angle
                
                # Yay çizimi
                arc_angles = np.linspace(
                    np.radians(start_angle), 
                    np.radians(end_angle), 
                    50
                )
                x = center[0] + radius * np.cos(arc_angles)
                y = center[1] + radius * np.sin(arc_angles)
                ax.plot(x, y, color=color, linewidth=linewidth, alpha=alpha)
                
                # Kapı sembolü (küçük daire)
                door_circle = plt.Circle(
                    center, radius*0.1, 
                    color='#FF4757', fill=True, alpha=0.8
                )
                ax.add_patch(door_circle)
                
                arc_count += 1
                all_x.extend([center[0] - radius, center[0] + radius])
                all_y.extend([center[1] - radius, center[1] + radius])
                
        except Exception as e:
            continue
    
    # Görünüm ayarları
    if all_x and all_y:
        margin = 0.1
        x_range = max(all_x) - min(all_x)
        y_range = max(all_y) - min(all_y)
        ax.set_xlim(min(all_x) - margin*x_range, max(all_x) + margin*x_range)
        ax.set_ylim(min(all_y) - margin*y_range, max(all_y) + margin*y_range)
    
    ax.set_aspect('equal')
    ax.grid(True, alpha=0.3)
    ax.set_title('DXF Plan Önizlemesi', fontsize=14, fontweight='bold')
    ax.set_xlabel('X Koordinatı (m)', fontsize=10)
    ax.set_ylabel('Y Koordinatı (m)', fontsize=10)
    
    # Legend
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=colors['wall'], lw=2, label=f'Duvar Katmanı: {wall_layer}'),
        Line2D([0], [0], color=colors['floor'], lw=2, label=f'Zemin Katmanı: {floor_layer}'),
        Line2D([0], [0], color=colors['arc'], lw=3, label=f'Kapılar (ARC): {arc_count} adet')
    ]
    ax.legend(handles=legend_elements, loc='upper right', fontsize=9)
    
    plt.tight_layout()
    return fig

# =============================================================================
# ANA UYGULAMA
# =============================================================================
def main():
    # Profil render
    render_sidebar_profile()
    
    # Başlık
    st.markdown('<h1 class="main-header">🏗️ Mimari Metraj Sistemi</h1>', 
                unsafe_allow_html=True)
    
    # DXF Yükleme Bölümü
    st.subheader("📁 Proje Yükleme")
    uploaded_file = st.file_uploader(
        "DXF dosyasını seçin (AutoCAD .dxf)",
        type=['dxf'],
        help="Mimari planınızın DXF formatında kaydedilmiş olması gerekir."
    )
    
    if uploaded_file is not None:
        # Dosyayı oku
        file_content = uploaded_file.getvalue()
        
        # DXF Yükle
        with st.spinner('DXF dosyası analiz ediliyor...'):
            doc, layers = load_dxf_file(file_content)
        
        if doc is None:
            st.markdown("""
            <div class="error-box">
                <strong>Hata!</strong> DXF dosyası okunamadı. 
                Lütfen dosyanın bozuk olmadığını kontrol edin.
            </div>
            """, unsafe_allow_html=True)
            return
        
        # Başarı mesajı
        st.markdown(f"""
        <div class="success-box">
            <strong>Başarılı!</strong> {uploaded_file.name} yüklendi. 
            Toplam <strong>{len(layers)}</strong> katman bulundu.
        </div>
        """, unsafe_allow_html=True)
        
        # Katman Seçimleri
        st.subheader("🔧 Katman Seçimleri")
        
        col1, col2 = st.columns(2)
        
        with col1:
            wall_layer = st.selectbox(
                "🧱 Duvar Katmanını Seçin:",
                options=layers,
                index=0 if layers else None,
                help="Duvar çizgilerinin bulunduğu katman (LINE ve LWPOLYLINE)"
            )
            
            floor_height = st.number_input(
                "📏 Kat Yüksekliği (m):",
                min_value=2.0,
                max_value=10.0,
                value=3.0,
                step=0.1,
                help="Standart kat yüksekliği (genellikle 2.8-3.2m)"
            )
        
        with col2:
            floor_layer = st.selectbox(
                "🏠 Zemin/Alan Katmanını Seçin:",
                options=layers,
                index=min(1, len(layers)-1) if len(layers) > 1 else 0,
                help="Kapalı alanların (odalar) bulunduğu katman"
            )
        
        # Hesaplama Butonu
        st.markdown("---")
        
        if st.button("🚀 Metraj Hesaplamasını Başlat", type="primary", use_container_width=True):
            
            with st.spinner('Hesaplamalar yapılıyor...'):
                
                # 1. Duvar Metrajı
                wall_results = calculate_wall_metrics(doc, wall_layer, floor_height)
                
                # 2. Kapı Sayımı (ARC objeleri)
                door_count, door_details = count_doors(doc)
                
                # 3. Zemin Metrajı
                floor_results = calculate_floor_area(doc, floor_layer)
                
                # Sonuçları Göster
                st.subheader("📊 Metraj Sonuçları")
                
                # Metrik Kartlar
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>🧱 Duvar Alanı</h4>
                        <h2>{wall_results['wall_area']:.2f} m²</h2>
                        <small>Aks: {wall_results['axis_length']:.2f}m × Yükseklik: {floor_height}m</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>🚪 Kapı Sayısı</h4>
                        <h2>{door_count} adet</h2>
                        <small>Toplam ARC objesi sayısı</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col3:
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>🏠 Zemin Alanı</h4>
                        <h2>{floor_results['total_area']:.2f} m²</h2>
                        <small>{floor_results['room_count']} kapalı alan</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col4:
                    hacim = wall_results['wall_area'] * 0.2  # Kabaca duvar hacmi
                    st.markdown(f"""
                    <div class="metric-card">
                        <h4>📦 Tahmini Hacim</h4>
                        <h2>{hacim:.2f} m³</h2>
                        <small>Duvar hacmi (kabaca)</small>
                    </div>
                    """, unsafe_allow_html=True)
                
                # Detaylı Tablolar
                st.markdown("---")
                
                tab1, tab2, tab3 = st.tabs(["🧱 Duvar Detayları", "🚪 Kapı Listesi", "🏠 Zemin Detayları"])
                
                with tab1:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Toplam Çizgi Uzunluğu", f"{wall_results['total_length']:.2f} m")
                        st.metric("Aks Uzunluğu (/2)", f"{wall_results['axis_length']:.2f} m")
                    with col2:
                        st.metric("İşlenen Entity Sayısı", f"{wall_results['entity_count']}")
                        st.metric("Kat Yüksekliği", f"{floor_height} m")
                
                with tab2:
                    st.write(f"**Toplam Kapı (ARC) Sayısı:** {door_count}")
                    if door_details:
                        door_df = [{
                            'No': i+1,
                            'Merkez X': d['center'][0],
                            'Merkez Y': d['center'][1],
                            'Yarıçap (m)': d['radius'],
                            'Başlangıç Açı': d['start_angle'],
                            'Bitiş Açı': d['end_angle']
                        } for i, d in enumerate(door_details[:20])]  # İlk 20
                        st.dataframe(door_df, use_container_width=True)
                        if len(door_details) > 20:
                            st.info(f"... ve {len(door_details)-20} adet daha")
                
                with tab3:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Toplam Zemin Alanı", f"{floor_results['total_area']:.2f} m²")
                        st.metric("Oda Sayısı", f"{floor_results['room_count']}")
                    with col2:
                        if floor_results['room_details']:
                            avg_area = floor_results['total_area'] / floor_results['room_count']
                            st.metric("Ortalama Oda Alanı", f"{avg_area:.2f} m²")
                
                # Plan Önizlemesi
                st.markdown("---")
                st.subheader("🗺️ Plan Önizlemesi")
                
                preview_fig = create_dxf_preview(
                    doc, 
                    wall_layer=wall_layer, 
                    floor_layer=floor_layer,
                    highlight_arcs=True
                )
                st.pyplot(preview_fig, use_container_width=True)
                
                # İndirme butonları
                st.markdown("---")
                col1, col2 = st.columns(2)
                
                with col1:
                    # Rapor metni oluştur
                    report = f"""
MİMARİ METRAJ RAPORU
====================
Proje: {uploaded_file.name}
Tarih: {st.session_state.get('_', '2024')}
Hazırlayan: Barış Öker - Fi-le Yazılım A.Ş.

DUVAR METRAJI
-------------
Katman: {wall_layer}
Toplam Çizgi Uzunluğu: {wall_results['total_length']:.2f} m
Aks Uzunluğu: {wall_results['axis_length']:.2f} m
Kat Yüksekliği: {floor_height} m
Duvar Alanı: {wall_results['wall_area']:.2f} m²

KAPI SAYIMI
-----------
Toplam Kapı (ARC): {door_count} adet

ZEMIN METRAJI
-------------
Katman: {floor_layer}
Toplam Alan: {floor_results['total_area']:.2f} m²
Oda Sayısı: {floor_results['room_count']}
                    """
                    st.download_button(
                        "📄 Metraj Raporunu İndir (.txt)",
                        report,
                        file_name=f"metraj_raporu_{uploaded_file.name.replace('.dxf', '')}.txt",
                        mime="text/plain"
                    )
    
    else:
        # Henüz dosya yüklenmedi
        st.info("👆 Lütfen bir DXF dosyası yükleyerek başlayın.")
        
        # Örnek bilgi kutusu
        st.markdown("""
        <div style="background-color: #e8f4f8; padding: 1.5rem; border-radius: 10px; margin-top: 2rem;">
            <h4>💡 Nasıl Çalışır?</h4>
            <ol>
                <li><strong>DXF Yükleyin:</strong> AutoCAD'de hazırladığınız mimari planı (.dxf) seçin.</li>
                <li><strong>Katmanları Seçin:</strong> Sistem otomatik olarak tüm katmanları listeler.</li>
                <li><strong>Duvar Katmanı:</strong> Duvar çizgilerinin olduğu katmanı seçin (çift çizgili).</li>
                <li><strong>Zemin Katmanı:</strong> Kapalı alanların (odalar) olduğu katmanı seçin.</li>
                <li><strong>Hesapla:</strong> Metraj otomatik hesaplanır ve plan önizlemesi gösterilir.</li>
            </ol>
            <p><small><strong>Not:</strong> Her ARC (yay) objesi otomatik olarak bir kapı olarak sayılır.</small></p>
        </div>
        """, unsafe_allow_html=True)

# =============================================================================
# UYGULAMA BAŞLATMA
# =============================================================================
if __name__ == "__main__":
    main()
