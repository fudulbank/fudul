from bs4 import BeautifulSoup
from constance import config
from django.core.management.base import BaseCommand
import requests

class Command(BaseCommand):
    def handle(self, *args, **options):

        cookies = {
            'sessionid': config.WF_SESSION_ID,
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Fedora; Linux x86_64; rv:63.0) Gecko/20100101 Firefox/63.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        response = requests.get('https://my.webfaction.com/transactions', headers=headers, cookies=cookies)
        soup = BeautifulSoup(response.text, 'html.parser')
        last_transaction_balance = soup.select('.transaction_balance.column')[1].text
        clean_balance = last_transaction_balance.split()[0].strip('$').strip()
        config.WF_CURRENT_BALANCE = int(float(clean_balance))
