"""
Konfigurasi untuk Twitter Scraper
Pisahkan konfigurasi dari kode utama untuk kemudahan maintenance
"""

import os
from typing import Dict, Any

# Konfigurasi default
DEFAULT_CONFIG: Dict[str, Any] = {
    # Twitter credentials
    "TWITTER_USERNAME": "@rey_misteria",
    "TWITTER_PASSWORD": "Shinkasen123.",
    "TARGET_PROFILE_URL": "https://x.com/GenshinImpactID",
    
    # Timing configuration
    "CHECK_INTERVAL_SECONDS": 60,
    "MIN_WAIT_SECONDS": 60,  # 60 detik
    "MAX_WAIT_SECONDS": 300,  # 61 detik
    "SELENIUM_TIMEOUT": 20,
    
    # WhatsApp Bot configuration
    "WHATSAPP_BOT_URL": "http://104.43.57.44:3000/kirim-pesan",
    "GROUP_ID": "120363417848982331@g.us",
    
    # Simple configuration
    "MAX_TWEETS_CHECK": 5,  # Selalu ambil 5 tweet terbaru
    
    # Data storage
    "TWEET_DATA_FILE": "scrapper/tweet_data.json",
    "LOG_LEVEL": "INFO",
    
    # Smart Scheduler configuration
    "USE_SMART_SCHEDULER": True,  # Gunakan smart scheduler
    "SCHEDULER_CHECK_INTERVAL": 60,  # Interval cek scheduler (detik)
    "TIMEZONE": "Asia/Jakarta",  # Timezone untuk scheduler
    
    # Legacy offline hours (tidak digunakan jika smart scheduler aktif)
    "OFFLINE_START_HOUR": 0,  # 00:00
    "OFFLINE_END_HOUR": 6,    # 06:00
    "OFFLINE_CHECK_INTERVAL": 30,  # menit
    
    # Cleanup configuration
    "MAX_STORED_TWEET_IDS": 1000,  # Maksimal ID tweet yang disimpan
}

def load_config_from_env() -> Dict[str, Any]:
    """
    Load konfigurasi dengan PRIORITAS MUTLAK config.py file
    Environment variables DIABAIKAN - config.py adalah sumber kebenaran tunggal
    """
    config = DEFAULT_CONFIG.copy()
    
    
    return config

def validate_config(config: Dict[str, Any]) -> bool:
    """
    Validasi konfigurasi untuk memastikan nilai yang valid
    """
    required_keys = [
        'TWITTER_USERNAME', 'TWITTER_PASSWORD', 'TARGET_PROFILE_URL',
        'WHATSAPP_BOT_URL', 'GROUP_ID'
    ]
    
    # Cek required keys
    for key in required_keys:
        if not config.get(key):
            print(f"Error: {key} tidak boleh kosong")
            return False
    
    # Validasi numeric values
    if config['MAX_TWEETS_CHECK'] != 5:
        print("Error: MAX_TWEETS_CHECK harus 5")
        return False
    
    if config['MIN_WAIT_SECONDS'] >= config['MAX_WAIT_SECONDS']:
        print("Error: MIN_WAIT_SECONDS harus < MAX_WAIT_SECONDS")
        return False
    
    # Validasi URL
    if not config['TARGET_PROFILE_URL'].startswith('https://x.com/'):
        print("Error: TARGET_PROFILE_URL harus berupa URL Twitter/X yang valid")
        return False
    
    if not config['WHATSAPP_BOT_URL'].startswith('http'):
        print("Error: WHATSAPP_BOT_URL harus berupa URL yang valid")
        return False
    
    return True

def get_config() -> Dict[str, Any]:
    """
    Mendapatkan konfigurasi final yang sudah divalidasi
    Prioritas: config.py file > environment variables (hanya untuk credentials)
    """
    config = load_config_from_env()
    
    if not validate_config(config):
        raise ValueError("Konfigurasi tidak valid")
    
    return config

def print_config_summary(config: Dict[str, Any]) -> None:
    """
    Tampilkan ringkasan konfigurasi (tanpa password)
    """
    print("📋 KONFIGURASI SCRAPER DENGAN SMART SCHEDULER")
    print("=" * 50)
    print(f"🎯 Target: {config['TARGET_PROFILE_URL']}")
    print(f"👤 Username: {config['TWITTER_USERNAME']}")
    print(f"📱 WhatsApp Group: {config['GROUP_ID']}")
    print(f"📊 Cek: {config['MAX_TWEETS_CHECK']} tweet terbaru setiap kali")
    print(f"⏰ Interval: {config['MIN_WAIT_SECONDS']}-{config['MAX_WAIT_SECONDS']} detik (random)")
    
    if config.get('USE_SMART_SCHEDULER', True):
        print(f"🤖 Smart Scheduler: AKTIF ({config.get('TIMEZONE', 'Asia/Jakarta')})")
        print(f"⏳ Check Interval: {config.get('SCHEDULER_CHECK_INTERVAL', 60)} detik")
        print("📅 Crawling hanya pada waktu tertentu untuk efisiensi")
    else:
        print(f"💤 Mode Legacy - Offline: {config['OFFLINE_START_HOUR']:02d}:00 - {config['OFFLINE_END_HOUR']:02d}:00")
    
    print("=" * 50)

if __name__ == "__main__":
    # Test konfigurasi
    try:
        config = get_config()
        print_config_summary(config)
        print("✅ Konfigurasi valid!")
    except Exception as e:
        print(f"❌ Error: {e}")