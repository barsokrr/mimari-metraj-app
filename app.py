from __future__ import annotations

import streamlit as st
import ezdxf
from ezdxf.explode import virtual_boundary_path_entities
from ezdxf.math import Vec3

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import math
import tempfile
import os
import time
import logging
import io
import html

import httpx
from supabase import create_client
from supabase.lib.client_options import SyncClientOptions
from supabase_auth import SyncMemoryStorage

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif", "serif"],
    }
)

st.set_page_config(
    page_title="🏗️ İnşaat Metraj Analizi",
    layout="wide",
    page_icon="🏗️",
    initial_sidebar_state="expanded",
)

# --- Tasarım tokenları (file. marka — seçenek B: mint-gri katmanlar, üst accent şerit) ---
THEME = {
    "bg": "#f0f4f3",
    "surface": "#e4eeec",
    "surface_elevated": "#ffffff",
    "sidebar": "#e8f2f0",
    "text_primary": "#0f172a",
    "text_secondary": "#475569",
    "text_muted": "#64748b",
    "accent": "#0f766e",
    "accent_secondary": "#0d9488",
    "accent_contrast": "#0f172a",
    "border": "#c5d9d4",
    "success": "#047857",
    "error": "#b91c1c",
    "warning": "#b45309",
    "plot_bg": "#f0f4f3",
    "plot_line_mute": "#9cb4af",
    "plot_line_accent": "#0f766e",
}

# --- PDF'den alınan iş kalemleri (İnşaat İş Kalemleri) ---
IS_KALEMLERI: tuple[str, ...] = (
    "Kazı",
    "Jet Grout",
    "Zemin Sıkıştırma",
    "Grobeton",
    "Temel Yalıtımı",
    "Temel Betonu",
    "Su Basman Perde",
    "Perde Yalıtımı",
    "Su Basman Dolgu",
    "Su Basman üstü Blokaj",
    "Kolon - Kiriş - Tabliye",
    "Baca Örülmesi",
    "Çatı Konstrüksiyon",
    "Çatı Su Yalıtım",
    "Çatı Isı Yalıtım",
    "Çatı Kaplama Kiremit",
    "Baca Şapkası",
    "Bims Blok Duvar",
    "PPRC Borulama duvar",
    "Islak Hacim Kaba Sıva",
    "Islak Hacim Tavan Sıva",
    "Tavan Karışık Alçı",
    "Tavan Saten Alçı",
    "Duvar Karışık Alçı Sıva",
    "Duvar Saten Alçı Sıva",
    "PPRC Borulama döşeme",
    "Şap",
    "Sürme Su Yalıtımı",
    "Seramik Kaplama Duvar (Banyo - WC)",
    "Seramik Kaplama Duvar (Mutfak)",
    "Seramik Kaplama Döşeme (Banyo - WC)",
    "Seramik Kaplama Döşeme (Mutfak)",
    "Tavan Astar - Boya",
    "Tavan Son Kat Boya",
    "İç Cephe Astar - Boya",
    "İç Cephe Son Kat Boya",
    "Laminat Parke",
    "Kör Kasa",
    "Denizlik",
    "Kapı",
    "Pencere",
    "PVC Pencere ve Isıcam",
    "Ahşap Kapı",
    "Demir Depo Kapı",
    "Çelik Giriş Kapı",
    "Çelik Kapı Eşik Mermer",
    "Lavabo Vitrifiye",
    "Banyo Vitrifiye",
    "Mutfak Tezgahı",
    "Mutfak Dolabı",
    "Kaba Sıva",
    "Taşyünü Isı Yalıtımı",
    "Yalıtım Üzeri Sıva",
    "Pencere Söve",
    "Dekoratif Sıva",
    "Tretuvar Betonu",
    "Andezit kaplama Bina Eteği",
    "Andezit kaplama döşeme - basamak",
    "Dış Cephe Astar - Boya",
    "Dış Cephe Son Kat Boya",
    "Merdiven Korkuluğu",
)

IS_KALEMI_CARPAN: dict[str, float] = {
    "Kazı": 0.35,
    "Jet Grout": 0.18,
    "Grobeton": 0.08,
    "Temel Betonu": 0.25,
    "Su Basman Perde": 0.20,
    "Su Basman Dolgu": 0.22,
    "Su Basman üstü Blokaj": 0.10,
    "Kolon - Kiriş - Tabliye": 0.16,
    "Baca Örülmesi": 0.04,
    "Tretuvar Betonu": 0.12,
    "Şap": 0.05,
    "Merdiven Korkuluğu": 0.60,
    "Kapı": 0.10,
    "Pencere": 0.12,
}


def _css_vars_block() -> str:
    t = THEME
    return f"""
    :root {{
        --bg: {t["bg"]};
        --surface: {t["surface"]};
        --surface-elevated: {t["surface_elevated"]};
        --sidebar: {t["sidebar"]};
        --text-primary: {t["text_primary"]};
        --text-secondary: {t["text_secondary"]};
        --text-muted: {t["text_muted"]};
        --accent: {t["accent"]};
        --accent-secondary: {t["accent_secondary"]};
        --accent-contrast: {t["accent_contrast"]};
        --border: {t["border"]};
        --success: {t["success"]};
        --error: {t["error"]};
        --warning: {t["warning"]};
    }}"""


def inject_global_styles() -> None:
    t = THEME
    _login_soft_5 = ", ".join(["0px 4px 12px 0px rgba(0, 0, 0, 0.15)"] * 5)
    st.markdown(
        f"""
    <style>
    {_css_vars_block()}
    .stApp {{
        background-color: var(--bg);
        color: var(--text-primary);
        font-family: "Times New Roman", Times, serif !important;
        padding-top: env(safe-area-inset-top, 0px);
        padding-bottom: env(safe-area-inset-bottom, 0px);
        padding-left: env(safe-area-inset-left, 0px);
        padding-right: env(safe-area-inset-right, 0px);
    }}
    .stApp [data-baseweb="typo"],
    .stApp [data-baseweb="typo"] *,
    .stApp .stMarkdown,
    .stApp .stMarkdown * {{
        font-family: "Times New Roman", Times, serif !important;
    }}
    [data-testid="stSidebar"] {{
        background-color: var(--sidebar);
        border-right: 1px solid var(--border);
        box-shadow: 2px 0 24px rgba(15, 118, 110, 0.04);
    }}
    [data-testid="stSidebar"] .block-container {{
        padding-top: 1rem;
    }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] {{
        background-color: rgba(99, 176, 100, 1) !important;
        border-style: solid !important;
        border-width: 1px !important;
        border-color: rgba(0, 0, 0, 1) !important;
        color: #000000 !important;
        font-family: "Times New Roman", Times, serif !important;
    }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] span {{
        color: #000000 !important;
        font-family: "Times New Roman", Times, serif !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] {{
        font-family: "Times New Roman", Times, serif !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stFileUploaderFileName"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"],
    [data-testid="stSidebar"] [data-testid="stFileUploader"] [data-testid="stMarkdownContainer"] p {{
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] {{
        background-color: rgba(99, 176, 100, 1) !important;
        border-style: solid !important;
        border-width: 1px !important;
        border-color: rgba(0, 0, 0, 1) !important;
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] *,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] span {{
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] button,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] button * {{
        font-family: "Times New Roman", Times, serif !important;
        color: #dc2626 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] svg {{
        color: #000000 !important;
        fill: currentColor !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] button svg {{
        color: #dc2626 !important;
        fill: currentColor !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] button {{
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stFileUploader"] svg {{
        color: #000000 !important;
        fill: currentColor !important;
    }}
    section[data-testid="stMain"] [data-testid="stMetric"] label,
    section[data-testid="stMain"] [data-testid="stMetric"] label p,
    section[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricLabel"],
    section[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricLabel"] p,
    section[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMarkdownContainer"] p {{
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
    }}
    section[data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricValue"],
    section[data-testid="stMain"] [data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        background-color: rgba(99, 176, 100, 1) !important;
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
    }}
    section[data-testid="stMain"] [data-testid="stDownloadButton"] button {{
        background-color: rgba(99, 176, 100, 1) !important;
        border-color: rgba(15, 23, 42, 0.14) !important;
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
    }}
    section[data-testid="stMain"] [data-testid="stDownloadButton"] button svg {{
        color: #000000 !important;
        fill: currentColor !important;
    }}
    section[data-testid="stMain"] [data-testid="stDownloadButton"] [data-testid="stMarkdownContainer"],
    section[data-testid="stMain"] [data-testid="stDownloadButton"] [data-testid="stMarkdownContainer"] > div,
    section[data-testid="stMain"] [data-testid="stDownloadButton"] p {{
        font-family: "Times New Roman", Times, serif !important;
        color: #000000 !important;
        background-color: #ffffff !important;
    }}
    section[data-testid="stMain"] [data-testid="stImage"] {{
        background-color: rgba(99, 176, 100, 1) !important;
        padding: 0.5rem !important;
        border-radius: 10px !important;
        box-sizing: border-box !important;
    }}
    section[data-testid="stMain"] [data-testid="stImage"] img {{
        background-color: rgba(99, 176, 100, 1) !important;
        border-radius: 6px !important;
    }}
    section[data-testid="stMain"]:not(:has(h1.centered-title)) [data-testid="stElementContainer"]:has([data-testid="stTextInput"]) {{
        width: 100% !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
    }}
    section[data-testid="stMain"]:not(:has(h1.centered-title)) [data-testid="stTextInput"] {{
        width: min(36rem, 100%) !important;
        max-width: 100% !important;
    }}
    section[data-testid="stMain"]:not(:has(h1.centered-title)) [data-testid="stTextInput"] div[data-baseweb="base-input"] {{
        width: 100% !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }}
    .login-shell {{
        max-width: 28rem;
        margin: 0 auto;
        padding: 0 1rem;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) div[data-testid="stVerticalBlock"] {{
        padding-bottom: calc(14rem + env(safe-area-inset-bottom, 0px));
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="column"] [data-testid="stVerticalBlock"] {{
        background-color: var(--surface) !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {{
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        width: 100% !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) [data-testid="stVerticalBlock"],
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) > div > div.stVerticalBlock {{
        background-color: var(--surface) !important;
        border-style: solid !important;
        border-width: 1px !important;
        border-color: rgba(0, 0, 0, 1) !important;
        height: 279px !important;
        min-height: 279px !important;
        margin-top: 34px !important;
        margin-bottom: 34px !important;
        width: 100% !important;
        max-width: 36rem !important;
        margin-left: auto !important;
        margin-right: auto !important;
        align-items: center !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stElementContainer"]:has([data-testid="stTextInput"]) {{
        max-width: 555px !important;
        width: min(555px, 100%) !important;
        height: 50px !important;
        min-height: 50px !important;
        display: flex !important;
        flex-direction: column !important;
        align-items: center !important;
        justify-content: center !important;
        margin-top: 4px !important;
        margin-bottom: 4px !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }}
    section[data-testid="stMain"] .stMarkdown p:empty {{
        display: none !important;
        margin: 0 !important;
        padding: 0 !important;
        height: 0 !important;
        min-height: 0 !important;
        overflow: hidden;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stTextInput"] {{
        max-width: 555px;
        width: 100%;
        margin-left: auto;
        margin-right: auto;
        margin-top: 3px;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stTextInput"] label,
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stTextInput"] label p {{
        padding-top: 0 !important;
        padding-bottom: 0 !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stTextInput"] div[data-baseweb="base-input"] {{
        width: 100% !important;
        max-width: min(555px, 100%) !important;
        margin-left: auto !important;
        margin-right: auto !important;
        background: unset !important;
        background-color: rgba(197, 217, 212, 1) !important;
        border-style: solid !important;
        border-width: 1px !important;
        border-color: rgba(255, 255, 255, 1) !important;
        border-image: none !important;
        box-shadow: {_login_soft_5} !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stTextInput"] input {{
        font-family: "Times New Roman", Times, serif !important;
        text-align: center !important;
        min-height: 46px !important;
        height: 46px !important;
        padding: 10px 20px 13px 20px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        width: min(100%, 520px) !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
        color: var(--success) !important;
        background: unset !important;
        background-color: rgba(197, 217, 212, 1) !important;
        border-style: solid !important;
        border-width: 1px !important;
        border-color: rgba(255, 255, 255, 1) !important;
        border-image: none !important;
        border-radius: 8px !important;
        box-shadow: {_login_soft_5} !important;
        overflow: visible !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) [data-testid="stTextInput"] input::placeholder {{
        color: var(--text-muted) !important;
        opacity: 1 !important;
        text-align: center !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) button[data-testid="stBaseButton-secondary"] {{
        max-width: 555px;
        width: 100%;
        min-height: 66px !important;
        margin-left: auto;
        margin-right: auto;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        background-color: #ffffff !important;
        border: 1px solid var(--border) !important;
        color: var(--accent) !important;
        font-family: "Times New Roman", Times, serif !important;
        font-weight: 600 !important;
        box-shadow: none !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) button[data-testid="stBaseButton-secondary"]:hover {{
        border-color: var(--accent) !important;
        background-color: #f8fafc !important;
    }}
    section[data-testid="stMain"]:has(h1.centered-title) button[data-testid="stBaseButton-secondary"] [data-testid="stMarkdownContainer"],
    section[data-testid="stMain"]:has(h1.centered-title) button[data-testid="stBaseButton-secondary"] p {{
        font-family: "Times New Roman", Times, serif !important;
        text-align: center !important;
        width: 100% !important;
        margin: 0 !important;
        padding: 0 !important;
        color: var(--accent) !important;
        background-image: none !important;
        background-clip: border-box !important;
        -webkit-background-clip: border-box !important;
        min-height: unset !important;
        max-width: none !important;
        line-height: 1.3 !important;
    }}
    .centered-title {{
        font-family: "Times New Roman", Times, serif !important;
        display: grid;
        place-items: center;
        text-align: center;
        margin-top: clamp(1rem, 4vh, 2.5rem) !important;
        margin-bottom: 0.5rem !important;
        font-weight: 700;
        color: rgba(99, 176, 100, 1) !important;
        font-size: clamp(1.2rem, 2.8vw + 0.6rem, 1.85rem);
        line-height: 1.25;
        letter-spacing: -0.02em;
        background: unset !important;
        background-color: rgba(197, 217, 212, 1) !important;
        border-style: solid !important;
        border-width: 1px !important;
        border-color: rgba(255, 255, 255, 1) !important;
        border-image: none !important;
        box-shadow: {_login_soft_5} !important;
    }}
    .user-info-card {{
        padding: 1rem 1.1rem;
        background-color: var(--surface-elevated);
        border-radius: 14px;
        border: 1px solid var(--border);
        border-top: 3px solid var(--accent);
        margin-bottom: 1rem;
        box-shadow: 0 2px 14px rgba(15, 118, 110, 0.08);
    }}
    .user-name {{ color: var(--text-primary); font-weight: 600; font-size: 1.05rem; margin-bottom: 4px; }}
    .user-credits {{ color: var(--accent); font-weight: 600; font-size: 0.95rem; }}
    .footer-fixed-section {{
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: var(--sidebar);
        padding: 12px 4% calc(12px + env(safe-area-inset-bottom, 0px)) 4%;
        border-top: 1px solid var(--border);
        z-index: 999;
        box-shadow: 0 -4px 20px rgba(15, 118, 110, 0.07);
    }}
    .copyright-text {{
        text-align: center;
        color: var(--text-muted);
        font-size: 0.7rem;
        margin-top: 8px;
    }}
    .page-footer-hr {{
        border: none;
        border-top: 1px solid var(--border);
        margin-top: 2.5rem;
    }}
    .page-footer-note {{
        text-align: center;
        color: var(--text-muted);
        font-size: 0.7rem;
        margin-bottom: max(4rem, env(safe-area-inset-bottom, 0px));
    }}
    .stButton > button {{
        min-height: 44px;
        border-radius: 10px;
        font-weight: 600;
    }}
    .stButton > button[kind="primary"] {{
        background-color: var(--surface-elevated) !important;
        border: 2px solid var(--accent) !important;
        color: var(--accent-contrast) !important;
        box-shadow: none !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        border-color: var(--accent-secondary) !important;
        color: var(--accent) !important;
        background-color: var(--surface) !important;
    }}
    .stApp a:link, .stApp a:visited {{
        color: var(--accent);
    }}
    .stApp a:hover {{
        color: var(--accent-secondary);
    }}
    div[data-testid="stAlert"] {{
        border: 1px solid var(--border);
        border-radius: 14px;
        background-color: var(--surface-elevated);
        box-shadow: 0 2px 10px rgba(15, 118, 110, 0.06);
    }}
    div[data-testid="stAlert"] [data-baseweb="notification"] {{
        background-color: transparent !important;
        color: var(--text-primary) !important;
    }}
    [data-testid="stTable"] {{
        border: 1px solid var(--border);
        border-radius: 8px;
        overflow: hidden;
    }}
    @media (max-width: 768px) {{
        div[data-testid="stVerticalBlock"] > div {{ min-height: unset !important; }}
        .footer-fixed-section [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
        }}
        .footer-fixed-section [data-testid="column"] {{
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: unset !important;
        }}
    }}
    @media (max-width: 900px) {{
        section[data-testid="stMain"] [data-testid="stHorizontalBlock"] {{
            flex-wrap: wrap !important;
            gap: 0.75rem !important;
        }}
        section[data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="column"] {{
            flex: 1 1 100% !important;
            width: 100% !important;
            min-width: unset !important;
        }}
    }}
    div[data-testid="stExpander"] details summary {{
        min-height: 44px;
        display: flex;
        align-items: center;
    }}
    /* Sadece üst panel sekmeleri (st.container key=metraj_root_tabs) */
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] {{
        background-color: #ffffff !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] [role="tablist"] {{
        background-color: #ffffff !important;
        gap: 0 !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"] {{
        background-color: #ffffff !important;
        color: var(--text-secondary) !important;
        border-radius: 0 !important;
        border-bottom: 2px solid transparent !important;
        transition: background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"]:not(:last-child) {{
        border-right: 1px solid var(--border) !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="false"] {{
        background-color: #ffffff !important;
        color: var(--text-secondary) !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="true"] {{
        background-color: #ffffff !important;
        color: var(--accent) !important;
        font-weight: 600 !important;
        border-bottom: 2px solid var(--accent) !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="false"]:hover,
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="false"]:focus-visible {{
        background-color: var(--surface) !important;
        color: var(--text-primary) !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="true"]:hover,
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="true"]:focus-visible {{
        background-color: #ffffff !important;
        color: var(--accent) !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="false"]:active {{
        background-color: var(--surface) !important;
    }}
    section[data-testid="stMain"] [class*="metraj_root_tabs"] [data-testid="stTabs"] button[data-testid="stTab"][aria-selected="true"]:active {{
        background-color: #ffffff !important;
        color: var(--accent) !important;
    }}
    </style>
    """,
        unsafe_allow_html=True,
    )


_DXF_DIM_TYPES = frozenset({"DIMENSION", "ARC_DIMENSION", "LARGE_RADIAL_DIMENSION"})
_PREVIEW_FLATTEN = 0.02


def _expand_msp_entity(entity, depth: int = 0):
    """INSERT / MINSERT içeriğini model uzayına taşır; bozuk blokta yerleşim işareti için INSERT bırakır."""
    if depth > 48:
        return
    if entity.dxftype() == "INSERT":
        if getattr(entity, "mcount", 1) > 1:
            try:
                for sub in entity.multi_insert():
                    yield from _expand_msp_entity(sub, depth + 1)
                return
            except Exception:
                pass
        try:
            any_child = False
            for ve in entity.virtual_entities():
                any_child = True
                yield from _expand_msp_entity(ve, depth + 1)
            if not any_child:
                yield entity
        except Exception:
            yield entity
    else:
        yield entity


def _iter_flat_msp(msp):
    for entity in msp:
        yield from _expand_msp_entity(entity, 0)


def dxf_figure_from_modelspace(msp, hedef_katman: str):
    """DXF modelspace önizlemesi (genişletilmiş entity desteği) ve hedef katman uzunluğu."""
    fig, ax = plt.subplots(
        figsize=(12.5, 9.0),
        dpi=160,
        facecolor=THEME["plot_bg"],
        layout="none",
    )
    ax.set_facecolor(THEME["plot_bg"])
    total_length = 0.0
    layers_seen: set[str] = set()
    mute = THEME["plot_line_mute"]
    accent = THEME["plot_line_accent"]
    hedef_u = (hedef_katman or "").strip().upper()

    def style_for(layer_name: str) -> tuple[str, float, bool]:
        is_target = bool(hedef_u) and (hedef_u in layer_name)
        if is_target:
            return accent, 2.85, True
        return mute, 1.05, False

    def plot_linestring(xs: list[float], ys: list[float], color: str, lw: float) -> None:
        if len(xs) < 2:
            return
        ax.plot(
            xs,
            ys,
            color=color,
            lw=lw,
            solid_capstyle="round",
            solid_joinstyle="round",
            antialiased=True,
        )

    def chord_length_sum(xs: list[float], ys: list[float], is_target: bool) -> float:
        if not is_target or len(xs) < 2:
            return 0.0
        s = 0.0
        for i in range(len(xs) - 1):
            s += math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i])
        return s

    def draw_one(entity, depth: int = 0) -> float:
        if depth > 64:
            return 0.0
        try:
            layer = getattr(entity.dxf, "layer", "").upper()
            if layer:
                layers_seen.add(layer)
            color, lw, is_target = style_for(layer)
            dt = entity.dxftype()

            if dt in _DXF_DIM_TYPES:
                acc = 0.0
                for ve in entity.virtual_entities():
                    acc += draw_one(ve, depth + 1)
                return acc

            if dt == "HATCH":
                acc = 0.0
                for path_group in virtual_boundary_path_entities(entity):
                    for ve in path_group:
                        acc += draw_one(ve, depth + 1)
                return acc

            if dt == "LINE":
                s, e = entity.dxf.start, entity.dxf.end
                xs = [float(s[0]), float(e[0])]
                ys = [float(s[1]), float(e[1])]
                plot_linestring(xs, ys, color, lw)
                return chord_length_sum(xs, ys, is_target)

            if dt == "LWPOLYLINE":
                if getattr(entity, "has_arc", False):
                    acc = 0.0
                    for ve in entity.virtual_entities():
                        acc += draw_one(ve, depth + 1)
                    return acc
                pts = list(entity.vertices_in_wcs())
                if len(pts) < 2:
                    return 0.0
                xs = [float(p.x) for p in pts]
                ys = [float(p.y) for p in pts]
                if entity.closed:
                    xs.append(xs[0])
                    ys.append(ys[0])
                plot_linestring(xs, ys, color, lw)
                return chord_length_sum(xs, ys, is_target)

            if dt == "POLYLINE":
                if getattr(entity, "is_polygon_mesh", False) and entity.is_polygon_mesh:
                    return 0.0
                if getattr(entity, "is_poly_face_mesh", False) and entity.is_poly_face_mesh:
                    return 0.0
                if getattr(entity, "has_arc", False):
                    acc = 0.0
                    for ve in entity.virtual_entities():
                        acc += draw_one(ve, depth + 1)
                    return acc
                try:
                    pts = list(entity.points_in_wcs())
                except (AttributeError, TypeError):
                    pts = list(entity.points())
                if len(pts) < 2:
                    return 0.0
                xs = [float(p.x) for p in pts]
                ys = [float(p.y) for p in pts]
                if getattr(entity, "is_closed", False) and entity.is_closed:
                    xs.append(xs[0])
                    ys.append(ys[0])
                plot_linestring(xs, ys, color, lw)
                return chord_length_sum(xs, ys, is_target)

            if dt == "ARC":
                pts = list(entity.flattening(_PREVIEW_FLATTEN))
                if len(pts) < 2:
                    return 0.0
                xs = [float(p.x) for p in pts]
                ys = [float(p.y) for p in pts]
                plot_linestring(xs, ys, color, lw)
                return chord_length_sum(xs, ys, is_target)

            if dt == "CIRCLE":
                pts = list(entity.flattening(_PREVIEW_FLATTEN))
                if len(pts) < 2:
                    return 0.0
                xs = [float(p.x) for p in pts]
                ys = [float(p.y) for p in pts]
                plot_linestring(xs, ys, color, lw)
                if is_target:
                    return 2.0 * math.pi * abs(float(entity.dxf.radius))
                return 0.0

            if dt == "ELLIPSE":
                pts = list(entity.flattening(_PREVIEW_FLATTEN))
                if len(pts) < 2:
                    return 0.0
                xs = [float(p.x) for p in pts]
                ys = [float(p.y) for p in pts]
                plot_linestring(xs, ys, color, lw)
                return chord_length_sum(xs, ys, is_target)

            if dt in ("SPLINE", "HELIX"):
                pts = list(entity.flattening(distance=_PREVIEW_FLATTEN))
                if len(pts) < 2:
                    return 0.0
                xs = [float(p.x) for p in pts]
                ys = [float(p.y) for p in pts]
                plot_linestring(xs, ys, color, lw)
                return chord_length_sum(xs, ys, is_target)

            if dt == "INSERT":
                ins = entity.dxf.insert
                ocs = entity.ocs()
                p = ocs.to_wcs(Vec3(ins))
                sx = abs(float(getattr(entity.dxf, "xscale", 1) or 1.0))
                sy = abs(float(getattr(entity.dxf, "yscale", 1) or 1.0))
                r = max(0.08 * (sx + sy), 0.05)
                lw_m = max(lw, 1.3)
                plot_linestring([p.x - r, p.x + r], [p.y, p.y], color, lw_m)
                plot_linestring([p.x, p.x], [p.y - r, p.y + r], color, lw_m)
                return 0.0

            if dt == "POINT":
                loc = entity.dxf.location
                ax.plot(float(loc[0]), float(loc[1]), marker=".", ms=3, color=color)
                return 0.0

            if dt in ("TEXT", "ATTRIB"):
                ins = entity.dxf.insert
                ax.plot(float(ins[0]), float(ins[1]), marker=",", ms=2, color=color)
                return 0.0

            if dt == "MTEXT":
                ins = entity.dxf.insert
                ax.plot(float(ins[0]), float(ins[1]), marker=",", ms=2, color=color)
                return 0.0

        except Exception:
            return 0.0
        return 0.0

    for ent in _iter_flat_msp(msp):
        total_length += draw_one(ent, 0)

    ax.set_aspect("equal", adjustable="datalim")
    ax.axis("off")
    if ax.lines or ax.collections:
        ax.relim(visible_only=False)
        ax.autoscale_view(tight=True)
        xmin, xmax = ax.get_xlim()
        ymin, ymax = ax.get_ylim()
        dx = xmax - xmin
        dy = ymax - ymin
        span = max(dx, dy, 1e-9)
        pad = span * 0.035
        ax.set_xlim(xmin - pad, xmax + pad)
        ax.set_ylim(ymin - pad, ymax + pad)
    fig.subplots_adjust(left=0.01, right=0.99, top=0.99, bottom=0.01)
    fig.canvas.draw()
    return fig, ax, total_length, sorted(layers_seen)


def excel_rows_duvar(total_length: float, birim: str, kat_yuksekligi: float) -> tuple[list, float, float]:
    birim_carpani = {"mm": 1000.0, "cm": 100.0, "m": 1.0}.get(birim, 100.0)
    aks_uzunluk = (total_length / 2.0) / birim_carpani
    toplam_alan = aks_uzunluk * kat_yuksekligi
    return [
        {"Kalem": "Aks Uzunluğu", "Değer": round(aks_uzunluk, 2), "Birim": "m"},
        {"Kalem": "Toplam Alan", "Değer": round(toplam_alan, 2), "Birim": "m²"},
        {"Kalem": "Kat Yüksekliği", "Değer": kat_yuksekligi, "Birim": "m"},
    ], aks_uzunluk, toplam_alan


def build_excel_bytes(excel_data: list) -> bytes:
    output_df = pd.DataFrame(excel_data)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        output_df.to_excel(writer, index=False, sheet_name="Metraj Sonuclari")
    return buffer.getvalue()


def _normalize_tr(text: str) -> str:
    return (
        text.lower()
        .replace("ı", "i")
        .replace("ş", "s")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ö", "o")
        .replace("ç", "c")
    )


def is_kalemi_birimi(kalem: str) -> str:
    n = _normalize_tr(kalem)
    m3_keys = ("kazi", "grout", "beton", "blokaj", "dolgu", "sap", "tabliye")
    m_keys = ("borulama", "kasa", "denizlik", "korkuluk")
    if any(k in n for k in m3_keys):
        return "m3"
    if any(k in n for k in m_keys):
        return "m"
    return "m2"


def is_kalemi_miktari(
    kalem: str,
    birim: str,
    aks_uzunluk_m: float,
    toplam_alan_m2: float,
    duvar_kalinligi_m: float,
) -> float:
    baz_hacim = toplam_alan_m2 * duvar_kalinligi_m
    carpan = float(IS_KALEMI_CARPAN.get(kalem, 1.0))
    if birim == "m3":
        return baz_hacim * carpan
    if birim == "m":
        return aks_uzunluk_m * carpan
    return toplam_alan_m2 * carpan


def build_is_kalemleri_raporu(
    aks_uzunluk_m: float,
    toplam_alan_m2: float,
    duvar_kalinligi_m: float,
) -> list[dict]:
    rows: list[dict] = []
    nan = float("nan")
    for kalem in IS_KALEMLERI:
        if kalem != "Bims Blok Duvar":
            rows.append({"İş Kalemi": kalem, "m³": nan, "m²": nan, "m": nan})
            continue
        birim = is_kalemi_birimi(kalem)
        miktar = round(
            is_kalemi_miktari(
                kalem,
                birim,
                aks_uzunluk_m=aks_uzunluk_m,
                toplam_alan_m2=toplam_alan_m2,
                duvar_kalinligi_m=duvar_kalinligi_m,
            ),
            3,
        )
        rows.append(
            {
                "İş Kalemi": kalem,
                "m³": miktar if birim == "m3" else nan,
                "m²": miktar if birim == "m2" else nan,
                "m": miktar if birim == "m" else nan,
            }
        )
    return rows


def render_is_kalemleri_paneli() -> None:
    metrics = st.session_state.get("dxf_last_metrics")
    if not metrics:
        st.info(
            "İş kalemleri bu sekmede (**YAPI İŞLERİ İNŞAAT**) listelenir. "
            "Önce **DUVAR** sekmesinde analizi başlatın."
        )
        return

    duvar_kalinligi = float(st.session_state.get("is_kalemleri_duvar_kalinligi", 0.20))

    aks = round(float(metrics["aks_uzunluk_m"]), 6)
    alan = round(float(metrics["toplam_alan_m2"]), 6)
    fp = (aks, alan)
    if (
        st.session_state.get("_is_kalemleri_fp") != fp
        or "is_kalemleri_df" not in st.session_state
    ):
        st.session_state["is_kalemleri_df"] = pd.DataFrame(
            build_is_kalemleri_raporu(
                aks_uzunluk_m=float(metrics["aks_uzunluk_m"]),
                toplam_alan_m2=float(metrics["toplam_alan_m2"]),
                duvar_kalinligi_m=duvar_kalinligi,
            )
        )
        st.session_state["_is_kalemleri_fp"] = fp

    df = st.session_state["is_kalemleri_df"].copy()
    editor_key = f"is_k_ed_{aks}_{alan}"

    edited = st.data_editor(
        df,
        width="stretch",
        hide_index=True,
        num_rows="fixed",
        key=editor_key,
        column_config={
            "İş Kalemi": st.column_config.TextColumn("İş Kalemi", disabled=True, width="large"),
            "m³": st.column_config.NumberColumn("m³", format="%.3f"),
            "m²": st.column_config.NumberColumn("m²", format="%.3f"),
            "m": st.column_config.NumberColumn("m", format="%.3f"),
        },
    )
    edited_df = pd.DataFrame(edited)
    mask_bims = edited_df["İş Kalemi"] == "Bims Blok Duvar"
    cols = ["m³", "m²", "m"]
    nan = float("nan")
    edited_df.loc[~mask_bims, cols] = nan

    st.session_state["is_kalemleri_df"] = edited_df

    excel_rows = edited_df.to_dict("records")
    st.download_button(
        label="📊 Tüm iş kalemlerini Excel olarak indir",
        data=build_excel_bytes(excel_rows),
        file_name=f"is_kalemleri_raporu_{int(time.time())}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )


def render_analysis_results(
    fig,
    total_length: float,
    birim: str,
    kat_yuksekligi: float,
    hedef_katman: str = "",
    layer_hints: list[str] | None = None,
) -> dict[str, float]:
    """Referans düzen: sol önizleme, sağ Aks uzunluğu / Toplam alan ve Excel indirme."""
    if total_length <= 0.0:
        st.warning(
            f"**{hedef_katman or 'DUVAR'}** ile eşleşen çizgi / yay / spline bulunamadı. "
            "Kenar çubuğundaki **Duvar Katmanı** değerini dosyanızdaki katman adıyla aynı (veya içeren) olacak şekilde güncelleyin."
        )
        if layer_hints:
            tail = ", ".join(layer_hints[:40])
            if len(layer_hints) > 40:
                tail += " …"
            st.caption(f"Dosyada görülen katman örnekleri: {tail}")
    excel_data, aks_uzunluk, toplam_alan = excel_rows_duvar(
        total_length, birim, kat_yuksekligi
    )
    col_left, col_right = st.columns([2, 1])
    with col_left:
        st.pyplot(fig, clear_figure=False)
    with col_right:
        st.metric("Aks Uzunluğu", f"{aks_uzunluk:.2f} m")
        st.metric("Toplam Alan", f"{toplam_alan:.2f} m²")
        if excel_data:
            st.download_button(
                label="📊 Analizi Excel Olarak İndir",
                data=build_excel_bytes(excel_data),
                file_name=f"metraj_analizi_{int(time.time())}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
            )
    return {"aks_uzunluk_m": float(aks_uzunluk), "toplam_alan_m2": float(toplam_alan)}


def run_dxf_analysis(
    uploaded_bytes: bytes,
    katman_secimi: str,
    birim: str,
    kat_yuksekligi: float,
) -> dict[str, float] | None:
    """Geçici dosya → DXF okuma → duvar metrajı (1 bilet çağıran tarafta düşülür)."""
    for _name in ("ezdxf", "ezdxf.xref", "ezdxf.options"):
        logging.getLogger(_name).setLevel(logging.ERROR)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".dxf") as tmp:
        tmp.write(uploaded_bytes)
        tmp_path = tmp.name
    fig = None
    try:
        plt.close("all")
        doc = ezdxf.readfile(tmp_path)
        msp = doc.modelspace()
        hedef_katman = (katman_secimi.strip().upper() or "DUVAR")
        fig, _ax, total_length, layer_hints = dxf_figure_from_modelspace(msp, hedef_katman)
        return render_analysis_results(
            fig,
            total_length,
            birim,
            kat_yuksekligi,
            hedef_katman,
            layer_hints,
        )
    except Exception as e:
        st.error(f"DXF işlenirken hata: {e}")
        if fig is not None:
            plt.close(fig)
        return None
    finally:
        if os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# --- VERİTABANI VE OTURUM ---
try:
    _sb_url = str(st.secrets["supabase"]["url"]).strip()
    _sb_key = str(st.secrets["supabase"]["key"]).strip()
except Exception:
    st.error("Veritabanı anahtarları eksik! Lütfen secrets.toml dosyasını kontrol edin.")
    st.stop()


@st.cache_resource
def _supabase_client():
    """Tek httpx oturumu; macOS LibreSSL / proxy kaynaklı TLS EOF hatalarını azaltır."""
    http = httpx.Client(
        http2=False,
        trust_env=False,
        timeout=httpx.Timeout(120.0, connect=60.0),
    )
    return create_client(
        _sb_url,
        _sb_key,
        options=SyncClientOptions(
            storage=SyncMemoryStorage(),
            httpx_client=http,
        ),
    )


try:
    supabase = _supabase_client()
except Exception as e:
    st.error(
        "Supabase istemcisi oluşturulamadı. Ağ, güvenlik duvarı veya SSL ortamını kontrol edin.\n\n"
        f"Ayrıntı: {e!s}"
    )
    st.stop()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "dxf_hedef_katman" not in st.session_state:
    st.session_state.dxf_hedef_katman = "DUVAR"
if "dxf_last_metrics" not in st.session_state:
    st.session_state.dxf_last_metrics = None

inject_global_styles()


def get_user_data(email):
    email = email.lower().strip()
    response = supabase.table("users").select("*").eq("email", email).execute()
    if len(response.data) == 0:
        new_user = {"email": email, "credits": 0}
        supabase.table("users").insert(new_user).execute()
        return new_user
    return response.data[0]


def _invalidate_sidebar_user_cache() -> None:
    st.session_state.pop("_sidebar_user_info", None)
    st.session_state.pop("_sidebar_user_info_for_email", None)


def get_sidebar_user_info(email: str) -> dict:
    """Kenar çubuğu için kullanıcı satırı; her rerun'da Supabase çağırmaz (DXF yüklemesi sonrası yanıt için)."""
    em = email.lower().strip()
    if (
        st.session_state.get("_sidebar_user_info_for_email") == em
        and "_sidebar_user_info" in st.session_state
    ):
        return st.session_state["_sidebar_user_info"]
    data = get_user_data(em)
    st.session_state["_sidebar_user_info_for_email"] = em
    st.session_state["_sidebar_user_info"] = data
    return data


def _clear_payment_status_query_param() -> None:
    """Ödeme callback'inde status=success tekrarlanmasın diye sorgu parametresini kaldır."""
    try:
        if "status" in st.query_params:
            st.query_params.pop("status", None)
    except Exception:
        try:
            st.query_params.clear()
        except Exception:
            pass


def use_credit(email):
    user = get_user_data(email)
    if user["credits"] > 0:
        new_credits = user["credits"] - 1
        supabase.table("users").update({"credits": new_credits}).eq("email", email).execute()
        _invalidate_sidebar_user_cache()
        return True
    return False


query_params = st.query_params
if query_params.get("status") == "success":
    target_email = (st.session_state.get("user_email") or "").lower().strip()
    if target_email:
        try:
            user_data = get_user_data(target_email)
            new_credits = user_data["credits"] + 1
            supabase.table("users").update({"credits": new_credits}).eq("email", target_email).execute()
            _invalidate_sidebar_user_cache()
            st.balloons()
            st.success(f"🎉 Ödeme Onaylandı! 1 Analiz Hakkı Tanımlandı. Yeni Bakiye: {new_credits}")
            _clear_payment_status_query_param()
            time.sleep(2)
            st.rerun()
        except Exception as e:
            st.error(f"Bilet tanımlanırken hata oluştu: {str(e)}")
            _clear_payment_status_query_param()
    else:
        st.warning("⚠️ Ödeme başarılı ancak biletin tanımlanması için önce giriş yapmalısınız.")
        _clear_payment_status_query_param()


def show_login_footer():
    st.markdown('<div class="footer-fixed-section">', unsafe_allow_html=True)
    col_leg1, col_leg2, col_leg3 = st.columns(3)
    with col_leg1:
        with st.expander("Gizlilik ve KVKK"):
            st.write("E-posta adresiniz sadece sisteme giriş ve bilet tanımlama amacıyla saklanır.")
    with col_leg2:
        with st.expander("Satış Sözleşmesi"):
            st.write("Satın alınan analiz hakları dijital içerik kapsamındadır ve anında tanımlanır.")
    with col_leg3:
        with st.expander("İade Politikası"):
            st.write("Dijital hizmetler (analiz hakları) Mesafeli Satış Sözleşmesi gereği iade kapsamı dışındadır.")
    st.markdown(
        '<div class="copyright-text">© 2026 <a href="https://filemimarlik.com" target="_blank" rel="noopener noreferrer">Fi-le Mimarlık & Yazılım</a>. Tüm hakları saklıdır.</div></div>',
        unsafe_allow_html=True,
    )


if not st.session_state.logged_in:
    st.markdown(
        '<div class="login-shell"><h1 class="centered-title" id="mimari-metraj-analizi">🏗️ İnşaat Metraj Analizi</h1></div>',
        unsafe_allow_html=True,
    )
    _, login_col, _ = st.columns([1, 6, 1])
    with login_col:
        email_input = st.text_input(
            "E-posta",
            placeholder="ornek@mail.com",
            label_visibility="collapsed",
        )

        if st.button("Giriş Yap", width="stretch"):
            if "@" in email_input and "." in email_input:
                user = get_user_data(email_input)
                st.session_state.user_email = user["email"]
                st.session_state.logged_in = True
                _invalidate_sidebar_user_cache()
                st.rerun()
            else:
                st.error("Lütfen geçerli bir e-posta adresi girin.")

        st.caption(
            "**Önemli:** Girdiğiniz e-posta adresi, hesabınızı tanımlamak amacıyla veri tabanında (Supabase) saklanır. "
            "Uygulama içi satın alınan analiz hakları yalnızca bu e-postaya tanımlanır. Kredilerinizin doğru hesabınıza "
            "atanması için lütfen her zaman aynı e-posta adresiyle giriş yapın."
        )

    show_login_footer()
    st.stop()

user_info = get_sidebar_user_info(st.session_state.user_email)
bilet_sayisi = user_info["credits"]
has_credits = bilet_sayisi > 0
_kullanici_goster = html.escape(st.session_state.user_email.strip())
_kredi_goster = html.escape(str(bilet_sayisi))

kat_yuksekligi = 2.85
birim = "cm"
uploaded = None

with st.sidebar:
    st.markdown(
        f"""
        <div class="user-info-card">
            <div class="user-name">Kullanıcı: {_kullanici_goster}</div>
            <div class="user-credits">Mevcut kredi: {_kredi_goster}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()
    if has_credits:
        # iOS / Safari dosya seçicide .dxf bazen gri kalıyor; bu yüzden tür filtresini kaldırıp
        # uzantı kontrolünü analiz butonunda yapıyoruz.
        uploaded = st.file_uploader("📁 DXF Dosyası Yükle")
        st.text_input(
            "Duvar Katmanı",
            key="dxf_hedef_katman",
            help="Metrajda sayılacak duvar çizgilerinin katman adı (boş veya eşleşmezse DUVAR kullanılır).",
        )
        kat_yuksekligi = st.number_input(
            "Kat Yüksekliği (m)",
            value=2.85,
            step=0.01,
        )
        birim = st.selectbox(
            "Çizim Birimi",
            ["cm", "mm", "m"],
            index=0,
            key="dxf_sidebar_cizim_birimi",
        )
    else:
        st.error("Analiz hakkınız kalmadı.")
        paytr_link = "https://www.paytr.com/link/Hp0l6fm"
        st.link_button("Satın Al (249 TL)", paytr_link, width="stretch")

    if st.button("Güvenli Çıkış", width="stretch"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        _invalidate_sidebar_user_cache()
        st.rerun()

st.title("İnşaat Metraj Analiz Paneli")

# Üst sekmeler: DUVAR (DXF), ardından üç YAPI sekmesi (İnşaat / Mekanik / Elektrik).
with st.container(key="metraj_root_tabs"):
    tab_dxf, tab_yapi_insaat, tab_yapi_mekanik, tab_yapi_elektrik = st.tabs(
        ["DUVAR", "YAPI İŞLERİ İNŞAAT", "YAPI İŞLERİ MEKANİK", "YAPI İŞLERİ ELEKTRİK"]
    )
    with tab_dxf:
        katman_secimi = str(st.session_state.get("dxf_hedef_katman", "DUVAR")).strip()

        if uploaded:
            if st.button("📥 Analizi Başlat (1 Bilet)", type="primary"):
                if use_credit(st.session_state.user_email):
                    try:
                        with st.spinner("DXF işleniyor; büyük dosyalarda birkaç dakika sürebilir…"):
                            metrics = run_dxf_analysis(
                                uploaded.getvalue(),
                                katman_secimi,
                                birim,
                                kat_yuksekligi,
                            )
                            if metrics:
                                st.session_state["dxf_last_metrics"] = metrics
                        _invalidate_sidebar_user_cache()
                    except Exception as e:
                        st.error(f"Hata: {str(e)}")
                else:
                    st.error("Yetersiz analiz hakkı!")
        else:
            st.info(
                f"Hoş geldiniz **{st.session_state.user_email}**. Analiz için kenar çubuğundan DXF yükleyin. "
                "Satın alma sonrası haklarınız otomatik tanımlanır."
            )

    with tab_yapi_insaat:
        render_is_kalemleri_paneli()

    with tab_yapi_mekanik:
        st.info("YAPI İŞLERİ MEKANİK — Bu bölüm yakında eklenecek.")

    with tab_yapi_elektrik:
        st.info("YAPI İŞLERİ ELEKTRİK — Bu bölüm yakında eklenecek.")

st.markdown(
    """
    <hr class="page-footer-hr" />
    <div class="page-footer-note">© 2026 <a href="https://filemimarlik.com" target="_blank" rel="noopener noreferrer">Fi-le Mimarlık & Yazılım</a>.</div>
    """,
    unsafe_allow_html=True,
)
