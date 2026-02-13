import logging
from datetime import datetime
from pathlib import Path
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("email.log"),  
        logging.StreamHandler() 
    ]
)

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_SSL_TLS=True,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=False,
    TEMPLATE_FOLDER=Path(__file__).resolve().parent.parent.parent / "templates",
    MAIL_DEBUG=True,
    MAIL_STARTTLS=False
)




async def send_email(to: list[str], subject: str, context: dict):
    print(conf)
    try:
        logger.info(f"Attempting to send email to: {to} | Subject: {subject}")
        logger.debug(f"Email context: {context}")

        message = MessageSchema(
            subject=subject,
            recipients=to,
            template_body=dict(**context, current_year=datetime.now().year),
            subtype=MessageType.html,
        )

        fm = FastMail(conf)
        await fm.send_message(message, template_name="base.html")

        logger.info(f"Email successfully sent to {to}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to} | Error: {e}", exc_info=True)
        return False