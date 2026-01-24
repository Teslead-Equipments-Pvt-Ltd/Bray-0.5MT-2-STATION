import os
import datetime
import atexit
import threading
import time
from django.apps import AppConfig


class StandardAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'bray_app'
    backup_thread = None
    stop_thread = False

    def ready(self):
        """Run when Django starts"""
        # Only run in the main process, not in reloader
        if os.environ.get('RUN_MAIN') == 'true':
            self.check_and_run_backup()
            # Start continuous backup checker
            self.start_backup_monitor()
            # Register shutdown backup
            atexit.register(self.shutdown_backup)

    def start_backup_monitor(self):
        """Start background thread to check for backup every hour"""
        if self.backup_thread is None or not self.backup_thread.is_alive():
            self.stop_thread = False
            self.backup_thread = threading.Thread(target=self.backup_monitor_loop, daemon=True)
            self.backup_thread.start()
            print(" Backup monitor started (checks every hour)")

    def backup_monitor_loop(self):
        """Background loop that checks for backup every hour"""
        while not self.stop_thread:
            time.sleep(100)  # Wait 
            if not self.stop_thread:
                self.check_and_run_backup()

    def check_and_run_backup(self):
        """Check if backup is needed and run it"""
        from django.core.management import call_command
        from django.db import connection
        
        try:
            # Check if backup already done today
            today = datetime.date.today().strftime("%Y-%m-%d")
            backup_dir = r"E:\Bray_db_backup"
            backup_file = os.path.join(backup_dir, f"backup_{today}.sql")
            
            if os.path.exists(backup_file):
                print(f" Backup already exists for today: {backup_file}")
                return
            
            # Check if safe to backup (no tests running)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM master_temp_data 
                    WHERE STATION_STATUS = 'Enabled'
                """)
                test_count = cursor.fetchone()[0]
            
            if test_count == 0:
                print("Starting daily database backup...")
                call_command('daily_db_backup')
            else:
                print(f"Backup skipped: {test_count} test(s) in progress")
                
        except Exception as e:
            print(f"Backup check failed: {e}")

    def shutdown_backup(self):
        """Run backup when Django shuts down"""
        from django.core.management import call_command
        
        # Stop the background thread
        self.stop_thread = True
        
        try:
            # Check if backup already done today
            today = datetime.date.today().strftime("%Y-%m-%d")
            backup_dir = r"E:\Bray_db_backup"
            backup_file = os.path.join(backup_dir, f"backup_{today}.sql")
            
            if os.path.exists(backup_file):
                return  # Already backed up today
            
            # On shutdown, tests should be stopped, so just create backup
            print("\nShutdown: Creating daily database backup...")
            call_command('daily_db_backup')
                
        except Exception as e:
            print(f"Shutdown backup failed: {e}")
