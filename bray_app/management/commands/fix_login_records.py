from django.core.management.base import BaseCommand
from bray_app.services.user_accounting_service import fix_employee_login_records, get_login_data_debug


class Command(BaseCommand):
    help = 'Fix employee login records with incorrect employee codes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Show debug information about login records',
        )
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Fix incorrect employee codes in login records',
        )

    def handle(self, *args, **options):
        if options['debug']:
            self.stdout.write("Showing debug information...")
            get_login_data_debug()
        
        if options['fix']:
            self.stdout.write("Fixing employee login records...")
            updated_count = fix_employee_login_records()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully fixed {updated_count} login records')
            )
        
        if not options['debug'] and not options['fix']:
            self.stdout.write("Use --debug to see login data or --fix to correct employee codes")