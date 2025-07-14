#!/usr/bin/env python3
"""
Simple Twitter Scraper Starter
"""

import sys
import subprocess
from config import get_config, print_config_summary

def check_dependencies():
    """Cek dependencies yang diperlukan"""
    required_packages = ['selenium', 'requests', 'pytz', 'webdriver_manager']
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Run: pip install -r requirements.txt")
        return False
    return True

def main():
    print("🚀 Twitter Scraper")
    print("=" * 30)
    
    # Quick dependency check
    if not check_dependencies():
        return
    
    # Show config
    try:
        config = get_config()
        print_config_summary(config)
        print("=" * 50)
    except Exception as e:
        print(f"❌ Config error: {e}")
        return
    
    # Start scraper directly
    try:
        subprocess.run([sys.executable, "selenium-scrapper.py"], check=True)
    except KeyboardInterrupt:
        print("\n⏹️ Scraper stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Scraper failed with exit code {e.returncode}")

if __name__ == "__main__":
    main()