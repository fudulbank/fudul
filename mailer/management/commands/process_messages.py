from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand
from django.utils.html import strip_tags
from post_office import mail
from post_office.models import EmailTemplate

from mailer.models import Message


class Command(BaseCommand):
    def handle(self, *args, **options):
        pending_messages = Message.objects.filter(status="PENDING")
        for message in pending_messages:
            print("Processing message #{}...".format(message.pk))
            # Change status
            message.status = 'PROCESSING'
            message.save()

            # Create post-office EmailTemplate
            template_name = "mailer_{}".format(message.pk)
            while EmailTemplate.objects.filter(name=template_name).exists():
                template_name = template_name + "_"

            template = EmailTemplate.objects.create(name=template_name,
                                                    subject=message.subject,
                                                    description="Automatically generated template for Message #{}".format(message.pk),
                                                    content=strip_tags(message.body),
                                                    html_content=message.body)

            from_address = "Fudul <{}>".format(message.from_address)

            # Generate list of receipts
            user_pool = User.objects.filter(is_active=True).exclude(email="")
            receipts = User.objects.none()
            if message.target == 'ALL':
                receipts = user_pool
            elif message.target == 'COLLEGES':
                for college in message.colleges.all():
                    receipts |= user_pool.filter(profile__college=college)
            elif message.target == 'INSTITUTIONS':
                for institution in message.institutions.all():
                    receipts |= user_pool.filter(profile__college__institution=institution)

            # Aaand send!
            email_addresses = receipts.values_list('email', 'profile__alternative_email')
            messages = []
            for email, alternative_email in email_addresses:
                message = {'sender': from_address,
                           'recipients': email,
                           'cc': alternative_email or None,
                           'render_on_delivery': True,
                           'template': template_name}
                messages.append(message)
            mail.send_many(messages)

            message.status = 'SENT'
            message.save()
