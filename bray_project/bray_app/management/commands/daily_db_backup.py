import os
import datetime
import subprocess
from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings

class Command(BaseCommand):
    help = "Daily DB backup if no test/cycle is running"

    def handle(self, *args, **kwargs):
        if not self.is_safe_to_backup():
            self.stdout.write("Backup skipped: Test or cycle in progress")
            return

        if self.backup_already_exists():
            self.stdout.write("Backup skipped: Today's backup already exists")
            return

        self.create_backup()

    def is_safe_to_backup(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*) 
                FROM master_temp_data 
                WHERE STATION_STATUS = 'Enabled'
            """)
            test_count = cursor.fetchone()[0]

        return test_count == 0

    def backup_already_exists(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        backup_dir = r"D:\Bray_db_backup"
        backup_file = os.path.join(backup_dir, f"backup_{today}.sql")
        return os.path.exists(backup_file)

    def create_backup(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        backup_dir = r"D:\Bray_db_backup"
        os.makedirs(backup_dir, exist_ok=True)

        backup_file = os.path.join(
            backup_dir, f"backup_{today}.sql"
        )

        db = settings.DATABASES['default']

        command = [
            "mysqldump",
            "-u", db['USER'],
            "-h", db['HOST'],
            "-P", str(db['PORT']),
            "--single-transaction",
            "--quick",
            db['NAME']
        ]

        env = os.environ.copy()
        env["MYSQL_PWD"] = db['PASSWORD']

        with open(backup_file, "w") as f:
            result = subprocess.run(
                command,
                stdout=f,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )

        if result.returncode != 0:
            self.stdout.write(f" Backup failed:\n{result.stderr}")
        else:
            self.stdout.write(f" Backup created: {backup_file}")
