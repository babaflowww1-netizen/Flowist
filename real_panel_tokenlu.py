import os
from flask import Flask, render_template_string, request, redirect, url_for, session, jsonify
import sqlite3
import requests
import json
import re
from datetime import datetime
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

app = Flask(__name__)
app.secret_key = "real_panel_secret_key_2026_richy"
DB_NAME = "real_panel.db"

# ======================== VERİTABANI ========================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            gmail TEXT NOT NULL,
            alias TEXT,
            credits INTEGER DEFAULT 50,
            role TEXT DEFAULT 'Normal',
            avatar TEXT DEFAULT 'https://i.imgur.com/6VBx3io.png',
            last_query TEXT,
            query_count INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            credits INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS query_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            query_type TEXT,
            query_param TEXT,
            response TEXT,
            date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute("SELECT * FROM users WHERE username = 'kurucu'")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (username, password, gmail, alias, credits, role) VALUES (?, ?, ?, ?, ?, ?)",
                       ('kurucu', 'real12345', 'kurucu@realpanel.com', 'Richy Founder', 9999, 'Kurucu'))
    
    cursor.execute("SELECT * FROM announcements")
    if not cursor.fetchone():
        cursor.execute("INSERT INTO announcements (text) VALUES ('📢 Real Panel v2 aktif! Tüm API''ler entegre edilmiştir.')")
        
    conn.commit()
    conn.close()

init_db()

# ======================== API SINIFI ========================
class RealAPI:
    def __init__(self):
        self.base_urls = {
            "tc": "https://tara-api-systems.gt.tc/tc.php?tc={}",
            "adres": "https://tara-api-systems.gt.tc/adres.php?tc={}",
            "tcgsm": "https://tara-api-systems.gt.tc/tcgsm.php?tc={}",
            "isyeri": "https://tara-api-systems.gt.tc/isyeri.php?tc={}",
            "sulale": "https://tara-api-systems.gt.tc/sulale.php?tc={}",
            "adsoyad": "https://tara-api-systems.gt.tc/adsoyad.php?adi={}&soyadi={}&il={}&ilce={}",
            "gsmtc": "https://tara-api-systems.gt.tc/gsmtc.php?gsm={}",
            "iban": "https://rinexibansorguapi.rf.gd/api.php?iban={}",
            "plaka": "https://rinexplakasorguapi.gt.tc/api/plaka.php?endpoint=ara&q={}",
            "papara_id": "https://rinexpaparasorguapi.rf.gd/api/papara.php?id={}",
            "papara_name": "https://rinexpaparasorguapi.rf.gd/api/papara.php?name={}",
            "turktel_adsoyad": "https://rinexturktelekomapi.gt.tc/api/turktelekom.php?sorgu=adsoyad°er={}",
            "turktel_ad": "https://rinexturktelekomapi.gt.tc/api/turktelekom.php?sorgu=ad°er={}",
            "turktel_il": "https://rinexturktelekomapi.gt.tc/api/turktelekom.php?sorgu=il°er={}",
            "instagram": "https://rinexinstegramsorguapi.rf.gd/api/instagram.php?kullanici_adi={}",
            "secmen_tc": "https://rinexsecmensorguapu.gt.tc/api/secmen.php?action=tc&tc={}",
            "secmen_adsoyad": "https://rinexsecmensorguapu.gt.tc/api/secmen.php?action=adsoyad&ad={}&soyad={}",
            "yeniden_tc": "https://yeniden-sorguapileri.onrender.com/api/tc.php?tc={}",
            "yeniden_adsoyad": "https://yeniden-sorguapileri.onrender.com/api/adsoyad.php?adi={}&soyadi={}&il={}&ilce={}",
            "yeniden_adres": "https://yeniden-sorguapileri.onrender.com/api/adres.php?tc={}",
            "yeniden_gsmtc": "https://yeniden-sorguapileri.onrender.com/api/gsmtc.php?gsm={}",
            "yeniden_sulale": "https://yeniden-sorguapileri.onrender.com/api/sulale.php?tc={}",
            "illegalist": "https://api.illegalist.online/asi/?tc={}&auth=LegalistApiService",
            "marlex_sulale": "https://www.marlexnow.xyz/api/sulalee/api.php?tc={}&token=ozii31",
            "mariel_sulale": "http://mariel.fun/api/escobar/soyagaci.php?tc={}",
            "api_tc": "http://172.232.237.12/api/tc.php?tc={}",
            "api_tcpro": "http://172.232.237.12/api/tcpro.php?tc={}",
            "api_gsmtc": "http://172.232.237.12/api/gsmtc.php?gsm={}",
            "api_tcgsm": "http://172.232.237.12/api/tcgsm.php?tc={}",
            "api_tapu": "http://172.232.237.12/api/tapu.php?tc={}",
            "api_isyeri": "http://172.232.237.12/api/isyeri.php?tc={}",
            "api_akp": "http://172.232.237.12/api/akp.php?tc={}",
            "api_adres": "http://172.232.237.12/api/adres.php?tc={}",
            "api_hane": "http://172.232.237.12/api/Hane.php?tc={}",
            "api_aile": "http://172.232.237.12/api/aile.php?tc={}",
            "api_ailepro": "http://172.232.237.12/api/ailepro.php?tc={}",
            "api_soyagaci": "http://172.232.237.12/api/soyağacı.php?tc={}",
            "api_sulale": "http://172.232.237.12/api/sulale.php?tc={}",
            "api_sulalepro": "http://172.232.237.12/api/sulalepro.php?tc={}"
        }
    
    def _get(self, url, params=None):
        try:
            response = requests.get(url, timeout=15)
            if response.status_code == 200:
                return response.json() if response.headers.get('content-type') == 'application/json' else response.text
            return {"error": f"API hatası: {response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def sorgula(self, query_type, **kwargs):
        url_template = self.base_urls.get(query_type)
        if not url_template:
            return {"error": "Geçersiz sorgu tipi"}
        
        try:
            url = url_template.format(**kwargs)
        except KeyError as e:
            return {"error": f"Eksik parametre: {e}"}
        
        result = self._get(url)
        return {
            "query_type": query_type,
            "params": kwargs,
            "url": url,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }

API = RealAPI()

# ======================== HTML TEMPLATE ========================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real Panel - Telegram Mini App</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background-color: #0b0914; color: #f3f4f6; min-height: 100vh; display: flex; justify-content: center; align-items: center; }
        .app-container { width: 100%; max-width: 420px; background: #0b0914; min-height: 100vh; position: relative; overflow-x: hidden; display: flex; flex-direction: column; box-shadow: 0 0 30px rgba(138, 43, 226, 0.2); }
        .auth-screen { padding: 30px 20px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 100vh; text-align: center; }
        .logo-img { width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #8a2be2; box-shadow: 0 0 20px rgba(138,43,226,0.6); margin-bottom: 12px; }
        .brand-title { font-size: 26px; font-weight: 700; color: #fff; letter-spacing: 1px; margin-bottom: 8px; }
        .active-badge { display: inline-flex; align-items: center; gap: 6px; background: rgba(16, 185, 129, 0.15); color: #10b981; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; border: 1px solid rgba(16, 185, 129, 0.3); margin-bottom: 6px; }
        .active-dot { width: 7px; height: 7px; background: #10b981; border-radius: 50%; box-shadow: 0 0 8px #10b981; }
        .slogan { font-size: 11px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 25px; }
        .card { width: 100%; background: rgba(26, 22, 37, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(138, 43, 226, 0.3); border-radius: 16px; padding: 25px 20px; box-shadow: 0 8px 32px rgba(0,0,0,0.4); text-align: left; }
        .card h3 { font-size: 18px; margin-bottom: 6px; color: #fff; }
        .card p { font-size: 12px; color: #9ca3af; margin-bottom: 20px; }
        .input-group { position: relative; margin-bottom: 15px; }
        .input-group i { position: absolute; left: 14px; top: 50%; transform: translateY(-50%); color: #9ca3af; font-size: 14px; }
        .input-field { width: 100%; background: #13101d; border: 1px solid #2d2640; border-radius: 10px; padding: 12px 14px 12px 42px; color: #fff; font-size: 13px; transition: 0.3s; }
        .input-field:focus { border-color: #8a2be2; outline: none; box-shadow: 0 0 10px rgba(138,43,226,0.3); }
        .btn { width: 100%; background: linear-gradient(135deg, #7c3aed, #8a2be2); color: #fff; border: none; padding: 12px; border-radius: 10px; font-weight: 600; font-size: 14px; cursor: pointer; transition: 0.3s; box-shadow: 0 4px 15px rgba(138,43,226,0.4); }
        .btn:hover { opacity: 0.9; transform: translateY(-1px); }
        .switch-auth { margin-top: 15px; font-size: 12px; color: #9ca3af; text-align: center; }
        .switch-auth a { color: #a78bfa; text-decoration: none; font-weight: 600; }
        .dashboard-header { display: flex; justify-content: space-between; align-items: center; padding: 15px 20px; background: #13101d; border-bottom: 1px solid #2d2640; }
        .menu-btn { background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; }
        .header-brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; color: #fff; }
        .header-brand img { width: 28px; height: 28px; border-radius: 50%; }
        .marquee-container { background: #1a1625; color: #a78bfa; padding: 8px 0; overflow: hidden; white-space: nowrap; border-bottom: 1px solid #2d2640; font-size: 12px; font-weight: 500; }
        .marquee-content { display: inline-block; animation: marquee 18s linear infinite; }
        @keyframes marquee { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }
        .dashboard-body { padding: 15px; overflow-y: auto; flex: 1; padding-bottom: 30px; }
        .stats-row { display: flex; gap: 10px; margin-bottom: 15px; }
        .stat-card { flex: 1; background: #1a1625; border: 1px solid #2d2640; border-radius: 12px; padding: 12px; display: flex; align-items: center; gap: 10px; }
        .stat-card i { font-size: 20px; color: #a78bfa; }
        .stat-info span { font-size: 11px; color: #9ca3af; display: block; }
        .stat-info h4 { font-size: 14px; color: #fff; font-weight: 700; }
        .bonus-btn { width: 100%; background: linear-gradient(135deg, #059669, #10b981); color: #fff; border: none; padding: 10px; border-radius: 10px; font-weight: 600; font-size: 13px; cursor: pointer; margin-bottom: 20px; box-shadow: 0 4px 15px rgba(16,185,129,0.3); display: flex; align-items: center; justify-content: center; gap: 8px; }
        .section-title { font-size: 13px; font-weight: 600; color: #9ca3af; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }
        .queries-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin-bottom: 20px; }
        .query-card { background: #1a1625; border: 1px solid #2d2640; border-radius: 12px; padding: 15px; text-align: center; cursor: pointer; transition: 0.3s; position: relative; display: flex; flex-direction: column; align-items: center; gap: 8px; }
        .query-card:hover { border-color: #8a2be2; transform: translateY(-2px); box-shadow: 0 5px 15px rgba(138,43,226,0.2); }
        .query-card i { font-size: 22px; color: #a78bfa; margin-bottom: 4px; }
        .query-card span { font-size: 12px; font-weight: 600; color: #fff; }
        .vip-tag { position: absolute; top: 8px; right: 8px; background: linear-gradient(135deg, #f59e0b, #d97706); color: #fff; font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 6px; box-shadow: 0 2px 6px rgba(245,158,11,0.4); }
        .sidebar { position: fixed; top: 0; left: -100%; width: 280px; height: 100%; background: #13101d; z-index: 1000; transition: 0.3s ease; border-right: 1px solid #2d2640; display: flex; flex-direction: column; }
        .sidebar.active { left: 0; }
        .sidebar-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.6); z-index: 999; display: none; }
        .sidebar-overlay.active { display: block; }
        .profile-section { padding: 20px; background: #1a1625; border-bottom: 1px solid #2d2640; text-align: left; display: flex; align-items: center; gap: 12px; }
        .profile-avatar { width: 50px; height: 50px; border-radius: 10px; object-fit: cover; border: 2px solid #8a2be2; }
        .profile-info h4 { font-size: 14px; font-weight: 700; color: #fff; }
        .profile-info p { font-size: 11px; color: #10b981; display: flex; align-items: center; gap: 4px; margin-top: 2px; }
        .sidebar-menu { padding: 15px; flex: 1; overflow-y: auto; }
        .sidebar-item { display: flex; align-items: center; justify-content: space-between; padding: 12px 15px; color: #d1d5db; text-decoration: none; border-radius: 10px; font-size: 13px; font-weight: 500; margin-bottom: 5px; transition: 0.2s; }
        .sidebar-item:hover { background: #1a1625; color: #fff; }
        .sidebar-item-left { display: flex; align-items: center; gap: 12px; }
        .sidebar-item i { font-size: 16px; color: #a78bfa; }
        .badge-pill { padding: 2px 6px; border-radius: 4px; font-size: 9px; font-weight: 700; text-transform: uppercase; }
        .badge-kurucu { background: #dc2626; color: #fff; }
        .badge-admin { background: #2563eb; color: #fff; }
        .badge-vip { background: #d97706; color: #fff; }
        .badge-normal { background: #4b5563; color: #fff; }
        .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 1100; justify-content: center; align-items: center; padding: 20px; }
        .modal-content { background: #161221; border: 1px solid #2d2640; border-radius: 16px; width: 100%; max-width: 360px; padding: 20px; position: relative; max-height: 90vh; overflow-y: auto; }
        .close-modal { position: absolute; top: 15px; right: 15px; background: none; border: none; color: #9ca3af; font-size: 18px; cursor: pointer; }
        .alert { padding: 10px; border-radius: 8px; font-size: 12px; margin-bottom: 15px; text-align: center; }
        .alert-success { background: rgba(16,185,129,0.15); color: #10b981; border: 1px solid rgba(16,185,129,0.3); }
        .alert-error { background: rgba(239,68,68,0.15); color: #ef4444; border: 1px solid rgba(239,68,68,0.3); }
        #queryResult { background: #13101d; border-radius: 8px; padding: 12px; border: 1px solid #2d2640; max-height: 200px; overflow-y: auto; margin-top: 10px; white-space: pre-wrap; word-break: break-all; font-size: 12px; display: none; }
    </style>
</head>
<body>

<div class="app-container">
    {% if not session.get('user_id') %}
    <div class="auth-screen">
        <img src="https://i.imgur.com/6VBx3io.png" alt="Logo" class="logo-img">
        <h1 class="brand-title">Real Panel</h1>
        <div class="active-badge"><span class="active-dot"></span>7/24 AKTİF</div>
        <div class="slogan">TÜRKİYE'NİN EN GELİŞMİŞ SORGU PLATFORMU</div>
        <div class="card">
            <h3>{% if is_register %}Kayıt Ol{% else %}Giriş Yap{% endif %}</h3>
            <p>{% if is_register %}Yeni hesap oluştur ve sorgulamaya başla.{% else %}Hesabına giriş yap ve sorgulamaya başla.{% endif %}</p>
            {% if error %}<div class="alert alert-error">{{ error }}</div>{% endif %}
            {% if success %}<div class="alert alert-success">{{ success }}</div>{% endif %}
            <form method="POST" action="{% if is_register %}/register{% else %}/login{% endif %}">
                <div class="input-group"><i class="fa-solid fa-user"></i><input type="text" name="username" class="input-field" placeholder="Kullanıcı Adı" required></div>
                {% if is_register %}<div class="input-group"><i class="fa-solid fa-envelope"></i><input type="email" name="gmail" class="input-field" placeholder="Gmail Adresi" required></div>{% endif %}
                <div class="input-group"><i class="fa-solid fa-lock"></i><input type="password" name="password" class="input-field" placeholder="Şifre" required></div>
                <button type="submit" class="btn">{% if is_register %}Kayıt Ol{% else %}Giriş Yap{% endif %} →</button>
            </form>
            <div class="switch-auth">
                {% if is_register %}Zaten hesabın var mı? <a href="/">Giriş Yap</a>
                {% else %}Hesabın yok mu? <a href="/register_view">Kayıt Ol</a>{% endif %}
            </div>
        </div>
    </div>
    {% else %}
    <div class="dashboard-header">
        <button class="menu-btn" onclick="toggleSidebar()"><i class="fa-solid fa-bars"></i></button>
        <div class="header-brand"><img src="{{ user.avatar }}" alt="Logo"> Real Panel</div>
        <div style="width:20px;"></div>
    </div>
    <div class="marquee-container"><div class="marquee-content">📢 {{ announcement }} &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 🚀 TÜRKİYE'NİN LİDER SORGU PLATFORMU 7/24 HİZMETİNİZDE!</div></div>
    <div class="dashboard-body">
        <div class="stats-row">
            <div class="stat-card"><i class="fa-solid fa-coins"></i><div class="stat-info"><span>Kalan Kredi</span><h4>{{ user.credits }} Kredi</h4></div></div>
            <div class="stat-card"><i class="fa-solid fa-shield-halved"></i><div class="stat-info"><span>Üyelik Tipi</span><h4>{{ user.role }}</h4></div></div>
        </div>
        <form method="POST" action="/daily_bonus"><button type="submit" class="bonus-btn"><i class="fa-solid fa-gift"></i> Günlük Bonus Al (+10 Kredi)</button></form>
        <div class="section-title">Sorgu Kategorileri</div>
        <div class="queries-grid">
            <div class="query-card" onclick="openQueryModal('tc', 'TC Sorgu')"><i class="fa-solid fa-id-card"></i><span>TC Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('adres', 'Adres Sorgu')"><i class="fa-solid fa-map-location-dot"></i><span>Adres Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('tcgsm', 'TC\'den GSM')"><i class="fa-solid fa-phone"></i><span>TC'den GSM</span></div>
            <div class="query-card" onclick="openQueryModal('gsmtc', 'GSM\'den TC')"><i class="fa-solid fa-mobile-screen"></i><span>GSM'den TC</span></div>
            <div class="query-card" onclick="openQueryModal('isyeri', 'İş Yeri Sorgu')"><i class="fa-solid fa-briefcase"></i><span>İş Yeri Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('sulale', 'Sülale Sorgu (VIP)')"><div class="vip-tag">VIP</div><i class="fa-solid fa-users"></i><span>Sülale Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('adsoyad', 'Ad Soyad Sorgu')"><i class="fa-solid fa-address-book"></i><span>Ad Soyad Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('hane', 'Hane Sorgu')"><i class="fa-solid fa-people-roof"></i><span>Hane Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('api_tapu', 'Tapu Sorgu (VIP)')"><div class="vip-tag">VIP</div><i class="fa-solid fa-house-chimney"></i><span>Tapu Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('api_aile', 'Aile Sorgu (VIP)')"><div class="vip-tag">VIP</div><i class="fa-solid fa-people-arrows"></i><span>Aile Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('api_soyagaci', 'Soyağacı (VIP)')"><div class="vip-tag">VIP</div><i class="fa-solid fa-tree"></i><span>Soyağacı</span></div>
            <div class="query-card" onclick="openQueryModal('api_sulale', 'Sülale Pro')"><i class="fa-solid fa-users-gear"></i><span>Sülale Pro</span></div>
            <div class="query-card" onclick="openQueryModal('secmen_tc', 'Seçmen Sorgu (TC)')"><i class="fa-solid fa-check-to-slot"></i><span>Seçmen (TC)</span></div>
            <div class="query-card" onclick="openQueryModal('secmen_adsoyad', 'Seçmen (Ad-Soyad)')"><i class="fa-solid fa-check-to-slot"></i><span>Seçmen (Ad-Soyad)</span></div>
            <div class="query-card" onclick="openQueryModal('illegalist', 'Legalist TC')"><i class="fa-solid fa-scale-balanced"></i><span>Legalist TC</span></div>
            <div class="query-card" onclick="openQueryModal('marlex_sulale', 'Marlex Sülale')"><i class="fa-solid fa-link"></i><span>Marlex Sülale</span></div>
            <div class="query-card" onclick="openQueryModal('mariel_sulale', 'Mariel Soyağacı')"><i class="fa-solid fa-link"></i><span>Mariel Soyağacı</span></div>
            <div class="query-card" onclick="openQueryModal('papara_id', 'Papara ID Sorgu')"><i class="fa-solid fa-money-bill-transfer"></i><span>Papara ID</span></div>
            <div class="query-card" onclick="openQueryModal('papara_name', 'Papara İsim Sorgu')"><i class="fa-solid fa-money-bill-transfer"></i><span>Papara İsim</span></div>
            <div class="query-card" onclick="openQueryModal('instagram', 'Instagram Sorgu')"><i class="fa-brands fa-instagram"></i><span>Instagram Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('plaka', 'Plaka Sorgu')"><i class="fa-solid fa-car"></i><span>Plaka Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('iban', 'IBAN Sorgu')"><i class="fa-solid fa-building-columns"></i><span>IBAN Sorgu</span></div>
            <div class="query-card" onclick="openQueryModal('turktel_adsoyad', 'TT Ad-Soyad')"><i class="fa-solid fa-tower-cell"></i><span>TT Ad-Soyad</span></div>
            <div class="query-card" onclick="openQueryModal('turktel_ad', 'TT Ad')"><i class="fa-solid fa-tower-cell"></i><span>TT Ad</span></div>
            <div class="query-card" onclick="openQueryModal('turktel_il', 'TT İl')"><i class="fa-solid fa-tower-cell"></i><span>TT İl</span></div>
            <div class="query-card" onclick="openQueryModal('api_akp', 'AKP Sorgu')"><i class="fa-solid fa-landmark"></i><span>AKP Sorgu</span></div>
        </div>
        {% if query_result %}
        <div style="background:#1a1625;border:1px solid #10b981;border-radius:12px;padding:15px;margin-top:10px;">
            <h4 style="color:#10b981;">✅ Sorgu Sonucu</h4>
            <pre style="color:#d1d5db;font-size:12px;white-space:pre-wrap;word-break:break-all;">{{ query_result.result | tojson(indent=2) }}</pre>
        </div>
        {% endif %}
    </div>
    
    <div class="sidebar-overlay" id="sidebarOverlay" onclick="toggleSidebar()"></div>
    <div class="sidebar" id="sidebar">
        <div class="profile-section">
            <img src="{{ user.avatar }}" alt="Avatar" class="profile-avatar">
            <div class="profile-info">
                <h4>{{ user.alias or user.username }}</h4>
                <p><span style="width:6px;height:6px;background:#10b981;border-radius:50%;display:inline-block;"></span> Çevrimiçi</p>
                <div style="margin-top:4px;">
                    {% if user.role == 'Kurucu' %}<span class="badge-pill badge-kurucu">Kurucu</span>
                    {% elif user.role == 'Admin' %}<span class="badge-pill badge-admin">Admin</span>
                    {% elif user.role == 'VIP' %}<span class="badge-pill badge-vip">VIP Üye</span>
                    {% else %}<span class="badge-pill badge-normal">Standart</span>{% endif %}
                </div>
            </div>
        </div>
        <div class="sidebar-menu">
            <a href="#" class="sidebar-item" onclick="toggleSidebar()"><div class="sidebar-item-left"><i class="fa-solid fa-house" style="color:#8a2be2;"></i> Ana Sayfa</div></a>
            <a href="#" class="sidebar-item" onclick="openModal('profileModal')"><div class="sidebar-item-left"><i class="fa-solid fa-user-gear" style="color:#3b82f6;"></i> Profili Düzenle</div></a>
            <a href="#" class="sidebar-item" onclick="openModal('couponModal')"><div class="sidebar-item-left"><i class="fa-solid fa-ticket" style="color:#d97706;"></i> Kupon Kodu Kullan</div></a>
            {% if user.role in ['Kurucu', 'Admin'] %}
            <div style="font-size:11px;color:#9ca3af;margin:15px 0 5px 5px;text-transform:uppercase;font-weight:700;">Yönetim</div>
            <a href="#" class="sidebar-item" onclick="openModal('adminModal')"><div class="sidebar-item-left"><i class="fa-solid fa-shield-halved" style="color:#ef4444;"></i> Admin Paneli</div></a>
            {% endif %}
            <a href="/logout" class="sidebar-item" style="margin-top:20px;color:#ef4444;"><div class="sidebar-item-left"><i class="fa-solid fa-right-from-bracket" style="color:#ef4444;"></i> Çıkış Yap</div></a>
        </div>
    </div>
    
    <div class="modal" id="profileModal">
        <div class="modal-content">
            <button class="close-modal" onclick="closeModal('profileModal')">&times;</button>
            <h3 style="margin-bottom:15px;color:#fff;">Profili Düzenle</h3>
            <form method="POST" action="/update_profile">
                <div class="input-group"><i class="fa-solid fa-signature"></i><input type="text" name="alias" class="input-field" placeholder="Takma Ad" value="{{ user.alias or '' }}"></div>
                <div class="input-group"><i class="fa-solid fa-envelope"></i><input type="email" name="gmail" class="input-field" placeholder="Gmail Adresi" value="{{ user.gmail }}" required></div>
                <div class="input-group"><i class="fa-solid fa-image"></i><input type="text" name="avatar" class="input-field" placeholder="Avatar URL" value="{{ user.avatar }}"></div>
                <div class="input-group"><i class="fa-solid fa-lock"></i><input type="password" name="password" class="input-field" placeholder="Yeni Şifre (İsteğe bağlı)"></div>
                <button type="submit" class="btn">Güncelle</button>
            </form>
        </div>
    </div>
    
    <div class="modal" id="couponModal">
        <div class="modal-content">
            <button class="close-modal" onclick="closeModal('couponModal')">&times;</button>
            <h3 style="margin-bottom:15px;color:#fff;">Kupon Kodu Kullan</h3>
            <form method="POST" action="/use_coupon">
                <div class="input-group"><i class="fa-solid fa-ticket"></i><input type="text" name="code" class="input-field" placeholder="Kupon Kodunu Girin" required></div>
                <button type="submit" class="btn">Kodu Kullan</button>
            </form>
        </div>
    </div>
    
    <div class="modal" id="queryModal">
        <div class="modal-content">
            <button class="close-modal" onclick="closeModal('queryModal')">&times;</button>
            <h3 id="queryTitle" style="margin-bottom:10px;color:#fff;">Sorgu</h3>
            <form method="POST" action="/query">
                <input type="hidden" name="query_type" id="queryType">
                <div id="queryParams"></div>
                <button type="submit" class="btn" style="margin-top:10px;">Sorgula →</button>
            </form>
            <div id="queryResult"></div>
        </div>
    </div>
    
    {% if user.role in ['Kurucu', 'Admin'] %}
    <div class="modal" id="adminModal">
        <div class="modal-content" style="max-width:380px;">
            <button class="close-modal" onclick="closeModal('adminModal')">&times;</button>
            <h3 style="margin-bottom:15px;color:#f59e0b;"><i class="fa-solid fa-shield"></i> Yönetici Paneli</h3>
            <form method="POST" action="/admin_announcement" style="margin-bottom:15px;">
                <label style="font-size:11px;color:#9ca3af;display:block;margin-bottom:5px;">Duyuru Metnini Düzenle</label>
                <div class="input-group"><input type="text" name="announcement" class="input-field" value="{{ announcement }}" required style="padding-left:14px;"></div>
                <button type="submit" class="btn" style="padding:8px;font-size:12px;">Duyuruyu Güncelle</button>
            </form>
            <form method="POST" action="/admin_coupon" style="margin-bottom:15px;">
                <label style="font-size:11px;color:#9ca3af;display:block;margin-bottom:5px;">Yeni Kupon Oluştur</label>
                <div class="input-group" style="margin-bottom:8px;"><input type="text" name="code" class="input-field" placeholder="Kupon Kodu" required style="padding-left:14px;"></div>
                <div class="input-group" style="margin-bottom:8px;"><input type="number" name="credits" class="input-field" placeholder="Kredi Miktarı" required style="padding-left:14px;"></div>
                <button type="submit" class="btn" style="padding:8px;font-size:12px;">Kupon Üret</button>
            </form>
            <form method="POST" action="/admin_credits">
                <label style="font-size:11px;color:#9ca3af;display:block;margin-bottom:5px;">Kullanıcıya Kredi Ekle</label>
                <div class="input-group" style="margin-bottom:8px;"><input type="text" name="target_user" class="input-field" placeholder="Kullanıcı Adı" required style="padding-left:14px;"></div>
                <div class="input-group" style="margin-bottom:8px;"><input type="number" name="add_credits" class="input-field" placeholder="Eklenecek Kredi" required style="padding-left:14px;"></div>
                <button type="submit" class="btn" style="padding:8px;font-size:12px;">Kredi Tanımla</button>
            </form>
        </div>
    </div>
    {% endif %}
    
    <script>
        function toggleSidebar() {
            document.getElementById('sidebar').classList.toggle('active');
            document.getElementById('sidebarOverlay').classList.toggle('active');
        }
        function openModal(id) {
            document.getElementById(id).style.display = 'flex';
            toggleSidebar();
        }
        function closeModal(id) {
            document.getElementById(id).style.display = 'none';
        }
        
        function openQueryModal(type, title) {
            document.getElementById('queryType').value = type;
            document.getElementById('queryTitle').innerText = title;
            const paramsDiv = document.getElementById('queryParams');
            paramsDiv.innerHTML = '';
            document.getElementById('queryResult').style.display = 'none';
            document.getElementById('queryResult').innerHTML = '';
            
            const paramConfig = {
                'tc': [{name:'tc', label:'TC Kimlik No'}],
                'adres': [{name:'tc', label:'TC Kimlik No'}],
                'tcgsm': [{name:'tc', label:'TC Kimlik No'}],
                'gsmtc': [{name:'gsm', label:'GSM No'}],
                'isyeri': [{name:'tc', label:'TC Kimlik No'}],
                'sulale': [{name:'tc', label:'TC Kimlik No'}],
                'adsoyad': [{name:'adi', label:'Ad'},{name:'soyadi', label:'Soyad'},{name:'il', label:'İl'},{name:'ilce', label:'İlçe'}],
                'hane': [{name:'tc', label:'TC Kimlik No'}],
                'instagram': [{name:'kullanici_adi', label:'Instagram Kullanıcı Adı'}],
                'plaka': [{name:'plaka', label:'Plaka'}],
                'iban': [{name:'iban', label:'IBAN'}],
                'turktel_adsoyad': [{name:'adsoyad', label:'Ad Soyad'}],
                'turktel_ad': [{name:'ad', label:'Ad'}],
                'turktel_il': [{name:'il', label:'İl'}],
                'papara_id': [{name:'id', label:'Papara ID'}],
                'papara_name': [{name:'name', label:'Papara İsim'}],
                'secmen_tc': [{name:'tc', label:'TC Kimlik No'}],
                'secmen_adsoyad': [{name:'ad', label:'Ad'},{name:'soyad', label:'Soyad'}],
                'illegalist': [{name:'tc', label:'TC Kimlik No'}],
                'marlex_sulale': [{name:'tc', label:'TC Kimlik No'}],
                'mariel_sulale': [{name:'tc', label:'TC Kimlik No'}],
                'api_tapu': [{name:'tc', label:'TC Kimlik No'}],
                'api_aile': [{name:'tc', label:'TC Kimlik No'}],
                'api_soyagaci': [{name:'tc', label:'TC Kimlik No'}],
                'api_sulale': [{name:'tc', label:'TC Kimlik No'}],
                'api_tc': [{name:'tc', label:'TC Kimlik No'}],
                'api_tcpro': [{name:'tc', label:'TC Kimlik No'}],
                'api_gsmtc': [{name:'gsm', label:'GSM No'}],
                'api_tcgsm': [{name:'tc', label:'TC Kimlik No'}],
                'api_isyeri': [{name:'tc', label:'TC Kimlik No'}],
                'api_akp': [{name:'tc', label:'TC Kimlik No'}],
                'api_adres': [{name:'tc', label:'TC Kimlik No'}],
                'api_hane': [{name:'tc', label:'TC Kimlik No'}],
                'api_ailepro': [{name:'tc', label:'TC Kimlik No'}],
                'api_sulalepro': [{name:'tc', label:'TC Kimlik No'}]
            };
            
            const params = paramConfig[type] || [{name:'param', label:'Parametre'}];
            params.forEach(p => {
                const div = document.createElement('div');
                div.className = 'input-group';
                const icon = p.name === 'tc' ? 'id-card' : p.name === 'gsm' ? 'phone' : 'search';
                div.innerHTML = `<i class="fa-solid fa-${icon}"></i><input type="text" name="${p.name}" class="input-field" placeholder="${p.label}" required>`;
                paramsDiv.appendChild(div);
            });
            
            document.getElementById('queryModal').style.display = 'flex';
        }
    </script>
    {% endif %}
</div>
</body>
</html>
'''

# ======================== FLASK ROTALARI ========================
@app.route('/')
def index():
    if 'user_id' in session:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()
        cursor.execute("SELECT text FROM announcements ORDER BY id DESC LIMIT 1")
        ann = cursor.fetchone()
        conn.close()
        return render_template_string(HTML_TEMPLATE, user=user, announcement=ann['text'] if ann else '', query_result=None)
    return render_template_string(HTML_TEMPLATE, is_register=False)

@app.route('/register_view')
def register_view():
    return render_template_string(HTML_TEMPLATE, is_register=True)

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    user = cursor.fetchone()
    conn.close()
    if user:
        session['user_id'] = user['id']
        return redirect(url_for('index'))
    else:
        return render_template_string(HTML_TEMPLATE, is_register=False, error="Hatalı kullanıcı adı veya şifre!")

@app.route('/register', methods=['POST'])
def register():
    username = request.form.get('username')
    gmail = request.form.get('gmail')
    password = request.form.get('password')
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO users (username, password, gmail, credits, role) VALUES (?, ?, ?, ?, ?)",
                       (username, password, gmail, 50, 'Normal'))
        conn.commit()
        conn.close()
        return render_template_string(HTML_TEMPLATE, is_register=False, success="Kayıt başarılı! Şimdi giriş yapabilirsiniz.")
    except sqlite3.IntegrityError:
        conn.close()
        return render_template_string(HTML_TEMPLATE, is_register=True, error="Bu kullanıcı adı zaten alınmış!")

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route('/daily_bonus', methods=['POST'])
def daily_bonus():
    if 'user_id' in session:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET credits = credits + 10 WHERE id = ?", (session['user_id'],))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_id' in session:
        alias = request.form.get('alias')
        gmail = request.form.get('gmail')
        avatar = request.form.get('avatar')
        password = request.form.get('password')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        if password:
            cursor.execute("UPDATE users SET alias = ?, gmail = ?, avatar = ?, password = ? WHERE id = ?",
                           (alias, gmail, avatar, password, session['user_id']))
        else:
            cursor.execute("UPDATE users SET alias = ?, gmail = ?, avatar = ? WHERE id = ?",
                           (alias, gmail, avatar, session['user_id']))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/use_coupon', methods=['POST'])
def use_coupon():
    if 'user_id' in session:
        code = request.form.get('code')
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM coupons WHERE code = ?", (code,))
        coupon = cursor.fetchone()
        if coupon:
            cursor.execute("UPDATE users SET credits = credits + ? WHERE id = ?", (coupon['credits'], session['user_id']))
            cursor.execute("DELETE FROM coupons WHERE id = ?", (coupon['id'],))
            conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/admin_announcement', methods=['POST'])
def admin_announcement():
    if 'user_id' in session:
        new_text = request.form.get('announcement')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO announcements (text) VALUES (?)", (new_text,))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/admin_coupon', methods=['POST'])
def admin_coupon():
    if 'user_id' in session:
        code = request.form.get('code')
        credits = request.form.get('credits')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO coupons (code, credits) VALUES (?, ?)", (code, credits))
            conn.commit()
        except:
            pass
        conn.close()
    return redirect(url_for('index'))

@app.route('/admin_credits', methods=['POST'])
def admin_credits():
    if 'user_id' in session:
        target_user = request.form.get('target_user')
        add_credits = request.form.get('add_credits')
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET credits = credits + ? WHERE username = ?", (add_credits, target_user))
        conn.commit()
        conn.close()
    return redirect(url_for('index'))

@app.route('/query', methods=['POST'])
def query():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    query_type = request.form.get('query_type')
    params = {}
    for key in request.form:
        if key != 'query_type' and request.form[key]:
            params[key] = request.form[key]
    
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT credits, role FROM users WHERE id = ?", (session['user_id'],))
    user = cursor.fetchone()
    
    vip_queries = ['sulale', 'api_tapu', 'api_aile', 'api_soyagaci', 'api_sulale', 'api_sulalepro', 'marlex_sulale', 'mariel_sulale']
    cost = 15 if query_type in vip_queries else 5
    
    if user['credits'] < cost:
        conn.close()
        return render_template_string(HTML_TEMPLATE, user=user, error=f"Yetersiz kredi! {cost} kredi gerekli.")
    
    result = API.sorgula(query_type, **params)
    
    cursor.execute("UPDATE users SET credits = credits - ?, query_count = query_count + 1, last_query = ? WHERE id = ?", 
                   (cost, datetime.now().isoformat(), session['user_id']))
    cursor.execute("INSERT INTO query_logs (user_id, query_type, query_param, response) VALUES (?, ?, ?, ?)",
                   (session['user_id'], query_type, str(params), str(result.get('result', ''))[:500]))
    conn.commit()
    
    cursor.execute("SELECT * FROM users WHERE id = ?", (session['user_id'],))
    user_updated = cursor.fetchone()
    conn.close()
    
    return render_template_string(HTML_TEMPLATE, user=user_updated, query_result=result, announcement="")

# ======================== TELEGRAM BOTU ========================
TOKEN = "8933323448:AAE2_xRM6xwlV-aXs1Y1cd-BVeDVhuuaOBU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    web_app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:5000")
    keyboard = [[InlineKeyboardButton("🚀 Real Panel'i Aç", web_app=WebAppInfo(url=web_app_url))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 **Real Panel'e Hoş Geldiniz!**\n\nTürkiye'nin en gelişmiş sorgu platformuna erişmek için aşağıdaki butonlu menüyü kullanabilirsiniz.",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

def run_telegram_bot():
    if TOKEN == "BURAYA_TELEGRAM_BOT_TOKENINI_YAZ":
        print("⚠️ Telegram bot token girilmediği için bot başlatılamadı, sadece Flask paneli çalışıyor.")
        return
    bot_app = ApplicationBuilder().token(TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    print("🤖 Telegram bot arka planda çalıştırılıyor...")
    bot_app.run_polling()

# ======================== ÇALIŞTIRMA ========================
if __name__ == '__main__':
    # Telegram botunu ayrı bir thread içinde başlatıyoruz ki Flask ile çakışmasın
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.daemon = True
    bot_thread.start()

    print("🚀 Real Panel Flask sunucusu başlatılıyor... http://127.0.0.1:5000")
    app.run(debug=False, port=5000, host="0.0.0.0")
