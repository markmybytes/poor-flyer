import logging
import smtplib
from email.message import Message
from email.mime.text import MIMEText
from typing import TypedDict

from src.services.config import ConfigManager

logger = logging.getLogger(__name__)


class SMTPConfig(TypedDict):
    host: str
    port: int
    user: str
    password: str
    sender_email: str
    require_auth: bool


def get_smtp_config() -> SMTPConfig:
    return {
        'host': ConfigManager.get_str('smtp', 'host') or '',
        'port': ConfigManager.get_int('smtp', 'port') or 587,
        'user': ConfigManager.get_str('smtp', 'user') or '',
        'password': ConfigManager.get_str('smtp', 'password') or '',
        'sender_email': ConfigManager.get_str('smtp', 'sender_email') or '',
        'require_auth': ConfigManager.get_bool('smtp', 'require_auth', True),
    }


def send_email(cfg: SMTPConfig, msg: Message) -> bool:
    try:
        if cfg['port'] == 465:
            with smtplib.SMTP_SSL(cfg['host'], cfg['port']) as server:
                if cfg.get('require_auth', True):
                    server.login(cfg['user'], cfg['password'])
                server.send_message(msg)
        else:
            with smtplib.SMTP(cfg['host'], cfg['port']) as server:
                server.starttls()
                if cfg.get('require_auth', True):
                    server.login(cfg['user'], cfg['password'])
                server.send_message(msg)
        return True
    except Exception as e:
        logger.error(f'SMTP error: {e}')
        return False


def send_text_email(cfg: SMTPConfig, rec: str, sub: str, txt: str) -> bool:
    return send_email(cfg, _prepare_msg(cfg, rec, sub, MIMEText(txt, 'plain')))


def send_html_email(cfg: SMTPConfig, rec: str, sub: str, html: str) -> bool:
    return send_email(cfg, _prepare_msg(cfg, rec, sub, MIMEText(html, 'html')))


def _prepare_msg(cfg: SMTPConfig, rec: str, sub: str, body: Message) -> Message:
    body['From'], body['To'], body['Subject'] = cfg.get('sender_email') or cfg['user'], rec, sub
    return body
