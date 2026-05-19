from flask import Blueprint, jsonify, render_template, request

from src.services.config import ConfigManager
from src.services.email import get_smtp_config, send_html_email

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('', methods=['GET'])
def get_settings():
    try:
        return jsonify(
            {
                'success': True,
                'data': {ns: ConfigManager.get_all_masked(ns) for ns in ['smtp', 'email']},
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('', methods=['POST'])
def update_settings():
    try:
        data = request.get_json(silent=True) or request.form.to_dict()

        if smtp := data.get('smtp', {}):
            port = smtp.get('port', 587)
            try:
                port = int(port)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'message': 'SMTP port must be an integer'}), 400

            smtp_settings = {
                'host': smtp.get('host', ''),
                'port': str(port),
                'user': smtp.get('user', ''),
                'sender_email': smtp.get('sender_email', ''),
                'require_auth': 'true' if smtp.get('require_auth', True) else 'false',
                'protocol': smtp.get('protocol', 'STARTTLS'),
            }

            if smtp.get('password'):
                smtp_settings['password'] = smtp['password']

            ConfigManager.set_many('smtp', smtp_settings)

        if email := data.get('email', {}):
            ConfigManager.set_many('email', {'recipients': email.get('recipients', '')})

        return jsonify({'success': True, 'message': 'Settings updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400


@settings_bp.route('/test-email', methods=['POST'])
def test_email():
    try:
        data = request.get_json(silent=True) or request.form.to_dict()
        recipient = data.get('recipient', '').strip()

        if not recipient:
            return jsonify(
                {'success': False, 'message': 'Recipient email address is required'}
            ), 400

        success = send_html_email(
            get_smtp_config(),
            recipient,
            'PoorFlyer - Test Email',
            render_template('email/test_email.html'),
        )

        if success:
            return jsonify({'success': True, 'message': f'Test email sent to {recipient}'})
        return jsonify(
            {
                'success': False,
                'message': 'Failed to send test email. Check SMTP configuration and logs.',
            }
        ), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
