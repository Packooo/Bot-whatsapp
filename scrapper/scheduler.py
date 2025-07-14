"""
Smart Scheduler untuk Twitter Bot
Menjalankan crawling hanya pada waktu-waktu tertentu untuk efisiensi dan menghindari deteksi bot
"""

import datetime
import pytz
import time
import logging
from typing import List, Tuple, Optional

class SmartScheduler:
    def __init__(self, timezone: str = 'Asia/Jakarta'):
        """
        Initialize scheduler dengan timezone
        
        Args:
            timezone: Timezone string (default: Asia/Jakarta)
        """
        self.timezone = pytz.timezone(timezone)
        
        # Jadwal crawling (jam:menit - jam:menit)
        self.crawling_windows = [
            (6, 0, 6, 5),    # 06:00 - 06:05
            (8, 10, 8, 15),  # 08:10 - 08:15
            (9, 0, 9, 5),    # 09:00 - 09:05
            (9, 30, 11, 35), # 09:30 - 11:35
            (11, 55, 12, 5), # 11:55 - 12:05
            (12, 27, 12, 30), # 12:27 - 12:30
            (13, 0, 13, 35), # 13:00 - 13:35
            (13, 55, 14, 10), # 13:55 - 14:10
            (14, 45, 14, 50), # 14:45 - 14:50
            (15, 0, 15, 15), # 15:00 - 15:15
            (15, 44, 16, 5), # 15:44 - 16:05
            (16, 30, 16, 35), # 16:30 - 16:35
            (17, 0, 17, 38), # 17:00 - 17:38
            (18, 10, 18, 15), # 18:10 - 18:15
            (19, 15, 19, 20), # 19:15 - 19:20
            (19, 40, 20, 10), # 19:40 - 20:10
            (20, 20, 20, 35), # 20:20 - 20:35
            (21, 0, 21, 15), # 21:00 - 21:15
            (23, 50, 23, 55), # 23:50 - 23:55
        ]
        
        logging.info(f"Smart Scheduler initialized with {len(self.crawling_windows)} time windows")
    
    def _get_current_time(self) -> datetime.datetime:
        """Mendapatkan waktu saat ini dalam timezone yang ditentukan"""
        return datetime.datetime.now(self.timezone)
    
    def _time_to_minutes(self, hour: int, minute: int) -> int:
        """Konversi jam:menit ke total menit dalam sehari"""
        return hour * 60 + minute
    
    def _current_time_to_minutes(self, dt: datetime.datetime) -> int:
        """Konversi datetime ke total menit dalam sehari"""
        return dt.hour * 60 + dt.minute
    
    def is_crawling_time(self) -> bool:
        """
        Cek apakah saat ini adalah waktu untuk crawling
        
        Returns:
            bool: True jika saat ini adalah waktu crawling
        """
        current_time = self._get_current_time()
        current_minutes = self._current_time_to_minutes(current_time)
        
        for start_hour, start_min, end_hour, end_min in self.crawling_windows:
            start_minutes = self._time_to_minutes(start_hour, start_min)
            end_minutes = self._time_to_minutes(end_hour, end_min)
            
            # Handle case where window crosses midnight
            if end_minutes < start_minutes:
                # Window crosses midnight (e.g., 23:50 - 00:05)
                if current_minutes >= start_minutes or current_minutes <= end_minutes:
                    return True
            else:
                # Normal window within same day
                if start_minutes <= current_minutes <= end_minutes:
                    return True
        
        return False
    
    def get_current_window_info(self) -> Optional[dict]:
        """
        Mendapatkan informasi window crawling saat ini
        
        Returns:
            dict atau None: Informasi window saat ini jika sedang dalam waktu crawling
        """
        if not self.is_crawling_time():
            return None
        
        current_time = self._get_current_time()
        current_minutes = self._current_time_to_minutes(current_time)
        
        for start_hour, start_min, end_hour, end_min in self.crawling_windows:
            start_minutes = self._time_to_minutes(start_hour, start_min)
            end_minutes = self._time_to_minutes(end_hour, end_min)
            
            # Check if current time is in this window
            in_window = False
            if end_minutes < start_minutes:
                # Window crosses midnight
                if current_minutes >= start_minutes or current_minutes <= end_minutes:
                    in_window = True
            else:
                # Normal window
                if start_minutes <= current_minutes <= end_minutes:
                    in_window = True
            
            if in_window:
                return {
                    'start_time': f"{start_hour:02d}:{start_min:02d}",
                    'end_time': f"{end_hour:02d}:{end_min:02d}",
                    'duration_minutes': (end_minutes - start_minutes) if end_minutes > start_minutes else (1440 - start_minutes + end_minutes),
                    'remaining_minutes': self._calculate_remaining_minutes(current_minutes, end_minutes)
                }
        
        return None
    
    def _calculate_remaining_minutes(self, current_minutes: int, end_minutes: int) -> int:
        """Hitung sisa menit dalam window saat ini"""
        if end_minutes >= current_minutes:
            return end_minutes - current_minutes
        else:
            # Handle midnight crossing
            return (1440 - current_minutes) + end_minutes
    
    def get_next_crawling_window(self) -> dict:
        """
        Mendapatkan informasi window crawling berikutnya
        
        Returns:
            dict: Informasi window crawling berikutnya
        """
        current_time = self._get_current_time()
        current_minutes = self._current_time_to_minutes(current_time)
        
        # Cari window berikutnya
        next_windows = []
        
        for start_hour, start_min, end_hour, end_min in self.crawling_windows:
            start_minutes = self._time_to_minutes(start_hour, start_min)
            
            if start_minutes > current_minutes:
                # Window hari ini
                wait_minutes = start_minutes - current_minutes
                next_windows.append({
                    'start_time': f"{start_hour:02d}:{start_min:02d}",
                    'end_time': f"{end_hour:02d}:{end_min:02d}",
                    'wait_minutes': wait_minutes,
                    'wait_seconds': wait_minutes * 60
                })
        
        # Jika tidak ada window hari ini, ambil window pertama besok
        if not next_windows:
            first_window = self.crawling_windows[0]
            start_hour, start_min, end_hour, end_min = first_window
            wait_minutes = (1440 - current_minutes) + self._time_to_minutes(start_hour, start_min)
            next_windows.append({
                'start_time': f"{start_hour:02d}:{start_min:02d}",
                'end_time': f"{end_hour:02d}:{end_min:02d}",
                'wait_minutes': wait_minutes,
                'wait_seconds': wait_minutes * 60
            })
        
        # Return window terdekat
        return min(next_windows, key=lambda x: x['wait_minutes'])
    
    def wait_for_next_window(self, config=None) -> None:
        """
        Tunggu sampai window crawling berikutnya
        
        Args:
            config: Dictionary konfigurasi untuk menentukan interval check
        """
        # Tentukan check interval berdasarkan config
        if config:
            check_interval = config.get('SCHEDULER_CHECK_INTERVAL', 60)
        else:
            check_interval = 60
            
        while not self.is_crawling_time():
            next_window = self.get_next_crawling_window()
            current_time = self._get_current_time()
            
            logging.info(f"⏰ Menunggu window crawling berikutnya: {next_window['start_time']} - {next_window['end_time']}")
            logging.info(f"🕐 Waktu saat ini: {current_time.strftime('%H:%M:%S')} WIB")
            logging.info(f"⏳ Sisa waktu tunggu: {next_window['wait_minutes']} menit")
            
            # Tunggu dengan interval yang ditentukan, maksimal check_interval detik
            wait_time = min(check_interval, next_window['wait_seconds'])
            logging.info(f"💤 Sleeping for {wait_time} seconds...")
            time.sleep(wait_time)
    
    def get_schedule_summary(self) -> str:
        """
        Mendapatkan ringkasan jadwal crawling
        
        Returns:
            str: Ringkasan jadwal dalam format string
        """
        summary = "📅 JADWAL CRAWLING BOT\n"
        summary += "=" * 40 + "\n"
        
        for i, (start_hour, start_min, end_hour, end_min) in enumerate(self.crawling_windows, 1):
            duration = self._time_to_minutes(end_hour, end_min) - self._time_to_minutes(start_hour, start_min)
            if duration < 0:
                duration += 1440  # Handle midnight crossing
            
            summary += f"{i:2d}. {start_hour:02d}:{start_min:02d} - {end_hour:02d}:{end_min:02d} ({duration} menit)\n"
        
        summary += "=" * 40 + "\n"
        summary += f"Total: {len(self.crawling_windows)} window crawling per hari"
        
        return summary
    
    def should_continue_crawling(self) -> bool:
        """
        Cek apakah crawling harus dilanjutkan (masih dalam window)
        
        Returns:
            bool: True jika masih dalam window crawling
        """
        return self.is_crawling_time()
    
    def get_optimal_check_interval(self, config=None) -> int:
        """
        Mendapatkan interval check optimal berdasarkan config dan window saat ini
        
        Args:
            config: Dictionary konfigurasi dengan MIN_WAIT_SECONDS dan MAX_WAIT_SECONDS
        
        Returns:
            int: Interval dalam detik (random berdasarkan config)
        """
        import random
        
        # Default values jika config tidak diberikan
        min_wait = 60
        max_wait = 61
        
        if config:
            min_wait = config.get('MIN_WAIT_SECONDS', 60)
            max_wait = config.get('MAX_WAIT_SECONDS', 61)
        
        window_info = self.get_current_window_info()
        
        if not window_info:
            # Jika tidak dalam window, gunakan interval yang lebih panjang
            return random.randint(min_wait * 5, min_wait * 10)  # 5-10x interval normal
        
        # Gunakan interval dari config untuk semua window
        return random.randint(min_wait, max_wait)