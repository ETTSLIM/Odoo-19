# -*- coding: utf-8 -*-
import re
import urllib.parse
import logging
import requests

_logger = logging.getLogger(__name__)

def normalize_morocco_phone(raw_phone):
    """Normalise un numéro marocain vers le format international 212XXXXXXXXX."""
    if not raw_phone:
        return False
    # Nettoyage des caractères non numériques
    clean = re.sub(r'[\s\-\.\(\)\+]', '', str(raw_phone))
    
    # 06XXXXXXXX ou 07XXXXXXXX -> 2126XXXXXXXX
    if clean.startswith('0') and len(clean) == 10:
        return '212' + clean[1:]
    # 6XXXXXXXX ou 7XXXXXXXX -> 2126XXXXXXXX
    elif (clean.startswith('6') or clean.startswith('7')) and len(clean) == 9:
        return '212' + clean
    # Déjà au format international 212XXXXXXXXX
    elif clean.startswith('212') and len(clean) >= 12:
        return clean
    return clean

def send_garage_whatsapp(env, raw_phone, message_text):
    """
    Envoie un message WhatsApp via la passerelle configurée (Evolution API, Meta Cloud API ou Lien Direct).
    Retourne un tuple: (success: bool, info: str, wa_link: str)
    """
    phone = normalize_morocco_phone(raw_phone)
    if not phone:
        return False, "Numéro de téléphone invalide", False

    params = env['ir.config_parameter'].sudo()
    provider = params.get_param('garage_repair_core.whatsapp_provider', default='evolution')
    
    # Génération du lien de secours direct wa.me
    encoded_text = urllib.parse.quote(message_text)
    wa_direct_link = f"https://api.whatsapp.com/send?phone={phone}&text={encoded_text}"

    # 1. Mode Evolution API (Standard happy-faraday)
    if provider == 'evolution':
        api_url = params.get_param('garage_repair_core.evolution_api_url', 'http://localhost:8080').rstrip('/')
        api_key = params.get_param('garage_repair_core.evolution_api_key', '')
        instance = params.get_param('garage_repair_core.evolution_instance_name', 'garage_workshop')

        if api_url and api_key and instance:
            endpoint = f"{api_url}/message/sendText/{instance}"
            headers = {"apikey": api_key, "Content-Type": "application/json"}
            payload = {"number": phone, "text": message_text}
            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=5)
                if resp.status_code in (200, 201):
                    _logger.info("WhatsApp délivré avec succès à %s via Evolution API", phone)
                    return True, "Délivré via Evolution API", wa_direct_link
                else:
                    _logger.warning("Échec Evolution API (%s): %s", resp.status_code, resp.text)
            except Exception as e:
                _logger.error("Exception connexion Evolution API: %s", str(e))

    # 2. Mode Meta WhatsApp Cloud API
    elif provider == 'meta_cloud':
        token = params.get_param('garage_repair_core.meta_api_token', '')
        phone_id = params.get_param('garage_repair_core.meta_phone_number_id', '')

        if token and phone_id:
            endpoint = f"https://graph.facebook.com/v19.0/{phone_id}/messages"
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone,
                "type": "text",
                "text": {"preview_url": True, "body": message_text}
            }
            try:
                resp = requests.post(endpoint, json=payload, headers=headers, timeout=5)
                if resp.status_code in (200, 201):
                    _logger.info("WhatsApp délivré avec succès à %s via Meta Cloud API", phone)
                    return True, "Délivré via Meta Cloud API", wa_direct_link
                else:
                    _logger.warning("Échec Meta Cloud API (%s): %s", resp.status_code, resp.text)
            except Exception as e:
                _logger.error("Exception connexion Meta Cloud API: %s", str(e))

    # 3. Fallback ou Mode Manuel Direct wa.me
    return True, "Lien direct WhatsApp Web généré", wa_direct_link
