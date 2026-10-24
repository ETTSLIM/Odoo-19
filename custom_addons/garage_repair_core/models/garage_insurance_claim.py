# -*- coding: utf-8 -*-
import uuid
import urllib.parse
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from .whatsapp_gateway import send_garage_whatsapp, normalize_morocco_phone


class GarageInsuranceClaim(models.Model):
    _name = 'garage.insurance.claim'
    _description = "Dossier Sinistre & Expertise Automobile"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc, id desc'

    name = fields.Char(string="Référence Interne", required=True, copy=False, readonly=True,
                       default=lambda self: _('Nouveau'))
    claim_number = fields.Char(string="N° Sinistre Compagnie", required=True, tracking=True,
                               help="Ex: SIN-WAFA-984210")
    police_number = fields.Char(string="N° Police / Attestation", tracking=True)

    # Compagnie & Cabinet d'Expertise
    insurance_id = fields.Many2one('res.partner', string="Compagnie d'Assurance", required=True,
                                   domain="[('is_insurance_company', '=', True)]", tracking=True)
    insurance_ice = fields.Char(related='insurance_id.ice', string="ICE Assureur", readonly=True)
    insurance_agent = fields.Char(string="Agence / Courtier", tracking=True)

    expert_cabinet_id = fields.Many2one('res.partner', string="Cabinet d'Expertise",
                                        domain="[('is_expert_cabinet', '=', True)]", tracking=True)
    expert_name = fields.Char(string="Nom de l'Expert", tracking=True)
    expert_email = fields.Char(string="Email Expert", tracking=True)
    expert_phone = fields.Char(string="Tél / WhatsApp Expert", tracking=True)

    # Véhicule & Assuré
    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule Accidenté", required=True, tracking=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string="Immatriculation", store=True)
    vin_number = fields.Char(related='vehicle_id.vin_number', string="N° Châssis (VIN)", readonly=True)
    customer_id = fields.Many2one('res.partner', string="Client / Assuré", required=True, tracking=True)
    customer_phone = fields.Char(related='customer_id.phone', string="Téléphone Assuré", readonly=False)
    customer_cin = fields.Char(related='customer_id.cin', string="CIN Assuré", readonly=True)

    # Liaisons Opérations
    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", tracking=True)
    repair_order_id = fields.Many2one('repair.order', string="Ordre de Réparation", tracking=True)

    # Dates
    accident_date = fields.Date(string="Date de l'Accident", default=fields.Date.context_today, tracking=True)
    expert_visit_date = fields.Date(string="Date Visite Expert", tracking=True)
    accord_date = fields.Date(string="Date Bon d'Accord", tracking=True)

    # Statuts & Cycle de Vie (Libellés concis 1-ligne)
    state = fields.Selection([
        ('draft', 'Nouveau'),
        ('dossier_sent', 'Transmis Expert'),
        ('expert_review', 'Expertise'),
        ('amendment_pending', 'Avenant'),
        ('accord_approved', 'BA Validé'),
        ('in_repair', 'En Atelier'),
        ('repaired', 'Prêt / À Facturer'),
        ('invoiced', 'Facturé'),
        ('closed', 'Clôturé'),
        ('cancel', 'Annulé'),
    ], string="État du Sinistre", default='draft', tracking=True)

    # Descriptif Dommages & Photos
    shock_location = fields.Selection([
        ('front', 'Choc Avant'),
        ('rear', 'Choc Arrière'),
        ('left', 'Choc Latéral Gauche'),
        ('right', 'Choc Latéral Droit'),
        ('multiple', 'Chocs Multiples / Marbre / Tonneau'),
    ], string="Localisation du Choc", default='front', required=True)
    damage_notes = fields.Text(string="Constat Visuel & Éléments Endommagés")
    attachment_ids = fields.Many2many(
        'ir.attachment', 'garage_insurance_claim_attachment_rel',
        'claim_id', 'attachment_id',
        string="Photos de Choc & Documents"
    )
    attachment_count = fields.Integer(string="Nb. Photos & Pièces", compute='_compute_attachment_count')

    # Checklist Documents Justificatifs Assurances
    doc_carte_grise = fields.Boolean(string="Carte Grise / Certificat", tracking=True)
    doc_permis = fields.Boolean(string="Permis de Conduire Assuré", tracking=True)
    doc_constat = fields.Boolean(string="Constat Amiable / Récépissé", tracking=True)
    doc_bon_accord = fields.Boolean(string="Bon d'Accord Signé", tracking=True)

    # Données Financières - Chiffrage Garage
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    initial_estimate_parts = fields.Monetary(string="Pièces Devis Initial HT", default=0.0)
    initial_estimate_labor = fields.Monetary(string="Main-d'Œuvre Devis Initial HT", default=0.0)
    claim_estimate_untaxed = fields.Monetary(string="Chiffrage Initial Total HT", compute='_compute_claim_estimate', store=True, readonly=False)

    # Avenants
    amendment_ids = fields.One2many('garage.insurance.amendment', 'claim_id', string="Avenants (Dégâts Masqués)")
    amendments_count = fields.Integer(string="Nombre d'Avenants", compute='_compute_amendments', store=True)
    amendment_total_untaxed = fields.Monetary(string="Total Avenants HT", compute='_compute_amendments', store=True)
    total_garage_claim_untaxed = fields.Monetary(string="Total Réclamation Atelier HT", compute='_compute_total_claim', store=True)

    # Bon d'Accord Expert & Répartition (Split)
    expert_accord_amount_untaxed = fields.Monetary(string="Montant Agréé Expert HT (Pièces Neuves & MO)", default=0.0, tracking=True)
    expert_used_parts_net = fields.Monetary(string="Pièces d'Occasion Agréées Net", default=0.0, tracking=True,
                                           help="Montant net forfaitaire agréé par l'expert pour les pièces de réemploi/casse (TVA refusée par l'expert)")
    used_parts_vat_shortfall = fields.Monetary(string="TVA Récupérée en Vétusté (20%)", compute='_compute_accord_totals', store=True,
                                              help="TVA à 20% sur pièces d'occasion refusée par l'expert, imputée légalement en vétusté à l'assuré")
    expert_accord_amount_tax = fields.Monetary(string="TVA Agréée (20%)", compute='_compute_accord_totals', store=True)
    expert_accord_amount_ttc = fields.Monetary(string="Montant Agréé Expert TTC", compute='_compute_accord_totals', store=True)

    # Accord Client sur Avis Expert (Obligatoire avant atelier)
    client_accord_status = fields.Selection([
        ('pending', 'En Attente Accord Client'),
        ('approved', 'Avis Expert Validé par le Client'),
        ('contested', 'Contesté par le Client'),
    ], string="Accord Client sur Avis Expert", default='pending', tracking=True)
    client_accord_date = fields.Datetime(string="Date Accord Client", readonly=True, tracking=True)
    client_accord_ip = fields.Char(string="Canal / IP Accord Client", readonly=True)
    client_accord_notes = fields.Text(string="Remarques / Réserves du Client")

    franchise_type = fields.Selection([
        ('fixed', 'Montant Fixe (MAD)'),
        ('percent', 'Pourcentage sur Dégâts (%)'),
    ], string="Type de Franchise", default='fixed', required=True)
    franchise_rate = fields.Float(string="Taux Franchise (%)", default=0.0)
    franchise_amount = fields.Monetary(string="Franchise Client TTC", default=0.0, tracking=True)
    wear_amount = fields.Monetary(string="Vétusté Pièces d'Usure TTC", default=0.0, tracking=True,
                                  help="Abattement appliqué par l'expert sur pneus, amortisseurs, batterie, etc.")

    # Décompte Scindé Automatique
    insurance_net_payable = fields.Monetary(string="Prise en Charge Compagnie TTC", compute='_compute_split_amounts', store=True)
    insurance_net_untaxed = fields.Monetary(string="Prise en Charge Compagnie HT", compute='_compute_split_amounts', store=True)
    customer_payable = fields.Monetary(string="Part à Payer Client TTC (Franchise + Vétusté)", compute='_compute_split_amounts', store=True)
    customer_payable_untaxed = fields.Monetary(string="Part Client HT", compute='_compute_split_amounts', store=True)

    # Factures Scindées
    insurance_invoice_id = fields.Many2one('account.move', string="Facture Compagnie d'Assurance", copy=False, readonly=True)
    customer_invoice_id = fields.Many2one('account.move', string="Facture / Reçu Franchise Client", copy=False, readonly=True)
    invoice_count = fields.Integer(string="Factures Scindées", compute='_compute_invoice_count')
    is_invoiced = fields.Boolean(string="Facturé", compute='_compute_is_invoiced', store=True)

    # Jeton de suivi client
    tracking_token = fields.Char(string="Lien Suivi Client", compute='_compute_tracking_token', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('Nouveau')) == _('Nouveau'):
                vals['name'] = self.env['ir.sequence'].next_by_code('garage.insurance.claim') or _('Nouveau')
        return super().create(vals_list)

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id(self):
        if self.vehicle_id and self.vehicle_id.customer_id:
            self.customer_id = self.vehicle_id.customer_id

    @api.depends('repair_order_id.tracking_token', 'reception_id.tracking_token')
    def _compute_tracking_token(self):
        for claim in self:
            token = False
            if claim.repair_order_id and claim.repair_order_id.tracking_token:
                token = claim.repair_order_id.tracking_token
            elif claim.reception_id and claim.reception_id.tracking_token:
                token = claim.reception_id.tracking_token
            if not token:
                token = claim.tracking_token or uuid.uuid4().hex[:12]
            claim.tracking_token = token

    @api.depends('initial_estimate_parts', 'initial_estimate_labor', 'repair_order_id.amount_untaxed_total')
    def _compute_claim_estimate(self):
        for claim in self:
            if claim.repair_order_id and not (claim.initial_estimate_parts or claim.initial_estimate_labor):
                claim.claim_estimate_untaxed = claim.repair_order_id.amount_untaxed_total
            else:
                claim.claim_estimate_untaxed = claim.initial_estimate_parts + claim.initial_estimate_labor

    @api.depends('amendment_ids.total_untaxed', 'amendment_ids.state')
    def _compute_amendments(self):
        for claim in self:
            valid_amendments = claim.amendment_ids.filtered(lambda a: a.state in ('submitted', 'approved'))
            claim.amendments_count = len(claim.amendment_ids)
            claim.amendment_total_untaxed = sum(valid_amendments.mapped('total_untaxed'))

    @api.depends('claim_estimate_untaxed', 'amendment_total_untaxed')
    def _compute_total_claim(self):
        for claim in self:
            claim.total_garage_claim_untaxed = claim.claim_estimate_untaxed + claim.amendment_total_untaxed

    @api.depends('expert_accord_amount_untaxed', 'expert_used_parts_net')
    def _compute_accord_totals(self):
        for claim in self:
            tax = round(claim.expert_accord_amount_untaxed * 0.20, 2)
            claim.expert_accord_amount_tax = tax
            claim.used_parts_vat_shortfall = round(claim.expert_used_parts_net * 0.20, 2)
            # Total agréé TTC = Base taxable TTC (Pièces neuves & MO) + Pièces d'occasion net
            claim.expert_accord_amount_ttc = round(claim.expert_accord_amount_untaxed * 1.20, 2) + claim.expert_used_parts_net

    @api.onchange('franchise_type', 'franchise_rate', 'expert_accord_amount_ttc')
    def _onchange_franchise_calc(self):
        if self.franchise_type == 'percent' and self.franchise_rate:
            self.franchise_amount = round(self.expert_accord_amount_ttc * (self.franchise_rate / 100.0), 2)

    @api.depends('expert_accord_amount_ttc', 'franchise_amount', 'wear_amount', 'used_parts_vat_shortfall')
    def _compute_split_amounts(self):
        for claim in self:
            # La part client comprend la franchise contractuelle, la vétusté standard, ET la TVA récupérée en vétusté sur pièces d'occasion
            cust_ttc = claim.franchise_amount + claim.wear_amount + claim.used_parts_vat_shortfall
            claim.customer_payable = cust_ttc
            claim.customer_payable_untaxed = round(cust_ttc / 1.20, 2) if cust_ttc else 0.0

            # La compagnie d'assurance paie le montant agréé TTC diminué de la franchise et vétusté standard
            # (Le manque à gagner TVA n'impute PAS la compagnie, il est réglé par le client)
            ins_ttc = max(0.0, claim.expert_accord_amount_ttc - claim.franchise_amount - claim.wear_amount)
            claim.insurance_net_payable = ins_ttc
            claim.insurance_net_untaxed = round(ins_ttc / 1.20, 2) if ins_ttc else 0.0

    @api.depends('insurance_invoice_id', 'customer_invoice_id')
    def _compute_is_invoiced(self):
        for claim in self:
            claim.is_invoiced = bool(claim.insurance_invoice_id or claim.customer_invoice_id)

    @api.depends('attachment_ids')
    def _compute_attachment_count(self):
        for rec in self:
            rec.attachment_count = len(rec.attachment_ids)

    @api.depends('insurance_invoice_id', 'customer_invoice_id')
    def _compute_invoice_count(self):
        for claim in self:
            count = 0
            if claim.insurance_invoice_id:
                count += 1
            if claim.customer_invoice_id:
                count += 1
            claim.invoice_count = count

    # Navigation Smart Buttons (1-Clic)
    def action_view_attachments(self):
        """Affiche les photos de choc et documents du dossier sinistre."""
        self.ensure_one()
        return {
            'name': _("Photos & Justificatifs - Sinistre %s", self.claim_number),
            'type': 'ir.actions.act_window',
            'res_model': 'ir.attachment',
            'view_mode': 'kanban,list,form',
            'domain': [('id', 'in', self.attachment_ids.ids)],
            'context': {'default_res_model': 'garage.insurance.claim', 'default_res_id': self.id},
        }

    def action_view_reception(self):
        """Ouvre la fiche de réception associée."""
        self.ensure_one()
        if not self.reception_id:
            raise UserError(_("Aucune fiche de réception associée."))
        return {
            'name': _("Fiche de Réception"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.reception',
            'res_id': self.reception_id.id,
            'view_mode': 'form',
        }

    def action_view_repair_order(self):
        """Ouvre l'ordre de réparation associé."""
        self.ensure_one()
        if not self.repair_order_id:
            raise UserError(_("Aucun ordre de réparation associé."))
        return {
            'name': _("Ordre de Réparation"),
            'type': 'ir.actions.act_window',
            'res_model': 'repair.order',
            'res_id': self.repair_order_id.id,
            'view_mode': 'form',
        }

    def action_view_amendments(self):
        """Affiche les avenants pour pièces masquées."""
        self.ensure_one()
        return {
            'name': _("Avenants Sinistre %s", self.claim_number),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.insurance.amendment',
            'view_mode': 'list,form',
            'domain': [('claim_id', '=', self.id)],
            'context': {'default_claim_id': self.id},
        }

    # Actions Métier
    def action_send_dossier_expert(self):
        """Transmet le dossier et photos à l'expert."""
        self.ensure_one()
        self.write({'state': 'dossier_sent'})
        self.message_post(body=Markup(_(
            "Dossier Sinistre et pièces justificatives transmis au Cabinet d'Expertise <b>%s</b>."
        ) % (self.expert_cabinet_id.name or self.expert_name or 'Expert')))
        return True

    def action_expert_visit(self):
        """Passe le dossier en examen / contre-visite expert."""
        self.ensure_one()
        self.write({
            'state': 'expert_review',
            'expert_visit_date': fields.Date.context_today(self),
        })
        self.message_post(body=Markup(_(
            "Visite contradictoire de l'Expert réalisée le <b>%s</b>."
        ) % fields.Date.context_today(self)))
        return True

    def action_request_amendment(self):
        """Ouvre un dialogue pour saisir un nouvel avenant pour pièces cachées."""
        self.ensure_one()
        self.write({'state': 'amendment_pending'})
        return {
            'name': _("Nouvel Avenant Pièces Masquées"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.insurance.amendment',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_claim_id': self.id,
                'default_name': _("Avenant %d - Dégâts Masqués Découverts au Démontage", len(self.amendment_ids) + 1),
            }
        }

    def action_approve_accord(self):
        """Valide le Bon d'Accord Définitif de l'Expert."""
        self.ensure_one()
        if not self.expert_accord_amount_untaxed and not self.expert_accord_amount_ttc:
            raise UserError(_("Veuillez renseigner le montant agréé par l'expert avant de valider l'accord."))
        self.write({
            'state': 'accord_approved',
            'accord_date': fields.Date.context_today(self),
        })
        self.message_post(body=Markup(
            "<b>Bon d'Accord Définitif Validé</b><br/>"
            "• Montant Agréé : <b>%s MAD TTC</b><br/>"
            "• Net Compagnie : <b>%s MAD TTC</b><br/>"
            "• Franchise / Vétusté Client : <b>%s MAD TTC</b>"
        ) % (
            self.expert_accord_amount_ttc, self.insurance_net_payable, self.customer_payable
        ))
        if self.reception_id:
            self.reception_id.with_context(auto_workflow_sync=True).write({'statut_expertise': 'accord_valide'})
            task_2c = self.reception_id.task_ids.filtered(
                lambda t: ("2c" in t.name.lower() or "accord expert" in t.name.lower() or "خبير" in t.name.lower()) and t.state != '1_done'
            )
            for st in task_2c:
                st.with_context(auto_workflow_sync=True).write({
                    'state': '1_done',
                    'is_done': True,
                    'completed_date': fields.Datetime.now(),
                })
            stage_2 = self.env['garage.workshop.stage'].search([('sequence', '=', 20)], limit=1)
            if stage_2:
                self.reception_id._check_and_auto_advance_stage(stage_2)
        # Notifie le client sur WhatsApp si possible
        self._notify_customer_accord()
        return True

    def _notify_customer_accord(self):
        """Notification WhatsApp au client l'informant de l'accord expert et du montant éventuel de franchise."""
        if not self.customer_phone:
            return
        phone = normalize_morocco_phone(self.customer_phone)
        if not phone:
            return
        portal_url = f"{self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')}/garage/tracking/{self.tracking_token}" if hasattr(self, 'tracking_token') and self.tracking_token else ""
        msg = (
            f"🚗 *Garage Pro Sinistre* - Avis Expert Reçu\n"
            f"Véhicule: *{self.vehicle_id.name}* ({self.license_plate})\n"
            f"Dossier: *{self.claim_number}* ({self.insurance_id.name})\n\n"
            f"L'expert automobile a émis son décompte chiffré :\n"
            f"• Prise en charge Assurance : *{self.insurance_net_payable:,.2f} MAD TTC*\n"
        )
        if self.customer_payable > 0:
            msg += f"• Franchise / Vétusté fixée par l'expert : *{self.customer_payable:,.2f} MAD TTC*\n\n"
        else:
            msg += "• Prise en charge à 100% sans franchise.\n\n"
        
        msg += "⚠️ *Important :* Conformément aux procédures, votre approbation préalable est obligatoire avant tout démarrage des travaux en atelier.\n\n"
        if portal_url:
            msg += f"👉 Consultez et validez l'avis expert en 1 clic sur votre lien sécurisé :\n{portal_url}"

        send_garage_whatsapp(self.env, phone, msg)

    def action_start_repair(self):
        """Lance les travaux d'atelier - Bloqué tant que le client n'a pas validé l'avis expert."""
        self.ensure_one()
        if self.client_accord_status != 'approved':
            raise UserError(_(
                "Impossible de démarrer les travaux : L'approbation de l'expert n'est pas suffisante !\n\n"
                "Le propriétaire du véhicule doit impérativement donner son accord préalable sur l'avis de l'expert, "
                "la franchise et la vétusté avant tout début d'intervention en atelier.\n\n"
                "Veuillez faire valider le client via le lien magique WhatsApp ou cliquer sur 'Valider Accord Client' au guichet."
            ))
        self.write({'state': 'in_repair'})
        if self.repair_order_id and self.repair_order_id.state in ('draft', 'confirmed'):
            try:
                self.repair_order_id.action_validate()
            except Exception:
                pass
        return True

    def action_complete_repair(self):
        """Marque les réparations terminées."""
        self.ensure_one()
        self.write({'state': 'repaired'})
        self.message_post(body=Markup(_("<b>Travaux atelier terminés.</b> Véhicule prêt pour facturation scindée et restitution.")))
        return True

    def action_open_split_invoicing_wizard(self):
        """Ouvre l'assistant de facturation scindée (Compagnie d'assurance + Client)."""
        self.ensure_one()
        if self.state not in ('accord_approved', 'in_repair', 'repaired'):
            raise UserError(_("Le bon d'accord doit être validé avant d'émettre la facturation scindée."))
        if self.client_accord_status != 'approved':
            raise UserError(_("L'accord du client sur le décompte sinistre est obligatoire avant d'émettre la facturation scindée."))
        return {
            'name': _("Facturation Scindée - Sinistre %s", self.claim_number),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.insurance.invoice.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_claim_id': self.id,
            }
        }

    def action_client_approve_expert(self, ip_address="Guichet"):
        """Valide formellement l'avis de l'expert par le client (via portail mobile ou guichet)."""
        self.ensure_one()
        self.write({
            'client_accord_status': 'approved',
            'client_accord_date': fields.Datetime.now(),
            'client_accord_ip': ip_address,
        })
        self.message_post(body=Markup(_(
            "✅ <b>Accord Client Validé sur Avis Expert :</b> Le client %s a approuvé le décompte "
            "(Franchise/Vétusté: <b>%s MAD TTC</b>) le %s (Canal/IP: %s)."
        ) % (
            self.customer_id.name or "Client",
            self.customer_payable,
            fields.Datetime.now().strftime('%d/%m/%Y %H:%M'),
            ip_address
        )))
        if self.reception_id:
            task_2b = self.reception_id.task_ids.filtered(
                lambda t: ("2b" in t.name.lower() or "accord client" in t.name.lower()) and t.state != '1_done'
            )
            for st in task_2b:
                st.with_context(auto_workflow_sync=True).write({
                    'state': '1_done',
                    'is_done': True,
                    'completed_date': fields.Datetime.now(),
                })
            stage_2 = self.env['garage.workshop.stage'].search([('sequence', '=', 20)], limit=1)
            if stage_2:
                self.reception_id._check_and_auto_advance_stage(stage_2)

        # Lancement automatique des travaux atelier dès accord client
        if self.state == 'accord_approved':
            try:
                self.action_start_repair()
            except Exception:
                pass

        return True

    def action_print_franchise_receipt(self):
        """Imprime le reçu officiel de franchise et vétusté."""
        self.ensure_one()
        return self.env.ref('garage_repair_core.action_report_insurance_franchise_receipt').report_action(self)

    def action_view_invoices(self):
        """Affiche les factures scindées émises pour ce dossier sinistre."""
        self.ensure_one()
        invoice_ids = []
        if self.insurance_invoice_id:
            invoice_ids.append(self.insurance_invoice_id.id)
        if self.customer_invoice_id:
            invoice_ids.append(self.customer_invoice_id.id)
        return {
            'name': _("Factures Sinistre %s", self.claim_number),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': [('id', 'in', invoice_ids)],
        }

    def action_print_expert_report(self):
        """Imprime le dossier officiel d'expertise automobile."""
        self.ensure_one()
        return self.env.ref('garage_repair_core.action_report_insurance_claim_expert').report_action(self)

    def action_send_whatsapp_expert(self):
        """Ouvre un lien WhatsApp direct vers l'expert."""
        self.ensure_one()
        if not self.expert_phone:
            raise UserError(_("Veuillez renseigner le numéro de téléphone / WhatsApp de l'expert."))
        phone = normalize_morocco_phone(self.expert_phone)
        text = (
            f"Bonjour Maître / M. {self.expert_name or ''},\n"
            f"Concernant le dossier Sinistre N° *{self.claim_number}* ({self.insurance_id.name})\n"
            f"Véhicule: *{self.vehicle_id.name}* - Immat: *{self.license_plate}*\n"
            f"Le devis d'atelier est prêt et consultable. Merci de nous confirmer votre passage ou accord."
        )
        encoded_text = urllib.parse.quote(text)
        return {
            'type': 'ir.actions.act_url',
            'url': f"https://wa.me/{phone}?text={encoded_text}",
            'target': 'new',
        }

    def action_send_whatsapp_customer(self):
        """Ouvre un lien WhatsApp direct vers le client adapté à l'état du sinistre."""
        self.ensure_one()
        if not self.customer_phone:
            raise UserError(_("Veuillez renseigner le téléphone du client assuré."))
        phone = normalize_morocco_phone(self.customer_phone)
        if self.state in ('repaired', 'invoiced', 'closed'):
            if self.customer_payable > 0:
                text = (
                    f"Bonjour M./Mme {self.customer_id.name},\n"
                    f"Votre véhicule *{self.vehicle_id.name}* ({self.license_plate}) est prêt à l'atelier.\n"
                    f"Dossier Sinistre: {self.claim_number}.\n"
                    f"Reste à régler au retrait (Franchise / Vétusté) : *{self.customer_payable:,.2f} MAD TTC*.\n"
                    f"À votre entière disposition pour la restitution."
                )
            else:
                text = (
                    f"Bonjour M./Mme {self.customer_id.name},\n"
                    f"Votre véhicule *{self.vehicle_id.name}* ({self.license_plate}) est entièrement terminé et prêt pour restitution.\n"
                    f"Dossier Sinistre: {self.claim_number} (Prise en charge intégrale assurance).\n"
                    f"À votre entière disposition pour la restitution."
                )
        else:
            stage_label = dict(self._fields['state'].selection).get(self.state, self.state)
            text = (
                f"Bonjour M./Mme {self.customer_id.name},\n"
                f"Suivi du dossier Sinistre {self.claim_number} - Véhicule *{self.vehicle_id.name}* ({self.license_plate}) :\n"
                f"Statut actuel : *{stage_label}*.\n"
                f"Nous vous tenons immédiatement informé dès validation de l'étape suivante."
            )
        encoded_text = urllib.parse.quote(text)
        return {
            'type': 'ir.actions.act_url',
            'url': f"https://wa.me/{phone}?text={encoded_text}",
            'target': 'new',
        }


class GarageInsuranceAmendment(models.Model):
    _name = 'garage.insurance.amendment'
    _description = "Avenant Sinistre / Pièces Cachées"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'

    claim_id = fields.Many2one('garage.insurance.claim', string="Dossier Sinistre", required=True, ondelete='cascade')
    sequence = fields.Integer(string="Séquence", default=1)
    name = fields.Char(string="Titre de l'Avenant", required=True, tracking=True,
                       help="Ex: Avenant 1 - Berceau moteur plié et condenseur clim percé")
    date_submission = fields.Date(string="Date Soumission", default=fields.Date.context_today, required=True, tracking=True)
    date_response = fields.Date(string="Date Réponse Expert", tracking=True)

    reason = fields.Selection([
        ('hidden_part', 'Dégâts Masqués Découverts au Démontage'),
        ('additional_labor', 'Heures Complémentaires Marbre / Tôlerie'),
        ('price_discrepancy', 'Rectification Tarif Pièce Catalogue'),
        ('other', 'Autre Complément'),
    ], string="Motif de l'Avenant", default='hidden_part', required=True, tracking=True)

    description = fields.Text(string="Constat Technique & Détail des Pièces Cachées", required=True)

    currency_id = fields.Many2one(related='claim_id.currency_id')
    parts_amount_untaxed = fields.Monetary(string="Pièces Complémentaires HT", default=0.0, tracking=True)
    labor_amount_untaxed = fields.Monetary(string="MO Complémentaire HT", default=0.0, tracking=True)
    total_untaxed = fields.Monetary(string="Total Avenant HT", compute='_compute_total', store=True)

    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('submitted', 'Soumis à l\'Expert'),
        ('approved', 'Validé par l\'Expert'),
        ('rejected', 'Rejeté par l\'Expert'),
    ], string="Statut", default='draft', tracking=True)

    expert_notes = fields.Text(string="Remarques / Observations de l'Expert")
    attachment_ids = fields.Many2many(
        'ir.attachment', 'garage_claim_amendment_attachment_rel',
        'amendment_id', 'attachment_id',
        string="Photos Dégâts Découverts"
    )

    @api.depends('parts_amount_untaxed', 'labor_amount_untaxed')
    def _compute_total(self):
        for rec in self:
            rec.total_untaxed = rec.parts_amount_untaxed + rec.labor_amount_untaxed

    def action_submit_to_expert(self):
        self.ensure_one()
        self.write({'state': 'submitted'})
        self.claim_id.message_post(body=Markup(_(
            "Avenant soumis à l'Expert : <b>%s</b> (+%s MAD HT)."
        ) % (self.name, self.total_untaxed)))
        return True

    def action_approve_by_expert(self):
        self.ensure_one()
        self.write({
            'state': 'approved',
            'date_response': fields.Date.context_today(self),
        })
        self.claim_id.message_post(body=Markup(_(
            "Avenant <b>%s</b> validé par l'Expert (+%s MAD HT)."
        ) % (self.name, self.total_untaxed)))
        return True

    def action_reject_by_expert(self):
        self.ensure_one()
        self.write({
            'state': 'rejected',
            'date_response': fields.Date.context_today(self),
        })
        self.claim_id.message_post(body=Markup(_(
            "Avenant <b>%s</b> refusé par l'Expert."
        ) % self.name))
        return True
