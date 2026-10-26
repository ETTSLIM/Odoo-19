# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class GaragePhotoGalleryWizard(models.TransientModel):
    _name = 'garage.photo.gallery.wizard'
    _description = "Galerie Photos & Visionneuse de Documents"

    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", readonly=True)
    claim_id = fields.Many2one('garage.insurance.claim', string="Dossier Sinistre", readonly=True)

    vehicle_name = fields.Char(string="Véhicule", compute='_compute_header_info')
    license_plate = fields.Char(string="Immatriculation", compute='_compute_header_info')

    category_filter = fields.Selection([
        ('all', "Toutes les photos"),
        ('papiers', "Papiers & Documents"),
        ('chocs', "Dégâts & Chocs"),
        ('atelier', "Travaux Atelier"),
    ], default='all', string="Filtre Catégorie")

    current_index = fields.Integer(default=0, string="Index Photo")
    total_count = fields.Integer(compute='_compute_gallery_data', string="Total Photos")

    current_image_binary = fields.Binary(compute='_compute_gallery_data', string="Image Active")
    current_image_id = fields.Many2one('ir.attachment', compute='_compute_gallery_data', string="Pièce Jointe Active")
    current_image_name = fields.Char(compute='_compute_gallery_data', string="Nom Image")
    current_image_category = fields.Char(compute='_compute_gallery_data', string="Catégorie Image")
    current_image_date = fields.Datetime(compute='_compute_gallery_data', string="Date Image")
    current_image_url = fields.Char(compute='_compute_gallery_data', string="URL Image")

    counter_display = fields.Char(compute='_compute_gallery_data', string="Compteur")
    has_images = fields.Boolean(compute='_compute_gallery_data', string="Contient des Images")

    all_count = fields.Integer(compute='_compute_category_counts', string="Nb Total")
    papiers_count = fields.Integer(compute='_compute_category_counts', string="Nb Papiers")
    chocs_count = fields.Integer(compute='_compute_category_counts', string="Nb Chocs")
    atelier_count = fields.Integer(compute='_compute_category_counts', string="Nb Atelier")

    @api.depends('reception_id', 'claim_id')
    def _compute_header_info(self):
        for wiz in self:
            v_name = ""
            plate = ""
            if wiz.reception_id:
                plate = wiz.reception_id.license_plate or ""
                v_name = wiz.reception_id.vehicle_model_name or (wiz.reception_id.vehicle_id.name if wiz.reception_id.vehicle_id else "")
            elif wiz.claim_id:
                plate = wiz.claim_id.license_plate or ""
                v_name = wiz.claim_id.vehicle_id.name if wiz.claim_id.vehicle_id else ""
            wiz.license_plate = plate
            wiz.vehicle_name = v_name

    def _get_all_source_attachments(self):
        self.ensure_one()
        atts = self.env['ir.attachment']
        if self.reception_id:
            atts |= self.reception_id.attachment_ids
            atts |= self.reception_id.carte_grise_ids
            atts |= self.reception_id.permis_ids
            atts |= self.reception_id.constat_ids
            atts |= self.reception_id.damage_item_ids.photo_ids
        if self.claim_id:
            atts |= self.claim_id.attachment_ids
            atts |= self.claim_id.carte_grise_ids
            atts |= self.claim_id.permis_ids
            atts |= self.claim_id.constat_ids
            atts |= self.claim_id.assurance_ids
            atts |= self.claim_id.damage_item_ids.photo_ids
        return atts

    def _get_filtered_attachments(self, category):
        self.ensure_one()
        pool = self._get_all_source_attachments()
        if not pool:
            return self.env['ir.attachment']

        papiers_ids = set()
        if self.reception_id:
            papiers_ids.update((self.reception_id.carte_grise_ids | self.reception_id.permis_ids | self.reception_id.constat_ids).ids)
        if self.claim_id:
            papiers_ids.update((self.claim_id.carte_grise_ids | self.claim_id.permis_ids | self.claim_id.constat_ids | self.claim_id.assurance_ids).ids)

        papiers_keywords = ['carte', 'grise', 'permis', 'constat', 'assurance', 'papier', 'document', 'justificatif']
        atelier_keywords = ['atelier', 'travaux', 'reparation', 'mecanicien', 'diag', 'pont', 'vidange']

        papiers_atts = pool.filtered(lambda a: a.id in papiers_ids or any(k in (a.name or '').lower() for k in papiers_keywords))
        atelier_atts = pool.filtered(lambda a: any(k in (a.name or '').lower() for k in atelier_keywords) and a.id not in papiers_atts.ids)
        chocs_atts = pool.filtered(lambda a: a.id not in papiers_atts.ids and a.id not in atelier_atts.ids)

        if category == 'papiers':
            return papiers_atts
        elif category == 'atelier':
            return atelier_atts
        elif category == 'chocs':
            return chocs_atts
        return pool

    def _classify_attachment(self, att):
        self.ensure_one()
        papiers_atts = self._get_filtered_attachments('papiers')
        atelier_atts = self._get_filtered_attachments('atelier')
        if att.id in papiers_atts.ids:
            return _("📄 Dossier Papiers & Documents Légaux")
        elif att.id in atelier_atts.ids:
            return _("🔧 Suivi des Travaux Atelier")
        else:
            return _("💥 Constat Dégâts & Chocs Véhicule")

    @api.depends('category_filter', 'current_index', 'reception_id', 'claim_id')
    def _compute_gallery_data(self):
        for wiz in self:
            filtered_atts = wiz._get_filtered_attachments(wiz.category_filter)
            count = len(filtered_atts)
            wiz.total_count = count
            if count == 0:
                wiz.current_image_binary = False
                wiz.current_image_id = False
                wiz.current_image_name = _("Aucune photo dans cette catégorie")
                wiz.current_image_category = ""
                wiz.current_image_date = False
                wiz.current_image_url = ""
                wiz.counter_display = "0 / 0"
                wiz.has_images = False
            else:
                idx = max(0, min(wiz.current_index, count - 1))
                att = filtered_atts[idx]
                wiz.current_image_binary = att.datas
                wiz.current_image_id = att.id
                wiz.current_image_name = att.name or f"Photo #{idx + 1}"
                wiz.current_image_category = wiz._classify_attachment(att)
                wiz.current_image_date = att.create_date
                wiz.current_image_url = f"/web/image/{att.id}"
                wiz.counter_display = f"Photo {idx + 1} sur {count}"
                wiz.has_images = True

    @api.depends('reception_id', 'claim_id')
    def _compute_category_counts(self):
        for wiz in self:
            wiz.all_count = len(wiz._get_filtered_attachments('all'))
            wiz.papiers_count = len(wiz._get_filtered_attachments('papiers'))
            wiz.chocs_count = len(wiz._get_filtered_attachments('chocs'))
            wiz.atelier_count = len(wiz._get_filtered_attachments('atelier'))

    def action_next(self):
        self.ensure_one()
        filtered = self._get_filtered_attachments(self.category_filter)
        if filtered:
            new_idx = (self.current_index + 1) % len(filtered)
            self.write({'current_index': new_idx})
        return self._reopen_self()

    def action_prev(self):
        self.ensure_one()
        filtered = self._get_filtered_attachments(self.category_filter)
        if filtered:
            new_idx = (self.current_index - 1) % len(filtered)
            self.write({'current_index': new_idx})
        return self._reopen_self()

    def action_filter_all(self):
        self.ensure_one()
        self.write({'category_filter': 'all', 'current_index': 0})
        return self._reopen_self()

    def action_filter_papiers(self):
        self.ensure_one()
        self.write({'category_filter': 'papiers', 'current_index': 0})
        return self._reopen_self()

    def action_filter_chocs(self):
        self.ensure_one()
        self.write({'category_filter': 'chocs', 'current_index': 0})
        return self._reopen_self()

    def action_filter_atelier(self):
        self.ensure_one()
        self.write({'category_filter': 'atelier', 'current_index': 0})
        return self._reopen_self()

    def _reopen_self(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
