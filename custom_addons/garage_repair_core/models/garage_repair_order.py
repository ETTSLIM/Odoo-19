# -*- coding: utf-8 -*-
import uuid
from markupsafe import Markup
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from .whatsapp_gateway import send_garage_whatsapp, normalize_morocco_phone

class RepairOrder(models.Model):
    _inherit = 'repair.order'

    # Liaison Véhicule & Entrée Atelier
    vehicle_id = fields.Many2one('fleet.vehicle', string="Véhicule", required=True, tracking=True)
    license_plate = fields.Char(related='vehicle_id.license_plate', string="Immatriculation", store=True)
    vin_number = fields.Char(related='vehicle_id.vin_number', string="N° Châssis (VIN)", readonly=True)
    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", tracking=True)
    odometer_order = fields.Float(string="Kilométrage Actuel (km)")

    # Client & Informations Fiscales
    customer_type = fields.Selection(related='partner_id.customer_type', string="Type Client", readonly=True)
    customer_cin = fields.Char(related='partner_id.cin', string="CIN Client", readonly=True)
    customer_ice = fields.Char(related='partner_id.ice', string="ICE Société", readonly=True)

    # Portail Client & Validation Devis en 1-Clic
    tracking_token = fields.Char(string="Jeton de Suivi Client", copy=False, readonly=True)
    client_approval_status = fields.Selection([
        ('pending', 'En Attente Accord Client'),
        ('approved', 'Validé par le Client (1-Clic)'),
        ('rejected', 'Refusé / Contesté'),
    ], string="Accord Client Devis", default='pending', tracking=True)
    client_approval_date = fields.Datetime(string="Date Accord Client", readonly=True, tracking=True)
    client_approval_ip = fields.Char(string="IP de Validation", readonly=True)

    # Double Flux : Canal de Dénouement Opérationnel vs Fiscal
    billing_channel = fields.Selection([
        ('bl_internal', 'Bon de Travail / BL Atelier (Règlement direct)'),
        ('official_invoice', 'Facturation Fiscale Officielle (TVA 20% + Déclaré)'),
        ('insurance', 'Dossier Sinistre / Prise en charge Assurance'),
    ], string="Mode de Facturation", default='bl_internal', required=True, tracking=True)
    claim_id = fields.Many2one('garage.insurance.claim', string="Dossier Sinistre", tracking=True)
    is_insurance_claim = fields.Boolean(string="Dossier Sinistre Assuré", compute='_compute_is_insurance_claim', store=True)

    # Canal A : Suivi Bon de Travail & Encaissement Direct
    bl_number = fields.Char(string="N° Bon de Travail", readonly=True, copy=False)
    payment_status = fields.Selection([
        ('unpaid', 'Non Réglé'),
        ('partial', 'Partiellement Réglé'),
        ('paid', 'Totalement Soldé'),
    ], string="Statut Règlement BL", default='unpaid', tracking=True)

    payment_ids = fields.One2many('garage.repair.payment', 'repair_id', string="Historique des Règlements")
    amount_paid = fields.Monetary(string="Montant Encaissé Total", compute='_compute_financial_totals', store=True, readonly=False, tracking=True)
    amount_residual = fields.Monetary(string="Reste à Payer", compute='_compute_financial_totals', store=True)

    # Traçabilité Bancaire & Alerte Fiscale
    has_bank_traceable_payment = fields.Boolean(string="Paiement Bancaire Traçable (TPE/Chèque)", compute='_compute_bank_traceability', store=True)
    bank_traceable_amount = fields.Monetary(string="Total Encaissé Bancaire (TPE/Chèque/Virement)", compute='_compute_bank_traceability', store=True)
    fiscal_compliance_status = fields.Selection([
        ('unpaid', 'Non Encaissé'),
        ('ok_cash', 'Encaissé Espèces (BL Interne)'),
        ('alert_invoice_needed', 'Alerte : Règlement Bancaire Sans Facture Fiscale'),
        ('ok_invoiced', 'Conforme : Facture Fiscale Déclarée'),
    ], string="Conformité Fiscale Bancaire", compute='_compute_bank_traceability', store=True)

    # Canal B : Rapprochement Facture Fiscale Officielle
    official_invoice_id = fields.Many2one('account.move', string="Facture Fiscale Liée", copy=False, readonly=True, tracking=True)
    is_invoiced_officially = fields.Boolean(string="Facturé Officiellement", compute='_compute_is_invoiced', store=True)

    # Lignes d'opérations et de pièces atelier
    garage_parts_lines = fields.One2many('garage.repair.part.line', 'repair_id', string="Pièces Détachées")
    garage_labor_lines = fields.One2many('garage.repair.labor.line', 'repair_id', string="Main-d'Œuvre & Travaux")
    parts_bl_ids = fields.One2many('garage.parts.bl', 'repair_order_id', string="BL Pièces Fournisseurs")
    parts_bl_count = fields.Integer(string="Nb. BL Pièces Fournisseurs", compute='_compute_parts_bl_count')

    # Qualification Fiscale des Pièces
    amount_parts_operational = fields.Monetary(string="Pièces Non Déclarées (Opérationnelles)", compute='_compute_financial_totals', store=True)
    amount_parts_official = fields.Monetary(string="Pièces Déclarées (Officielles)", compute='_compute_financial_totals', store=True)
    has_operational_parts = fields.Boolean(string="A des pièces opérationnelles à substituer", compute='_compute_financial_totals', store=True)

    # Totaux Chiffrés (Ventes)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    amount_parts_untaxed = fields.Monetary(string="Total Pièces HT", compute='_compute_financial_totals', store=True)
    amount_labor_untaxed = fields.Monetary(string="Total MO HT", compute='_compute_financial_totals', store=True)
    amount_untaxed_total = fields.Monetary(string="Total Général HT", compute='_compute_financial_totals', store=True)
    amount_tax_total = fields.Monetary(string="TVA (20%)", compute='_compute_financial_totals', store=True)
    amount_total_ttc = fields.Monetary(string="Total TTC", compute='_compute_financial_totals', store=True)

    # Rentabilité Réelle Atelier (Coûts d'achat réels et marges)
    total_parts_cost = fields.Monetary(string="Coût Achat Pièces", compute='_compute_profitability', store=True)
    total_labor_cost = fields.Monetary(string="Coût Interne MO", compute='_compute_profitability', store=True)
    total_real_cost = fields.Monetary(string="Coût de Revient Réel", compute='_compute_profitability', store=True)
    real_gross_margin = fields.Monetary(string="Marge Brute Réelle", compute='_compute_profitability', store=True)
    real_margin_rate = fields.Float(string="Taux de Marge (%)", compute='_compute_profitability', store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('tracking_token'):
                # Hérite du jeton de la réception si lié, sinon en génère un nouveau
                if vals.get('reception_id'):
                    reception = self.env['garage.reception'].browse(vals['reception_id'])
                    vals['tracking_token'] = reception.tracking_token or uuid.uuid4().hex[:12]
                else:
                    vals['tracking_token'] = uuid.uuid4().hex[:12]
        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        if ('garage_parts_lines' in vals or 'garage_labor_lines' in vals) and not self.env.context.get('skip_devis_sync'):
            for order in self:
                if order.amount_untaxed_total > 0 and order.reception_id and order.reception_id.stock_status == 'envoye_stock':
                    try:
                        order.reception_id.with_context(skip_devis_sync=True).action_mark_devis_ready()
                    except Exception:
                        pass
        return res

    @api.depends('official_invoice_id')
    def _compute_is_invoiced(self):
        for order in self:
            order.is_invoiced_officially = bool(order.official_invoice_id)

    @api.depends('claim_id')
    def _compute_is_insurance_claim(self):
        for order in self:
            order.is_insurance_claim = bool(order.claim_id)

    @api.depends(
        'garage_parts_lines.subtotal',
        'garage_parts_lines.source_type',
        'garage_labor_lines.subtotal',
        'payment_ids.amount',
        'billing_channel',
        'official_invoice_id',
        'official_invoice_id.amount_untaxed',
        'official_invoice_id.amount_tax',
        'official_invoice_id.amount_total',
    )
    def _compute_financial_totals(self):
        for order in self:
            parts_total = sum(order.garage_parts_lines.mapped('subtotal'))
            labor_total = sum(order.garage_labor_lines.mapped('subtotal'))
            untaxed = parts_total + labor_total
            tax = untaxed * 0.20
            total_ttc = untaxed + tax

            # Découpage Opérationnel vs Fiscal des pièces
            op_parts = sum(order.garage_parts_lines.filtered(lambda l: l.source_type == 'operational').mapped('subtotal'))
            off_parts = sum(order.garage_parts_lines.filtered(lambda l: l.source_type == 'official').mapped('subtotal'))

            order.amount_parts_operational = op_parts
            order.amount_parts_official = off_parts
            order.has_operational_parts = op_parts > 0

            order.amount_parts_untaxed = parts_total
            order.amount_labor_untaxed = labor_total

            if order.billing_channel == 'official_invoice' and order.official_invoice_id:
                order.amount_untaxed_total = order.official_invoice_id.amount_untaxed
                order.amount_tax_total = order.official_invoice_id.amount_tax
                order.amount_total_ttc = order.official_invoice_id.amount_total
                target_amount = order.official_invoice_id.amount_total
            else:
                order.amount_untaxed_total = untaxed
                order.amount_tax_total = tax
                order.amount_total_ttc = total_ttc
                target_amount = total_ttc if order.billing_channel == 'official_invoice' else untaxed

            # Calcul du montant encaissé depuis les lignes de paiement si existantes
            if order.payment_ids:
                order.amount_paid = sum(order.payment_ids.mapped('amount'))

            order.amount_residual = max(0.0, target_amount - order.amount_paid)

            if order.amount_paid <= 0:
                order.payment_status = 'unpaid'
            elif order.amount_residual <= 0.01:
                order.payment_status = 'paid'
            else:
                order.payment_status = 'partial'

    @api.depends('payment_ids.amount', 'payment_ids.payment_method', 'official_invoice_id', 'payment_status')
    def _compute_bank_traceability(self):
        for order in self:
            traceable_payments = order.payment_ids.filtered(lambda p: p.payment_method in ('tpe', 'cheque', 'transfer'))
            order.has_bank_traceable_payment = bool(traceable_payments)
            order.bank_traceable_amount = sum(traceable_payments.mapped('amount'))

            if order.official_invoice_id:
                order.fiscal_compliance_status = 'ok_invoiced'
            elif order.has_bank_traceable_payment:
                order.fiscal_compliance_status = 'alert_invoice_needed'
            elif order.payment_status in ('paid', 'partial'):
                order.fiscal_compliance_status = 'ok_cash'
            else:
                order.fiscal_compliance_status = 'unpaid'

    @api.depends('garage_parts_lines.total_cost', 'garage_labor_lines.total_cost', 'amount_untaxed_total')
    def _compute_profitability(self):
        for order in self:
            parts_cost = sum(order.garage_parts_lines.mapped('total_cost'))
            labor_cost = sum(order.garage_labor_lines.mapped('total_cost'))
            total_cost = parts_cost + labor_cost
            margin = order.amount_untaxed_total - total_cost

            order.total_parts_cost = parts_cost
            order.total_labor_cost = labor_cost
            order.total_real_cost = total_cost
            order.real_gross_margin = margin
            order.real_margin_rate = (margin / order.amount_untaxed_total * 100) if order.amount_untaxed_total > 0 else 0.0

    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_garage(self):
        if self.vehicle_id:
            if self.vehicle_id.customer_id:
                self.partner_id = self.vehicle_id.customer_id
            if self.vehicle_id.odometer:
                self.odometer_order = self.vehicle_id.odometer

    def _get_tracking_url(self):
        self.ensure_one()
        token = self.tracking_token
        if not token and self.reception_id:
            token = self.reception_id.tracking_token
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url', 'http://localhost:8069')
        return f"{base_url.rstrip('/')}/garage/tracking/{token}"

    def action_send_whatsapp_quote(self):
        """Envoie le devis chiffré par WhatsApp avec bouton de validation 1-clic."""
        self.ensure_one()
        phone = self.partner_id.phone
        if not phone:
            raise UserError(_("Le client n'a aucun numéro de téléphone renseigné."))

        tracking_url = self._get_tracking_url()
        client_name = self.partner_id.name or "Client"
        plate = self.license_plate or "votre véhicule"
        total = self.amount_untaxed_total

        msg = (
            f"Bonjour {client_name},\n\n"
            f"Le devis pour la réparation de votre véhicule *{plate}* est prêt : *{total:,.2f} MAD*.\n\n"
            f"Consultez le détail des pièces et validez les travaux en 1 clic sur votre lien sécurisé :\n"
            f"{tracking_url}\n\n"
            f"Notre atelier débutera l'intervention dès votre validation."
        )

        # Auto-synchronisation devis chiffré sur la fiche réception
        if self.reception_id and self.reception_id.stock_status == 'envoye_stock':
            self.reception_id.action_mark_devis_ready()

        success, info, wa_link = send_garage_whatsapp(self.env, phone, msg)
        self.message_post(body=Markup(_("<b>Devis transmis par WhatsApp :</b> %s<br/>Lien de validation : <a href='%s' target='_blank'>Portail de Suivi Client</a>") % (info, tracking_url)))

        if wa_link and ("wa.me" in wa_link or "whatsapp.com" in wa_link):
            return {'type': 'ir.actions.act_url', 'url': wa_link, 'target': 'new'}

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Devis Transmis par WhatsApp"),
                'message': _("Devis envoyé avec succès à %s", phone),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_open_tracking_portal(self):
        """Ouvre le portail client dans un nouvel onglet."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': self._get_tracking_url(),
            'target': 'new',
        }

    def action_client_approve(self, ip_address=""):
        """Exécuté lorsque le client clique sur 'Valider & Autoriser les Travaux' depuis le portail."""
        self.ensure_one()
        self.write({
            'client_approval_status': 'approved',
            'client_approval_date': fields.Datetime.now(),
            'client_approval_ip': ip_address,
        })
        if self.state in ('draft', 'confirmed'):
            self.action_repair_start()

        if self.reception_id:
            # Synchronisation automatique des micro-tâches 2B (Accord Client) et 2D (Devis Complémentaire)
            subtasks_2b_2d = self.reception_id.task_ids.filtered(
                lambda t: ("2b" in t.name.lower() or "accord client" in t.name.lower() or
                           "2d" in t.name.lower() or "complémentaire" in t.name.lower()) and t.state != '1_done'
            )
            for st in subtasks_2b_2d:
                st.with_context(auto_workflow_sync=True).write({
                    'state': '1_done',
                    'is_done': True,
                    'completed_date': fields.Datetime.now(),
                })
            stage_2 = self.env['garage.workshop.stage'].search([('sequence', '=', 20)], limit=1)
            if stage_2:
                self.reception_id._check_and_auto_advance_stage(stage_2)
            elif self.reception_id.state in ('draft', 'diagnostic', 'quoted'):
                self.reception_id.write({'state': 'in_repair'})

        self.message_post(body=Markup(_(
            "<b>Accord Client Validé (1-Clic WhatsApp) :</b> Le client %s a validé les travaux pour un montant de <b>%s MAD HT</b> (%s MAD TTC). (IP: %s)"
        ) % (self.partner_id.name, f"{self.amount_untaxed_total:,.2f}", f"{self.amount_total_ttc:,.2f}", ip_address)))

    def action_repair_end(self):
        """Termine la réparation et synchronise l'avancement vers l'Étape 6 (Prêt) et le sinistre."""
        res = super().action_repair_end()
        for order in self:
            if order.reception_id and order.reception_id.stage_sequence < 60:
                stage_ready = self.env['garage.workshop.stage'].search([('sequence', '=', 60)], limit=1)
                if stage_ready:
                    order.reception_id.write({'stage_id': stage_ready.id})
            if order.claim_id and order.claim_id.state == 'in_repair':
                order.claim_id.action_complete_repair()
        return res

    @api.depends('parts_bl_ids')
    def _compute_parts_bl_count(self):
        for order in self:
            order.parts_bl_count = len(order.parts_bl_ids)

    def action_view_parts_bl(self):
        """Affiche les bons de réception pièces fournisseurs liés."""
        self.ensure_one()
        return {
            'name': _("Bons de Réception Pièces - %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.parts.bl',
            'view_mode': 'list,form',
            'domain': [('repair_order_id', '=', self.id)],
            'context': {'default_repair_order_id': self.id, 'default_vehicle_id': self.vehicle_id.id},
        }

    def action_view_reception(self):
        """Ouvre la fiche de réception atelier liée."""
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

    def action_generate_bl(self):
        """Génère la référence du Bon de Travail / BL Atelier si non existante et permet l'impression."""
        for order in self:
            if not order.bl_number:
                order.bl_number = self.env['ir.sequence'].next_by_code('garage.work.order.bl') or _('BL-PROV')
        return self.env.ref('garage_repair_core.action_report_work_order_bl').report_action(self)

    def action_open_billing_wizard(self):
        """Ouvre l'assistant pour convertir le Bon de Travail en Facture Fiscale avec moteur d'équivalence."""
        self.ensure_one()
        return {
            'name': _("Conversion Fiscale & Moteur d'Équivalence de Valeur"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.billing.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_repair_order_id': self.id,
                'default_partner_id': self.partner_id.id,
            }
        }

    def action_view_claim(self):
        """Ouvre ou crée le dossier sinistre lié à cet ordre de réparation."""
        self.ensure_one()
        if not self.claim_id:
            # Recherche une compagnie d'assurance par défaut
            default_insurance = self.env['res.partner'].search([('is_insurance_company', '=', True)], limit=1)
            claim = self.env['garage.insurance.claim'].create({
                'claim_number': _("SIN-%s") % (self.name or "NOUVEAU"),
                'vehicle_id': self.vehicle_id.id,
                'customer_id': self.partner_id.id,
                'insurance_id': default_insurance.id if default_insurance else False,
                'reception_id': self.reception_id.id if self.reception_id else False,
                'repair_order_id': self.id,
                'initial_estimate_parts': sum(self.garage_parts_lines.mapped('subtotal')),
                'initial_estimate_labor': sum(self.garage_labor_lines.mapped('subtotal')),
            })
            self.claim_id = claim.id
            self.billing_channel = 'insurance'
        return {
            'name': _("Dossier Sinistre %s", self.claim_id.claim_number),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.insurance.claim',
            'res_id': self.claim_id.id,
            'view_mode': 'form',
        }

    def action_open_payment_recovery_wizard(self):
        """Ouvre l'assistant d'encaissement au comptoir avec détection immédiate TPE/Chèque."""
        self.ensure_one()
        return {
            'name': _("Guichet d'Encaissement & Dénouement Règlement"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.payment.recovery.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_repair_order_id': self.id,
                'default_partner_id': self.partner_id.id,
                'default_payment_amount': self.amount_residual or self.amount_untaxed_total,
            }
        }

    def action_open_stock_picker_wizard(self):
        """Ouvre l'assistant de prélèvement de pièces dans le stock magasin central."""
        self.ensure_one()
        return {
            'name': _("Piocher du Stock Magasin"),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.stock.picker.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_repair_order_id': self.id,
            }
        }


class GarageRepairPartLine(models.Model):
    _name = 'garage.repair.part.line'
    _description = "Ligne de Pièce Détachée Atelier"

    repair_id = fields.Many2one('repair.order', string="Ordre de Réparation", ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string="Article / Réf Magasin")
    name = fields.Char(string="Désignation Pièce", required=True)
    qty = fields.Float(string="Qté", default=1.0)
    currency_id = fields.Many2one(related='repair_id.currency_id')

    # Qualification Fiscale du Stock
    source_type = fields.Selection([
        ('operational', 'Stock Opérationnel (BL Comptoir / Non déclaré)'),
        ('official', 'Stock Fiscal Déclaré (Facture Fournisseur ICE)'),
    ], string="Origine Fiscale Stock", default='operational', required=True)

    # Double tarification : Coût réel achat vs Prix de vente
    cost_price = fields.Monetary(string="Prix d'Achat (Coût)", required=True, default=0.0)
    sale_price = fields.Monetary(string="Prix de Vente Unitaire", required=True, default=0.0)
    
    subtotal = fields.Monetary(string="Sous-total Vente", compute='_compute_totals', store=True)
    total_cost = fields.Monetary(string="Sous-total Coût", compute='_compute_totals', store=True)
    margin = fields.Monetary(string="Marge Pièce", compute='_compute_totals', store=True)

    parts_bl_line_id = fields.Many2one('garage.parts.bl.line', string="Ligne BL Achat d'origine")

    # Anti-Double Emploi & Sortie Fiscale
    is_officially_cleared = fields.Boolean(string="Sortie Fiscale Effectuée", default=False, readonly=True,
                                           help="Indique que cette pièce a été consommée légalement sur une facture fiscale")
    official_invoice_id = fields.Many2one('account.move', string="Facture Fiscale de Dénouement", readonly=True)
    stock_move_id = fields.Many2one('stock.move', string="Mouvement Sortie Stock Fiscal", readonly=True)

    @api.depends('qty', 'sale_price', 'cost_price')
    def _compute_totals(self):
        for line in self:
            subtotal = line.qty * line.sale_price
            cost = line.qty * line.cost_price
            line.subtotal = subtotal
            line.total_cost = cost
            line.margin = subtotal - cost

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.name = self.product_id.display_name
            self.cost_price = self.product_id.standard_price
            self.sale_price = self.product_id.list_price

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._ensure_outgoing_stock_move()
        return records

    def _ensure_outgoing_stock_move(self):
        """Génère le mouvement réel de sortie de stock (Opérationnel ou Fiscal) lors de l'affectation atelier."""
        cust_loc = self.env.ref('stock.stock_location_customers', raise_if_not_found=False)
        if not cust_loc:
            cust_loc = self.env['stock.location'].search([('usage', '=', 'customer')], limit=1)
        if not cust_loc:
            return

        loc_op = self.env.ref('garage_repair_core.location_stock_operational', raise_if_not_found=False)
        loc_of = self.env.ref('garage_repair_core.location_stock_official', raise_if_not_found=False)

        for line in self:
            if line.stock_move_id or line.qty <= 0:
                continue
            prod = line.product_id or (line.parts_bl_line_id.product_id if line.parts_bl_line_id else False)
            if not prod:
                continue
            if not line.product_id:
                line.product_id = prod.id

            src_loc = loc_of if line.source_type == 'official' else loc_op
            if not src_loc:
                continue

            # Vérifier si la pièce provient d'un BL de stock ou si le stock physique existe
            quants = self.env['stock.quant'].search([
                ('product_id', '=', prod.id),
                ('location_id', 'child_of', src_loc.id),
            ])
            available_quant = sum(quants.mapped('quantity'))
            if line.parts_bl_line_id or available_quant >= line.qty:
                move = self.env['stock.move'].create({
                    'product_id': prod.id,
                    'product_uom': prod.uom_id.id,
                    'product_uom_qty': line.qty,
                    'location_id': src_loc.id,
                    'location_dest_id': cust_loc.id,
                    'price_unit': line.sale_price,
                })
                move._action_confirm()
                move._action_assign()
                move.quantity = line.qty
                move.picked = True
                move._action_done()
                line.stock_move_id = move.id

    def unlink(self):
        """Restitue le stock physique en rayon si une ligne de pièce non facturée est retirée de l'OR."""
        for line in self:
            if line.stock_move_id and line.stock_move_id.state == 'done' and not line.is_officially_cleared:
                old_move = line.stock_move_id
                ret_move = self.env['stock.move'].create({
                    'product_id': old_move.product_id.id,
                    'product_uom': old_move.product_uom.id,
                    'product_uom_qty': line.qty,
                    'location_id': old_move.location_dest_id.id,
                    'location_dest_id': old_move.location_id.id,
                    'price_unit': line.cost_price,
                })
                ret_move._action_confirm()
                ret_move._action_assign()
                ret_move.quantity = line.qty
                ret_move.picked = True
                ret_move._action_done()
        return super().unlink()


class GarageRepairLaborLine(models.Model):
    _name = 'garage.repair.labor.line'
    _description = "Ligne de Main-d'Œuvre et Opérations"

    repair_id = fields.Many2one('repair.order', string="Ordre de Réparation", ondelete='cascade', required=True)
    name = fields.Char(string="Description Travaux", required=True)
    work_type = fields.Selection([
        ('mechanic', 'Mécanique Générale'),
        ('bodywork', 'Tôlerie & Carrosserie'),
        ('paint', 'Peinture & Finition'),
        ('electric', 'Électricité & Diagnostic Électronique'),
        ('service', 'Vidange & Entretien Rapide'),
    ], string="Type d'Intervention", default='mechanic', required=True)

    mechanic_id = fields.Many2one('res.users', string="Intervenant / Mécanicien")
    hours = fields.Float(string="Heures", default=1.0)
    currency_id = fields.Many2one(related='repair_id.currency_id')

    hourly_cost = fields.Monetary(string="Coût Horaire Interne", default=50.0)
    hourly_rate = fields.Monetary(string="Taux Horaire Vente", default=150.0)

    subtotal = fields.Monetary(string="Sous-total Vente", compute='_compute_labor_totals', store=True)
    total_cost = fields.Monetary(string="Coût Revient", compute='_compute_labor_totals', store=True)
    margin = fields.Monetary(string="Marge MO", compute='_compute_labor_totals', store=True)

    @api.depends('hours', 'hourly_rate', 'hourly_cost')
    def _compute_labor_totals(self):
        for line in self:
            subtotal = line.hours * line.hourly_rate
            cost = line.hours * line.hourly_cost
            line.subtotal = subtotal
            line.total_cost = cost
            line.margin = subtotal - cost


class GarageRepairPayment(models.Model):
    _name = 'garage.repair.payment'
    _description = "Règlement / Encaissement Réparation"
    _order = 'payment_date desc, id desc'

    repair_id = fields.Many2one('repair.order', string="Ordre de Réparation", required=True, ondelete='cascade')
    partner_id = fields.Many2one(related='repair_id.partner_id', string="Client", readonly=True)
    currency_id = fields.Many2one(related='repair_id.currency_id')
    payment_date = fields.Datetime(string="Date d'Encaissement", default=fields.Datetime.now, required=True)
    amount = fields.Monetary(string="Montant Encaissé", required=True)
    payment_method = fields.Selection([
        ('cash', 'Espèces (Caisse Atelier)'),
        ('tpe', 'TPE / Carte Bancaire (Traçable)'),
        ('cheque', 'Chèque Bancaire (Traçable)'),
        ('transfer', 'Virement Bancaire (Traçable)'),
        ('insurance', 'Prise en Charge Assurance'),
    ], string="Mode d'Encaissement", required=True, default='cash')
    transaction_ref = fields.Char(string="N° Transaction TPE / N° Chèque / Réf Virement")
    bank_name = fields.Char(string="Banque Émettrice")
    cashier_id = fields.Many2one('res.users', string="Encaissé par", default=lambda self: self.env.user, required=True)
    is_bank_traceable = fields.Boolean(string="Traçable sur Compte Bancaire", compute='_compute_is_bank_traceable', store=True)
    notes = fields.Text(string="Remarques / Observations")
    official_invoice_id = fields.Many2one(related='repair_id.official_invoice_id', string="Facture Fiscale Liée", readonly=True)

    @api.depends('payment_method')
    def _compute_is_bank_traceable(self):
        for rec in self:
            rec.is_bank_traceable = rec.payment_method in ('tpe', 'cheque', 'transfer')
