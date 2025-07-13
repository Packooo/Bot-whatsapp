import time
import requests
import logging
import datetime
import pytz # type: ignore
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Konfigurasi Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Konfigurasi Scraper ---
CONFIG = {
    "TWITTER_USERNAME": "@rey_misteria",
    "TWITTER_PASSWORD": "Shinkasen123.",
    "TARGET_PROFILE_URL": "https://x.com/wijay820",
    "CHECK_INTERVAL_SECONDS": 60, # Direkomendasikan 
    "MIN_WAIT_SECONDS": 300,
    "MAX_WAIT_SECONDS": 600,
    "WHATSAPP_BOT_URL": "http://localhost:3000/kirim-pesan",
    "GROUP_ID": "120363417848982331@g.us",
    "SELENIUM_TIMEOUT": 20
}

class TwitterScraper:
    def __init__(self, config):
        self.config = config
        self.driver = self._setup_driver()
        self.last_tweet_text = "" # <-- Kembali menyimpan teks

    def _setup_driver(self):
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        try:
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            return driver
        except Exception as e:
            logging.error(f"Gagal menginisialisasi WebDriver: {e}")
            raise

    def login(self):
        try:
            logging.info("Mencoba login ke Twitter...")
            self.driver.get("https://x.com/login")
            username_input = WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(EC.presence_of_element_located((By.NAME, "text")))
            username_input.send_keys(self.config["TWITTER_USERNAME"])
            self.driver.find_element(By.XPATH, '//span[text()="Next"]').click()
            password_input = WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(EC.presence_of_element_located((By.NAME, "password")))
            password_input.send_keys(self.config["TWITTER_PASSWORD"])
            self.driver.find_element(By.XPATH, '//span[text()="Log in"]').click()
            WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(EC.presence_of_element_located((By.XPATH, '//a[@data-testid="AppTabBar_Home_Link"]')))
            logging.info("Login berhasil!")
            return True
        except Exception as e:
            logging.error(f"Terjadi error saat login: {e}")
            return False

    def get_second_tweet_info(self):
        """Mengambil info dari TWEET KEDUA di halaman profil."""
        try:
            logging.info(f"Mengunjungi profil: {self.config['TARGET_PROFILE_URL']}")
            self.driver.get(self.config['TARGET_PROFILE_URL'])

            tweet_selector = 'article[data-testid="tweet"]'
            all_tweets = WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, tweet_selector))
            )
            
            # Asumsi: Selalu ada pinned post, jadi tweet terbaru adalah di posisi kedua.
            if len(all_tweets) < 2:
                logging.warning("Tidak ditemukan cukup tweet (kurang dari 2). Tidak ada yang diproses.")
                return None

            second_tweet_element = all_tweets[1] # Langsung ambil tweet kedua
            
            tweet_text = second_tweet_element.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]').text
            image_url = self._find_image_url(second_tweet_element)

            return {
                "text": tweet_text,
                "image": image_url
            }

        except Exception as e:
            logging.error(f"Gagal mengambil tweet kedua: {e}", exc_info=True)
            return None

    def _find_image_url(self, tweet_element):
        try:
            images = tweet_element.find_elements(By.TAG_NAME, 'img')
            for img in images:
                src = img.get_attribute('src')
                if src and 'pbs.twimg.com/media' in src:
                    return src
            return None
        except Exception:
            return None

    def _send_to_whatsapp(self, message, image_url):
        payload = {'groupId': self.config['GROUP_ID'], 'message': message, 'imageUrl': image_url}
        try:
            requests.post(self.config['WHATSAPP_BOT_URL'], json=payload, timeout=10)
            logging.info("Data telah dikirim ke bot WhatsApp.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Gagal mengirim data ke bot WhatsApp: {e}")

    def run(self):
        """Menjalankan loop utama scraper."""
        if self.login():
            while True:

                # Tentukan zona waktu Jakarta
                jakarta_tz = pytz.timezone('Asia/Jakarta')
                now_jakarta = datetime.datetime.now(jakarta_tz)
                
                
                # Cek apakah jam saat ini antara 00:00 (inklusif) dan 06:00 (eksklusif)
                if 0 <= now_jakarta.hour < 6:
                    offline_sleep_minutes = 30
                    logging.info(
                        f"Jam {now_jakarta.strftime('%H:%M:%S')} WIB. "
                        f"Bot dalam mode offline. Akan dicek lagi dalam {offline_sleep_minutes} menit."
                    )
                    time.sleep(offline_sleep_minutes * 60)
                    continue  # Kembali ke awal loop untuk cek waktu lagi
                
                
                logging.info("Mencari tweet terbaru (di posisi kedua)...")
                tweet_info = self.get_second_tweet_info()

                if tweet_info and tweet_info["text"] != self.last_tweet_text:
                    logging.info(f">>> Tweet baru ditemukan! Teks: {tweet_info['text'][:70]}...")
                    self.last_tweet_text = tweet_info["text"] # Update dengan teks baru
                    self._send_to_whatsapp(tweet_info["text"], tweet_info["image"])
                else:
                    logging.info("Tidak ada tweet baru.")
                
                min_wait = self.config['MIN_WAIT_SECONDS']
                max_wait = self.config['MAX_WAIT_SECONDS']
                
                random_wait = random.randint(min_wait, max_wait)
                
                logging.info(f"Menunggu selama {random_wait} detik...")
                time.sleep(random_wait)

    def close(self):
        """Menutup WebDriver."""
        if self.driver:
            self.driver.quit()
            logging.info("WebDriver ditutup.")

if __name__ == "__main__":
    scraper = None
    try:
        scraper = TwitterScraper(CONFIG)
        scraper.run()
    except Exception as e:
        logging.critical(f"Terjadi error kritis pada scraper: {e}")
    finally:
        if scraper:
            scraper.close()