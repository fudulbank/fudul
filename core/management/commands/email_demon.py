import socket
import sys
import time
from django.core.management import call_command
from django.core.management.base import BaseCommand


def get_lock(process_name):
    get_lock._lock_socket = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)

    try:
        get_lock._lock_socket.bind('\0' + process_name)
        print('I got the lock')
    except socket.error:
        sys.exit()

get_lock('email_demon')

class Command(BaseCommand):
    def handle(self, *args, **options):
        while True:
            call_command('send_queued_mail', lockfile="/home/fudul/.post_office.lock")
            time.sleep(5)
