import logging
import random
import string

from django.conf import settings
from django.core.mail import send_mail as django_send_mail

logger = logging.getLogger(__name__)


def generate_code():
    """Generate 6-character code with 3 letters and 3 digits."""
    letters = "".join(random.choices(string.ascii_uppercase, k=3))
    digits = "".join(random.choices(string.digits, k=3))
    code = list(letters + digits)
    random.shuffle(code)
    return "".join(code)


def send_email(to, subject, message, from_email=None):
    """
    Send email using Django's email system with settings configuration.

    Args:
        to (str or list): Recipient email address(es)
        subject (str): Email subject line
        message (str): Email message content
        from_email (str, optional): Sender email (defaults to DEFAULT_FROM_EMAIL)

    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not to or not message or not subject:
            logger.error("Missing required email parameters")
            return False

        if not from_email:
            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@example.com")

        if isinstance(to, str):
            recipient_list = [to]
        else:
            recipient_list = to

        sent = django_send_mail(
            subject=subject,
            message=message,
            from_email=from_email,
            recipient_list=recipient_list,
            fail_silently=False,
        )

        if sent:
            logger.info(f"Email sent to {to} with subject: {subject}")
        else:
            logger.warning(f"Email not sent to {to}")
        return sent

    except Exception as e:
        logger.error(f"Failed to send email to {to}: {str(e)}")
        return False
