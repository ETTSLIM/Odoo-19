# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request

class GarageTrackingController(http.Controller):

    @http.route('/garage/tracking/<string:token>', type='http', auth='public', website=False, sitemap=False)
    def garage_tracking_portal(self, token, **kwargs):
        """Affiche le portail de suivi en temps réel du véhicule sans authentification (Lien magique)."""
        reception = request.env['garage.reception'].sudo().search([('tracking_token', '=', token)], limit=1)
        repair_order = request.env['repair.order'].sudo().search([('tracking_token', '=', token)], limit=1)
        claim = request.env['garage.insurance.claim'].sudo().search([('tracking_token', '=', token)], limit=1)

        # Rapprochement croisé si lié
        if claim and not repair_order and claim.repair_order_id:
            repair_order = claim.repair_order_id
        if claim and not reception and claim.reception_id:
            reception = claim.reception_id
        if repair_order and not claim and repair_order.claim_id:
            claim = repair_order.claim_id

        if reception and not repair_order and reception.repair_order_id:
            repair_order = reception.repair_order_id
        elif repair_order and not reception and repair_order.reception_id:
            reception = repair_order.reception_id

        if not reception and not repair_order and not claim:
            return request.render('garage_repair_core.portal_tracking_not_found', {})

        vehicle = (repair_order and repair_order.vehicle_id) or (claim and claim.vehicle_id) or (reception and reception.vehicle_id)
        partner = (repair_order and repair_order.partner_id) or (claim and claim.customer_id) or (reception and reception.customer_id)

        # Calcul de l'étape courante (1 à 7) basée sur le nouveau workflow 7 Étapes
        if reception and reception.stage_id:
            current_step = max(1, min(7, reception.stage_sequence // 10))
            current_stage_name = reception.stage_id.name
        else:
            state_to_step = {
                'draft': 1,
                'diagnostic': 1,
                'quoted': 2,
                'confirmed': 2,
                'in_repair': 4,
                'under_repair': 4,
                'qc': 5,
                'ready': 6,
                'done': 7,
                'delivered': 7,
            }
            current_state = (repair_order and repair_order.state) or (reception and reception.state) or 'draft'
            current_step = state_to_step.get(current_state, 1)
            current_stage_name = "En Atelier"

        # Tâches client-safe (nom, statut, étape)
        customer_tasks = []
        if reception and reception.task_ids:
            for t in reception.task_ids:
                customer_tasks.append({
                    'name': t.name,
                    'is_done': t.is_done,
                    'stage_step': max(1, min(7, t.stage_sequence // 10)),
                })

        # Possibilité pour le client de valider le devis en 1 clic
        can_approve = False
        if repair_order and repair_order.client_approval_status == 'pending':
            if repair_order.amount_untaxed_total > 0 and repair_order.state in ('draft', 'confirmed'):
                can_approve = True

        # Possibilité pour le client de valider l'avis de l'expert en 1 clic
        can_approve_expert = False
        if claim and claim.state == 'accord_approved' and claim.client_accord_status == 'pending':
            can_approve_expert = True

        values = {
            'token': token,
            'reception': reception,
            'repair_order': repair_order,
            'claim': claim,
            'vehicle': vehicle,
            'partner': partner,
            'current_step': current_step,
            'current_stage_name': current_stage_name,
            'checklist_progress': round(reception.checklist_progress, 1) if reception else 0.0,
            'customer_tasks': customer_tasks,
            'can_approve': can_approve,
            'can_approve_expert': can_approve_expert,
            'company': request.env.company,
        }

        return request.render('garage_repair_core.portal_tracking_page', values)

    @http.route('/garage/tracking/<string:token>/approve', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def garage_tracking_approve(self, token, **kwargs):
        """API appelée en 1 clic par le client sur son smartphone pour valider le devis."""
        repair_order = request.env['repair.order'].sudo().search([('tracking_token', '=', token)], limit=1)
        if not repair_order:
            reception = request.env['garage.reception'].sudo().search([('tracking_token', '=', token)], limit=1)
            if reception and reception.repair_order_id:
                repair_order = reception.repair_order_id

        if not repair_order:
            return {'success': False, 'error': 'Dossier introuvable.'}

        ip_addr = request.httprequest.remote_addr or 'Inconnue'
        repair_order.action_client_approve(ip_address=ip_addr)

        return {
            'success': True,
            'message': 'Votre accord a bien été transmis à l\'atelier. Les travaux démarrent immédiatement !',
            'amount_total_ttc': repair_order.amount_total_ttc,
        }

    @http.route('/garage/tracking/<string:token>/approve_expert', type='jsonrpc', auth='public', methods=['POST'], csrf=False)
    def garage_tracking_approve_expert(self, token, **kwargs):
        """API appelée en 1 clic par le client sur son smartphone pour valider l'avis de l'expert."""
        claim = request.env['garage.insurance.claim'].sudo().search([('tracking_token', '=', token)], limit=1)
        if not claim:
            repair_order = request.env['repair.order'].sudo().search([('tracking_token', '=', token)], limit=1)
            if repair_order and repair_order.claim_id:
                claim = repair_order.claim_id

        if not claim:
            return {'success': False, 'error': 'Dossier sinistre introuvable.'}

        ip_addr = request.httprequest.remote_addr or 'Inconnue'
        claim.action_client_approve_expert(ip_address=f"Mobile ({ip_addr})")

        return {
            'success': True,
            'message': 'Votre accord sur l\'avis de l\'expert a été enregistré avec succès. Les réparations atelier sont autorisées !',
            'customer_payable': claim.customer_payable,
        }
