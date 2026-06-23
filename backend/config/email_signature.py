import html
from email.mime.image import MIMEImage

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


SIGNATURE_CONTENT_ID = "agenda-educacao-ols-signature"
SIGNATURE_FILENAME = "assinatura-educacao-ols.png"
SIGNATURE_PATH = settings.BASE_DIR / "assets" / "email" / "signature.png"


def text_to_html(body):
    escaped = html.escape(body or "")
    html_text = escaped.replace("\n", "<br>")
    return f'<div style="text-align: justify;">{html_text}</div>'


def signature_html():
    return (
        "<br><br>"
        f'<img src="cid:{SIGNATURE_CONTENT_ID}" '
        'alt="Equipe da Educação - Operação Lei Seca" '
        'width="760" '
        'style="display:block;max-width:100%;height:auto;border:0;">'
    )


def attach_signature_image(message):
    if not SIGNATURE_PATH.exists():
        return

    image = MIMEImage(SIGNATURE_PATH.read_bytes(), _subtype="png")
    image.add_header("Content-ID", f"<{SIGNATURE_CONTENT_ID}>")
    image.add_header("Content-Disposition", "inline", filename=SIGNATURE_FILENAME)
    message.attach(image)


def build_signed_email(subject, body, from_email, to, reply_to=None):
    message = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=to,
        reply_to=reply_to,
    )
    message.encoding = "utf-8"
    message.attach_alternative(f"{text_to_html(body)}{signature_html()}", "text/html")
    attach_signature_image(message)
    return message
