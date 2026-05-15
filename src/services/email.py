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
    protocol: str  # 'SMTP', 'SMTP_SSL', 'STARTTLS'


def get_smtp_config() -> SMTPConfig:
    protocol = ConfigManager.get_str('smtp', 'protocol') or 'STARTTLS'
    return {
        'host': ConfigManager.get_str('smtp', 'host') or '',
        'port': ConfigManager.get_int('smtp', 'port') or 587,
        'user': ConfigManager.get_str('smtp', 'user') or '',
        'password': ConfigManager.get_str('smtp', 'password') or '',
        'sender_email': ConfigManager.get_str('smtp', 'sender_email') or '',
        'require_auth': ConfigManager.get_bool('smtp', 'require_auth', True),
        'protocol': protocol,
    }


def send_email(cfg: SMTPConfig, msg: Message) -> bool:
    try:
        protocol = cfg.get('protocol', 'STARTTLS')
        require_auth = cfg.get('require_auth', True)

        if protocol == 'SMTP_SSL':
            with smtplib.SMTP_SSL(cfg['host'], cfg['port']) as server:
                if require_auth:
                    server.login(cfg['user'], cfg['password'])
                server.send_message(msg)
        else:  # STARTTLS (default)
            with smtplib.SMTP(cfg['host'], cfg['port']) as server:
                server.starttls()
                if require_auth:
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
