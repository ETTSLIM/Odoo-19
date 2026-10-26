# -*- coding: utf-8 -*-
import io
import socket
import base64
import logging
from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)

try:
    import qrcode
except ImportError:
    qrcode = None


class GarageTabletPairingWizard(models.TransientModel):
    _name = 'garage.tablet.pairing.wizard'
    _description = "Assistant d'Appairage Tablette Atelier (Zero-CLI)"

    name = fields.Char(string="Titre", default="Appairage Tablette Atelier")
    server_url = fields.Char(string="Adresse Hostname", readonly=True)
    lan_ip_url = fields.Char(string="Adresse IP Locale", readonly=True)
    qr_code = fields.Binary(string="Code QR de Connexion", readonly=True)
    instructions = fields.Html(string="Instructions", readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        # 1. Résolution de l'adresse Bonjour / mDNS
        hostname = "MacBook-Pro.local"
        server_url = f"http://{hostname}:8069"

        # 2. Détection de l'IP locale de la machine hôte
        lan_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            lan_ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                lan_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                lan_ip = "192.168.100.11"

        lan_ip_url = f"http://{lan_ip}:8069"

        # 3. Génération dynamique du Code QR (pointe vers server_url)
        qr_b64 = False
        target_pair_url = server_url
        if qrcode:
            try:
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_M,
                    box_size=8,
                    border=2,
                )
                qr.add_data(target_pair_url)
                qr.make(fit=True)
                img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
                buf = io.BytesIO()
                img.save(buf, format='PNG')
                qr_b64 = base64.b64encode(buf.getvalue())
            except Exception as e:
                _logger.warning("Erreur génération QR Code appairage: %s", e)

        res.update({
            'server_url': server_url,
            'lan_ip_url': lan_ip_url,
            'qr_code': qr_b64,
            'instructions': f"""
                <div dir="rtl" style="font-family: system-ui, sans-serif; text-align: right; line-height: 1.6;">
                    <p style="font-size: 15px; font-weight: bold; color: #0284c7; margin-bottom: 6px;">
                        📲 ربط طابليط الورشة بنظام Odoo المحلي (Zero-CLI) :
                    </p>
                    <ol style="margin-top: 0; padding-right: 20px; font-size: 13.5px; color: #334155;">
                        <li>تأكد أن الطابليط والحاسوب متصلان بنفس شبكة <b>الـ Wi-Fi</b> أو <b>نقطة اتصال الهاتف (Partage 4G)</b>.</li>
                        <li>افتح تطبيق <b>Garage AI Workshop</b> على الطابليط.</li>
                        <li>انقر على أيقونة الإعدادات <b>(⚙️)</b> في أعلى الشاشة واختر <b>مسح الرمز (Scanner QR)</b>.</li>
                        <li>وجه كاميرا الطابليط نحو الرمز أسفله للاتصال التلقائي الفوري دون كتابة أي أرقام!</li>
                    </ol>
                </div>
            """
        })
        return res
