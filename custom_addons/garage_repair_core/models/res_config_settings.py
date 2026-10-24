# -*- coding: utf-8 -*-
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Passerelle WhatsApp (Compatible happy-faraday / Evolution API / Meta Cloud API)
    whatsapp_provider = fields.Selection([
        ('evolution', 'Evolution API (Recommandé / Instance dédiée)'),
        ('meta_cloud', 'Meta WhatsApp Cloud API (Officiel)'),
        ('wa_link', 'Lien Direct WhatsApp Web (Sans API / Manuel)'),
    ], string="Passerelle WhatsApp", default='evolution',
       config_parameter='garage_repair_core.whatsapp_provider')

    # Paramètres Evolution API
    evolution_api_url = fields.Char(
        string="URL Evolution API",
        default="http://localhost:8080",
        config_parameter='garage_repair_core.evolution_api_url',
        help="Ex: http://localhost:8080 ou https://evolution.mon-domaine.com"
    )
    evolution_api_key = fields.Char(
        string="Clé API Evolution",
        config_parameter='garage_repair_core.evolution_api_key'
    )
    evolution_instance_name = fields.Char(
        string="Nom de l'Instance Evolution",
        default="garage_workshop",
        config_parameter='garage_repair_core.evolution_instance_name'
    )

    # Paramètres Meta Cloud API
    meta_api_token = fields.Char(
        string="Token Meta Cloud API (Bearer)",
        config_parameter='garage_repair_core.meta_api_token'
    )
    meta_phone_number_id = fields.Char(
        string="ID Numéro Téléphone Meta",
        config_parameter='garage_repair_core.meta_phone_number_id'
    )
