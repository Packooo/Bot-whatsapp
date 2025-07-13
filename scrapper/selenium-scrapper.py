import time
import requests
import logging
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
    "TWITTER_USERNAME": "@rey_misteria",  # Ganti dengan username akun "korban"
    "TWITTER_PASSWORD": "Shinkasen123.",  # Ganti dengan passwordnya
    "TARGET_PROFILE_URL": "https://x.com/wijay820",  # Ganti dengan URL profil target
    "CHECK_INTERVAL_SECONDS": 60,  # Interval pengecekan dalam detik
    "WHATSAPP_BOT_URL": "http://localhost:3000/kirim-pesan",
    "GROUP_ID": "120363417848982331@g.us",
    "SELENIUM_TIMEOUT": 20
}

class TwitterScraper:
    """
    Sebuah kelas untuk melakukan scraping postingan terbaru dari profil Twitter
    dan mengirimkannya ke bot WhatsApp.
    """
    def __init__(self, config):
        self.config = config
        self.driver = self._setup_driver()
        self.last_tweet_text = ""

    def _setup_driver(self):
        """Menginisialisasi Chrome WebDriver."""
        options = webdriver.ChromeOptions()
        # options.add_argument('--headless')  # Aktifkan untuk mode tanpa UI
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
        """Melakukan proses login ke akun Twitter."""
        try:
            logging.info("Mencoba login ke Twitter...")
            self.driver.get("https://x.com/login")

            # Isi username
            username_input = WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(
                EC.presence_of_element_located((By.NAME, "text"))
            )
            username_input.send_keys(self.config["TWITTER_USERNAME"])
            self.driver.find_element(By.XPATH, '//span[text()="Next"]').click()

            # Isi password
            password_input = WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(
                EC.presence_of_element_located((By.NAME, "password"))
            )
            password_input.send_keys(self.config["TWITTER_PASSWORD"])
            self.driver.find_element(By.XPATH, '//span[text()="Log in"]').click()

            # Tunggu hingga halaman utama muncul
            WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(
                EC.presence_of_element_located((By.XPATH, '//a[@data-testid="AppTabBar_Home_Link"]'))
            )
            logging.info("Login berhasil!")
            return True
        except TimeoutException:
            logging.error("Timeout saat mencoba login. Elemen tidak ditemukan.")
            return False
        except Exception as e:
            logging.error(f"Terjadi error saat login: {e}")
            return False

    def scrape_latest_tweet(self):
        """Mengambil tweet terbaru dari profil target."""
        try:
            logging.info(f"Mengunjungi profil: {self.config['TARGET_PROFILE_URL']}")
            self.driver.get(self.config['TARGET_PROFILE_URL'])

            # Tunggu hingga container tweet muncul
            tweet_container_selector = 'article[data-testid="tweet"]'
            WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, tweet_container_selector))
            )
            latest_tweet_element = self.driver.find_element(By.CSS_SELECTOR, tweet_container_selector)

            # Ambil teks tweet
            tweet_text_element = latest_tweet_element.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]')
            current_tweet_text = tweet_text_element.text

            if current_tweet_text != self.last_tweet_text:
                logging.info(">>> Tweet baru ditemukan!")
                logging.info(f"Teks: {current_tweet_text}")

                image_url = self._find_image_url(latest_tweet_element)
                self._send_to_whatsapp(current_tweet_text, image_url)

                self.last_tweet_text = current_tweet_text
            else:
                logging.info("Tidak ada tweet baru.")

        except TimeoutException:
            logging.warning("Timeout saat menunggu tweet muncul. Mungkin profil kosong atau halaman tidak termuat.")
        except NoSuchElementException:
            logging.warning("Tidak dapat menemukan elemen teks atau gambar di tweet.")
        except Exception as e:
            logging.error(f"Gagal mengambil tweet: {e}")

    def _find_image_url(self, tweet_element):
        """Mencari URL gambar di dalam sebuah elemen tweet."""
        try:
            images = tweet_element.find_elements(By.TAG_NAME, 'img')
            for img in images:
                src = img.get_attribute('src')
                if 'pbs.twimg.com/media' in src:
                    logging.info(f"Gambar ditemukan: {src}")
                    return src
            logging.info("Tidak ada gambar yang valid di tweet ini.")
            return None
        except Exception as e:
            logging.error(f"Error saat mencari gambar: {e}")
            return None

    def _send_to_whatsapp(self, message, image_url):
        """Mengirim data ke bot WhatsApp."""
        payload = {
            'groupId': self.config['GROUP_ID'],
            'message': message,
            'imageUrl': image_url
        }
        try:
            response = requests.post(self.config['WHATSAPP_BOT_URL'], json=payload, timeout=10)
            response.raise_for_status()
            logging.info("Data telah dikirim ke bot WhatsApp.")
        except requests.exceptions.ConnectionError:
            logging.error("Gagal terhubung ke bot WhatsApp. Pastikan bot.js berjalan.")
        except requests.exceptions.RequestException as e:
            logging.error(f"Gagal mengirim data ke bot WhatsApp: {e}")

    def run(self):
        """Menjalankan loop utama scraper."""
        if self.login():
            while True:
                self.scrape_latest_tweet()
                logging.info(f"Menunggu selama {self.config['CHECK_INTERVAL_SECONDS']} detik...")
                time.sleep(self.config['CHECK_INTERVAL_SECONDS'])

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