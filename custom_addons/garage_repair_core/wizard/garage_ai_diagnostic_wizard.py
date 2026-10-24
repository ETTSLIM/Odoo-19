# -*- coding: utf-8 -*-
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class GarageAiDiagnosticWizard(models.TransientModel):
    _name = 'garage.ai.diagnostic.wizard'
    _description = "Assistant de Diagnostic IA & Tâches Dynamiques Atelier"

    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", required=True, ondelete='cascade')
    vehicle_id = fields.Many2one(related='reception_id.vehicle_id', string="Véhicule", readonly=True)
    license_plate = fields.Char(related='reception_id.license_plate', string="Immatriculation", readonly=True)

    audio_file = fields.Binary(string="Enregistrement Vocal (Audio)",
                               help="Fichier audio du diagnostic mécanicien (mp3, wav, m4a, ogg, webm).")
    audio_filename = fields.Char(string="Nom du fichier audio")

    raw_note = fields.Text(
        string="Notes / Constat du Mécanicien (Darija / Français)",
        help="Ex: إصلاح البارشو الأمامي، إصلاح الكابو ديال الموتور، تغيير زيت المحرك 5W30، تغيير فلتر المازوط، مراقبة البلاكيط..."
    )

    specialty = fields.Selection([
        ('mecanique', "🔧 Mécanique Générale & Moteur"),
        ('carrosserie', "🎨 Tôlerie, Carrosserie & Peinture"),
        ('electricite', "⚡ Électricité & Diagnostic OBD"),
        ('entretien', "🛢️ Entretien Rapide & Freinage"),
        ('climatisation', "❄️ Climatisation & Refroidissement"),
        ('pneumatique', "🛞 Pneumatiques & Géométrie 3D"),
    ], string="Spécialité Atelier Détectée")

    is_assurance = fields.Boolean(string="Dossier Sinistre / Assurance")

    extracted_todos = fields.Text(
        string="Tâches Personnalisées Détectées (Une par ligne)",
        help="Chaque ligne deviendra une micro-tâche verrouillée [Étape 4 • مخصصة] à l'Atelier..."
    )

    @api.onchange('raw_note')
    def _onchange_raw_note(self):
        """Pré-remplit les tâches extraites si des lignes sont saisies."""
        if self.raw_note and not self.extracted_todos:
            lines = [l.strip().lstrip('-•*').strip() for l in self.raw_note.split('\n') if len(l.strip()) >= 3]
            if lines:
                self.extracted_todos = "\n".join(lines)

    def action_process(self):
        """Lance l'interprétation IA et la création des micro-tâches dynamiques verrouillées."""
        self.ensure_one()
        audio_b64 = None
        if self.audio_file:
            audio_b64 = self.audio_file.decode('utf-8') if isinstance(self.audio_file, bytes) else str(self.audio_file)

        todos = []
        if self.extracted_todos:
            todos = [l.strip().lstrip('-•*').strip() for l in self.extracted_todos.split('\n') if l.strip()]

        res = self.reception_id.process_ai_diagnostic(
            audio_base64=audio_b64,
            raw_note=self.raw_note or '',
            custom_todos=todos,
            is_assurance=self.is_assurance,
            workshop_type=self.specialty,
        )

        todo_count = len(res.get('todo_tasks', []))
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Interprétation IA Réussie"),
                'message': _("%d micro-tâches dynamiques [Étape 4 • مخصصة] ont été injectées et verrouillées dans la gamme d'atelier.", todo_count),
                'sticky': False,
                'type': 'success',
            }
        }
