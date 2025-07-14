import time
import requests
import logging
import datetime
import pytz # type: ignore
import random
import json
import os
from collections import deque
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- Konfigurasi Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Import konfigurasi dan scheduler
from config import get_config, print_config_summary
from scheduler import SmartScheduler

class TwitterScraper:
    def __init__(self, config):
        self.config = config
        self.driver = self._setup_driver()
        self.last_tweet_text = "" # <-- Kembali menyimpan teks
        self.processed_tweet_ids = set()  # Set untuk menyimpan ID tweet yang sudah diproses
        self.post_timestamps = deque()  # Queue untuk tracking timestamp posting
        self.tweet_data_file = self.config["TWEET_DATA_FILE"]
        
        # Initialize smart scheduler jika diaktifkan
        use_smart_scheduler = self.config.get('USE_SMART_SCHEDULER', False)
        if use_smart_scheduler:
            self.scheduler = SmartScheduler(self.config.get('TIMEZONE', 'Asia/Jakarta'))
            logging.info("Smart Scheduler diaktifkan")
            logging.info(self.scheduler.get_schedule_summary())
        else:
            self.scheduler = None
            logging.info("Menggunakan mode legacy (tanpa smart scheduler)")
            logging.info(f"Legacy mode config - Offline: {self.config['OFFLINE_START_HOUR']:02d}:00 - {self.config['OFFLINE_END_HOUR']:02d}:00")
            logging.info(f"Legacy mode config - Check interval: {self.config['MIN_WAIT_SECONDS']}-{self.config['MAX_WAIT_SECONDS']} detik")
        
        self._load_processed_tweets()

    def _load_processed_tweets(self):
        """Memuat data tweet yang sudah diproses dari file JSON."""
        try:
            if os.path.exists(self.tweet_data_file):
                with open(self.tweet_data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_tweet_ids = set(data.get('processed_ids', []))
                    logging.info(f"Loaded {len(self.processed_tweet_ids)} processed tweet IDs")
            else:
                self.processed_tweet_ids = set()
                logging.info("No previous tweet data found, starting fresh")
        except Exception as e:
            logging.error(f"Error loading processed tweets: {e}")
            self.processed_tweet_ids = set()

    def _save_processed_tweets(self):
        """Menyimpan data tweet yang sudah diproses ke file JSON."""
        try:
            data = {
                'processed_ids': list(self.processed_tweet_ids),
                'last_updated': datetime.datetime.now().isoformat()
            }
            with open(self.tweet_data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logging.info(f"Saved {len(self.processed_tweet_ids)} processed tweet IDs")
        except Exception as e:
            logging.error(f"Error saving processed tweets: {e}")

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

    def _can_post_now(self):
        """Selalu return True karena tidak ada rate limiting untuk posts."""
        return True

    def _record_post(self):
        """Tidak perlu record post karena tidak ada rate limiting."""
        pass

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

    def get_latest_tweets(self):
        """Ambil tweet ID terbaru dari profil dengan scrolling yang efektif."""
        try:
            logging.info(f"Mengunjungi profil: {self.config['TARGET_PROFILE_URL']}")
            self.driver.get(self.config['TARGET_PROFILE_URL'])
            time.sleep(3)
            
            tweet_selector = 'article[data-testid="tweet"]'
            
            # Tunggu tweet muncul
            try:
                WebDriverWait(self.driver, self.config["SELENIUM_TIMEOUT"]).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, tweet_selector))
                )
            except TimeoutException:
                logging.warning("Timeout menunggu tweet, coba scroll untuk memicu loading...")
                self.driver.execute_script("window.scrollTo(0, 800);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(1)
            
            # Scroll bertahap untuk memuat lebih banyak tweet
            logging.info("Scroll untuk memuat tweet...")
            best_tweets = []
            
            # Scroll ke beberapa posisi dan ambil tweet terbanyak
            scroll_positions = [0, 600, 1200, 1800, 2400]
            for pos in scroll_positions:
                self.driver.execute_script(f"window.scrollTo(0, {pos});")
                time.sleep(1.5)
                
                current_tweets = self.driver.find_elements(By.CSS_SELECTOR, tweet_selector)
                if len(current_tweets) > len(best_tweets):
                    best_tweets = current_tweets
                    logging.info(f"Ditemukan {len(current_tweets)} tweet")
                
                if len(current_tweets) >= 5:
                    break
            
            # Ekstrak ID dari tweet terbaik yang ditemukan
            current_tweet_ids = []
            tweet_batch = best_tweets[:5] if best_tweets else []
            
            for i, tweet_element in enumerate(tweet_batch):
                try:
                    tweet_id = self._extract_tweet_id(tweet_element)
                    if tweet_id:
                        current_tweet_ids.append(tweet_id)
                        logging.info(f"Tweet {i+1}: ID {tweet_id}")
                except Exception as e:
                    logging.error(f"Error mengambil tweet ke-{i+1}: {e}")
                    continue
            
            logging.info(f"✅ Berhasil mengambil {len(current_tweet_ids)} tweet ID")
            return current_tweet_ids
            
        except Exception as e:
            logging.error(f"Error mengambil tweet: {e}")
            return []

    def _extract_tweet_id(self, tweet_element):
        """Ekstrak ID tweet dari elemen tweet."""
        # Metode utama: cari dari link timestamp
        try:
            time_element = tweet_element.find_element(By.CSS_SELECTOR, 'time')
            parent_link = time_element.find_element(By.XPATH, '..')
            href = parent_link.get_attribute('href')
            
            if href and '/status/' in href:
                tweet_id = href.split('/status/')[-1].split('?')[0].split('/')[0]
                if tweet_id.isdigit():
                    return tweet_id
        except:
            pass
        
        # Metode alternatif: cari dari semua link dalam tweet
        try:
            links = tweet_element.find_elements(By.TAG_NAME, 'a')
            for link in links:
                href = link.get_attribute('href')
                if href and '/status/' in href:
                    tweet_id = href.split('/status/')[-1].split('?')[0].split('/')[0]
                    if tweet_id.isdigit():
                        return tweet_id
        except:
            pass
        
        # Fallback: generate ID dari konten tweet
        try:
            tweet_text = tweet_element.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]').text
            if tweet_text:
                hash_id = str(abs(hash(tweet_text[:50])))[:10]
                return hash_id
        except:
            pass
        
        return None

    def _extract_tweet_info(self, tweet_element, tweet_id):
        """Ekstrak informasi lengkap dari elemen tweet."""
        try:
            # Ekstrak teks tweet
            try:
                tweet_text = tweet_element.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]').text
            except NoSuchElementException:
                tweet_text = ""
            
            # Ekstrak URL gambar
            image_url = self._find_image_url(tweet_element)
            
            # Ekstrak timestamp
            try:
                time_element = tweet_element.find_element(By.CSS_SELECTOR, 'time')
                timestamp = time_element.get_attribute('datetime')
            except NoSuchElementException:
                timestamp = datetime.datetime.now().isoformat()
            
            return {
                "id": tweet_id,
                "text": tweet_text,
                "image": image_url,
                "timestamp": timestamp
            }
            
        except Exception as e:
            logging.error(f"Error extracting tweet info for ID {tweet_id}: {e}")
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

    def _send_to_whatsapp(self, tweet_info):
        """Kirim tweet ke WhatsApp tanpa rate limiting."""
        payload = {
            'groupId': self.config['GROUP_ID'],
            'message': tweet_info['text'],
            'imageUrl': tweet_info['image']
        }
        
        try:
            response = requests.post(self.config['WHATSAPP_BOT_URL'], json=payload, timeout=10)
            if response.status_code == 200:
                logging.info(f"Tweet ID {tweet_info['id']} berhasil dikirim ke WhatsApp")
                return True
            else:
                logging.error(f"Failed to send tweet ID {tweet_info['id']}: HTTP {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            logging.error(f"Gagal mengirim tweet ID {tweet_info['id']} ke WhatsApp: {e}")
            return False

    def _get_tweet_details(self, tweet_id):
        """Ambil detail tweet berdasarkan ID."""
        try:
            # Cari tweet element berdasarkan ID
            tweet_selector = 'article[data-testid="tweet"]'
            tweets = self.driver.find_elements(By.CSS_SELECTOR, tweet_selector)
            
            for tweet_element in tweets:
                element_id = self._extract_tweet_id(tweet_element)
                if element_id == tweet_id:
                    # Ekstrak teks tweet
                    try:
                        tweet_text = tweet_element.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetText"]').text
                    except NoSuchElementException:
                        tweet_text = ""
                    
                    # Ekstrak URL gambar
                    image_url = self._find_image_url(tweet_element)
                    
                    return {
                        "id": tweet_id,
                        "text": tweet_text,
                        "image": image_url,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
            
            # Jika tidak ditemukan, buat data minimal
            return {
                "id": tweet_id,
                "text": f"Tweet baru dari {self.config['TARGET_PROFILE_URL']}",
                "image": None,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error getting tweet details for ID {tweet_id}: {e}")
            return None

    def check_and_process_new_tweets(self, current_tweet_ids):
        """Cek tweet baru dan proses jika ada."""
        logging.info(f"Status: {len(current_tweet_ids)} tweet ditemukan, {len(self.processed_tweet_ids)} sudah diproses")
        
        # Cari tweet yang belum diproses
        new_tweet_ids = [tweet_id for tweet_id in current_tweet_ids if tweet_id not in self.processed_tweet_ids]
        
        if not new_tweet_ids:
            logging.info("Tidak ada tweet baru")
            return 0
        
        logging.info(f"Memproses {len(new_tweet_ids)} tweet baru")
        
        # Proses setiap tweet baru
        processed_count = 0
        for tweet_id in new_tweet_ids:
            try:
                tweet_info = self._get_tweet_details(tweet_id)
                if tweet_info and self._send_to_whatsapp(tweet_info):
                    self.processed_tweet_ids.add(tweet_id)
                    processed_count += 1
                    logging.info(f"✅ Tweet {tweet_id} dikirim ke WhatsApp")
                    time.sleep(1)
                else:
                    logging.error(f"❌ Gagal mengirim tweet {tweet_id}")
            except Exception as e:
                logging.error(f"Error processing tweet {tweet_id}: {e}")
        
        if processed_count > 0:
            self._save_processed_tweets()
            logging.info(f"✅ {processed_count} tweet baru berhasil diproses")
        
        return processed_count

    def run(self):
        """Loop utama scraper dengan smart scheduler."""
        if not self.login():
            return
            
        while True:
            try:
                # Gunakan smart scheduler jika diaktifkan
                if self.scheduler:
                    self._run_with_smart_scheduler()
                else:
                    self._run_legacy_mode()
                    
            except Exception as e:
                logging.error(f"Error dalam main loop: {e}")
                time.sleep(60)
    
    def _run_with_smart_scheduler(self):
        """Jalankan scraper dengan smart scheduler."""
        # Cek apakah saat ini waktu crawling
        if not self.scheduler.is_crawling_time():
            # Tunggu sampai window crawling berikutnya
            self.scheduler.wait_for_next_window(self.config)
            return
        
        # Dapatkan info window saat ini
        window_info = self.scheduler.get_current_window_info()
        if window_info:
            logging.info(f"🟢 CRAWLING AKTIF - Window: {window_info['start_time']} - {window_info['end_time']}")
            logging.info(f"⏳ Sisa waktu window: {window_info['remaining_minutes']} menit")
        
        # Loop crawling selama masih dalam window
        while self.scheduler.should_continue_crawling():
            try:
                # Ambil tweet terbaru
                current_tweet_ids = self.get_latest_tweets()
                
                if current_tweet_ids:
                    # Cek dan proses tweet baru
                    processed_count = self.check_and_process_new_tweets(current_tweet_ids)
                    
                    if processed_count > 0:
                        logging.info(f"✅ {processed_count} tweet baru berhasil diproses")
                
                # Gunakan interval optimal berdasarkan config
                wait_time = self.scheduler.get_optimal_check_interval(self.config)
                logging.info(f"⏰ Menunggu {wait_time} detik (dalam window crawling)...")
                time.sleep(wait_time)
                
            except Exception as e:
                logging.error(f"Error dalam crawling window: {e}")
                time.sleep(30)  # Wait lebih pendek untuk error dalam window
        
        logging.info("🔴 Window crawling berakhir")
    
    def _run_legacy_mode(self):
        """Jalankan scraper dengan mode legacy (tanpa smart scheduler)."""
        # Cek waktu offline (mode legacy) - gunakan timezone dari config
        timezone_str = self.config.get('TIMEZONE', 'Asia/Jakarta')
        local_tz = pytz.timezone(timezone_str)
        now_local = datetime.datetime.now(local_tz)
        
        # Log informasi waktu saat ini
        logging.info(f"Legacy mode - Waktu saat ini: {now_local.strftime('%H:%M:%S')} ({timezone_str})")
        
        if self.config['OFFLINE_START_HOUR'] <= now_local.hour < self.config['OFFLINE_END_HOUR']:
            logging.info(f"Mode offline ({now_local.strftime('%H:%M')} {timezone_str})")
            logging.info(f"Offline dari {self.config['OFFLINE_START_HOUR']:02d}:00 sampai {self.config['OFFLINE_END_HOUR']:02d}:00")
            time.sleep(self.config['OFFLINE_CHECK_INTERVAL'] * 60)
            return
        
        # Ambil 5 tweet ID terbaru
        current_tweet_ids = self.get_latest_tweets()
        
        if current_tweet_ids:
            # Cek dan proses tweet baru
            processed_count = self.check_and_process_new_tweets(current_tweet_ids)
            
            if processed_count > 0:
                logging.info(f"✅ {processed_count} tweet baru berhasil diproses")
        
        # Random delay berdasarkan config
        wait_time = random.randint(self.config['MIN_WAIT_SECONDS'], self.config['MAX_WAIT_SECONDS'])
        logging.info(f"Menunggu {wait_time} detik...")
        time.sleep(wait_time)

    def get_stats(self):
        """Mendapatkan statistik scraper."""
        stats = {
            'processed_tweets': len(self.processed_tweet_ids),
            'max_tweets_check': self.config['MAX_TWEETS_CHECK'],
        }
        
        if self.scheduler:
            stats['scheduler_mode'] = 'Smart Scheduler'
            stats['timezone'] = self.config.get('TIMEZONE', 'Asia/Jakarta')
            stats['crawling_windows'] = len(self.scheduler.crawling_windows)
            
            if self.scheduler.is_crawling_time():
                window_info = self.scheduler.get_current_window_info()
                stats['current_status'] = f"AKTIF - {window_info['start_time']} sampai {window_info['end_time']}"
                stats['remaining_minutes'] = window_info['remaining_minutes']
            else:
                next_window = self.scheduler.get_next_crawling_window()
                stats['current_status'] = f"MENUNGGU - Next: {next_window['start_time']}"
                stats['wait_minutes'] = next_window['wait_minutes']
        else:
            stats['scheduler_mode'] = 'Legacy Mode'
            stats['check_interval'] = f"{self.config['MIN_WAIT_SECONDS']}-{self.config['MAX_WAIT_SECONDS']} detik (random)"
        
        return stats

    def cleanup_old_tweet_ids(self, max_ids=None):
        """Membersihkan ID tweet lama untuk menghemat memori."""
        if max_ids is None:
            max_ids = self.config['MAX_STORED_TWEET_IDS']
            
        if len(self.processed_tweet_ids) > max_ids:
            # Konversi ke list, sort, dan ambil yang terbaru
            sorted_ids = sorted(list(self.processed_tweet_ids))
            self.processed_tweet_ids = set(sorted_ids[-max_ids:])
            self._save_processed_tweets()
            logging.info(f"Cleaned up old tweet IDs, keeping {max_ids} most recent")

    def close(self):
        """Menutup WebDriver dan simpan data."""
        try:
            # Simpan data terakhir sebelum menutup
            self._save_processed_tweets()
            
            if self.driver:
                self.driver.quit()
                logging.info("WebDriver ditutup.")
                
            # Tampilkan statistik akhir
            stats = self.get_stats()
            logging.info(f"Statistik akhir: {stats['processed_tweets']} tweet diproses")
            
        except Exception as e:
            logging.error(f"Error saat menutup scraper: {e}")

if __name__ == "__main__":
    scraper = None
    try:
        # Load dan validasi konfigurasi
        CONFIG = get_config()
        
        logging.info("🚀 Memulai Twitter Scraper dengan batch processing dan rate limiting...")
        
        # Tampilkan ringkasan konfigurasi
        print_config_summary(CONFIG)
        
        scraper = TwitterScraper(CONFIG)
        
        # Cleanup tweet IDs lama setiap startup
        scraper.cleanup_old_tweet_ids()
        
        # Tampilkan statistik awal
        stats = scraper.get_stats()
        logging.info(f"Statistik awal: {stats['processed_tweets']} tweet sudah diproses sebelumnya")
        
        scraper.run()
        
    except KeyboardInterrupt:
        logging.info("⏹️ Scraper dihentikan oleh user")
    except Exception as e:
        logging.critical(f"Terjadi error kritis pada scraper: {e}", exc_info=True)
    finally:
        if scraper:
            logging.info("🔄 Menutup scraper...")
            scraper.close()
        logging.info("✅ Scraper telah ditutup")