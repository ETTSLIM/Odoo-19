# -*- coding: utf-8 -*-
import json
import base64
import logging
from odoo import http, fields, Command, _
from odoo.http import request

_logger = logging.getLogger(__name__)

CORS_HEADERS = {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type, Authorization, X-Requested-With',
}


def _json_response(data, status=200):
    """Helper pour retourner une réponse HTTP JSON avec en-têtes CORS."""
    return request.make_response(
        json.dumps(data, ensure_ascii=False, default=str),
        headers=CORS_HEADERS,
        status=status,
    )


def _reception_to_subtasks(r):
    subtasks_list = []
    for t in r.task_ids.sorted(lambda s: (s.sequence, s.id)):
        subtasks_list.append({
            'id': t.id,
            'name': t.name or '',
            'stage_name': t.stage_id.name or '',
            'stage_seq': (t.stage_sequence // 10) if t.stage_sequence else 1,
            'state': t.state or ('1_done' if t.is_done else '04_waiting_normal'),
            'allocated_hours': float(t.planned_hours or 0.5),
            'sequence': t.sequence or 10,
        })
    return subtasks_list


def _reception_to_vehicle_card(r):
    subtasks = _reception_to_subtasks(r)
    active_sub = next((s['name'] for s in subtasks if s['state'] == '01_in_progress'), "")
    if not active_sub:
        active_sub = next((s['name'] for s in subtasks if s['state'] != '1_done'), "")

    images = [f"/web/image/{att.id}" for att in r.attachment_ids]

    vin = ""
    if r.vehicle_id:
        if hasattr(r.vehicle_id, 'vin_sn') and r.vehicle_id.vin_sn:
            vin = r.vehicle_id.vin_sn
        elif hasattr(r.vehicle_id, 'vin_number') and r.vehicle_id.vin_number:
            vin = r.vehicle_id.vin_number

    return {
        'id': r.id,
        'name': r.name or '',
        'immatriculation': r.license_plate or '',
        'brand_model': r.vehicle_id.name if r.vehicle_id else 'Véhicule Atelier',
        'vin': vin,
        'customer_name': r.customer_id.name if r.customer_id else '',
        'stage_id': r.stage_id.id if r.stage_id else 0,
        'stage_name': r.stage_id.name if r.stage_id else '',
        'stage_seq': (r.stage_sequence // 10) if r.stage_sequence else 1,
        'workshop_tag': r.specialty or 'mecanique',
        'subtasks_done': r.checklist_done_count,
        'subtasks_total': r.checklist_total_count,
        'progress_pct': int(round(r.checklist_progress)),
        'active_subtask': active_sub,
        'stock_status': r.stock_status or 'attente_diag',
        'diagnostic_note': r.diagnostic_parts_note or r.symptoms or '',
        'is_assurance': bool(r.is_assurance or r.claim_id),
        'statut_expertise': r.statut_expertise or (r.claim_id.state if r.claim_id else ''),
        'deadline': r.estimated_completion_date.strftime('%Y-%m-%d %H:%M') if r.estimated_completion_date else '',
        'images': images,
        'subtasks': subtasks,
    }


def _reception_to_vehicle_detail(r):
    card = _reception_to_vehicle_card(r)
    card['customer_phone'] = r.customer_phone or (r.customer_id.phone if r.customer_id else '')
    card['compagnie_assurance'] = r.claim_id.insurance_id.name if r.claim_id and r.claim_id.insurance_id else ''
    card['num_sinistre'] = r.claim_id.claim_number if r.claim_id else ''
    card['expert_name'] = r.claim_id.expert_id.name if r.claim_id and r.claim_id.expert_id else ''
    return card


class GarageWorkshopTabletApiController(http.Controller):

    # =========================================================================
    # 1. COMPATIBILITÉ JSON-RPC EXISTANTE
    # =========================================================================

    @http.route('/garage/api/workshop/overview', type='jsonrpc', auth='user', methods=['POST'])
    def get_workshop_overview(self, **kwargs):
        """Fournit la liste complète des étapes et des véhicules actifs à l'atelier pour la tablette."""
        stages = request.env['garage.workshop.stage'].sudo().search([], order='sequence, id')
        receptions = request.env['garage.reception'].sudo().search(
            [('state', 'not in', ('delivered', 'cancel'))],
            order='stage_sequence asc, date_reception desc'
        )

        stages_data = [{
            'id': s.id,
            'name': s.name,
            'sequence': s.sequence,
            'code': s.code,
            'responsible_role': s.responsible_role,
        } for s in stages]

        vehicles_data = []
        for r in receptions:
            tasks_data = [{
                'id': t.id,
                'name': t.name,
                'stage_id': t.stage_id.id,
                'planned_hours': t.planned_hours,
                'state': t.state,
                'is_done': t.is_done,
                'operator_name': t.completed_by_operator_id.name if t.completed_by_operator_id else False,
            } for t in r.task_ids]

            vehicles_data.append({
                'id': r.id,
                'name': r.name,
                'plate': r.license_plate or '',
                'vehicle_name': r.vehicle_id.name if r.vehicle_id else '',
                'customer_name': r.customer_id.name if r.customer_id else '',
                'specialty': r.specialty,
                'stage_id': r.stage_id.id if r.stage_id else False,
                'stage_name': r.stage_id.name if r.stage_id else '',
                'stage_sequence': r.stage_sequence,
                'stock_status': r.stock_status,
                'checklist_progress': round(r.checklist_progress, 1),
                'checklist_done_count': r.checklist_done_count,
                'checklist_total_count': r.checklist_total_count,
                'current_operator': r.current_operator_id.name if r.current_operator_id else False,
                'is_assurance': bool(r.is_assurance or r.claim_id),
                'claim_status': r.claim_id.state if r.claim_id else False,
                'tasks': tasks_data,
            })

        return {
            'success': True,
            'stages': stages_data,
            'vehicles': vehicles_data,
        }

    @http.route('/garage/api/workshop/pin_action', type='jsonrpc', auth='user', methods=['POST'])
    def execute_pin_action(self, pin_code, reception_id, action_type, **kwargs):
        """Valide une action sur tablette via code PIN opérateur."""
        pin = str(pin_code or '').strip()
        if not pin or len(pin) != 4 or not pin.isdigit():
            return {'success': False, 'error': "Code PIN invalide (4 chiffres requis)."}

        operator = request.env['garage.workshop.operator'].sudo().search(
            [('pin_code', '=', pin), ('active', '=', True)], limit=1
        )
        if not operator:
            return {'success': False, 'error': "Code PIN non reconnu."}

        rec = request.env['garage.reception'].sudo().browse(reception_id)
        if not rec.exists():
            return {'success': False, 'error': "Fiche réception introuvable."}

        rec.current_operator_id = operator.id

        if action_type == 'toggle_task':
            task_id = kwargs.get('task_id')
            task = request.env['garage.reception.task'].sudo().browse(task_id)
            if not task.exists() or task.reception_id.id != rec.id:
                return {'success': False, 'error': "Tâche introuvable."}
            task.action_toggle_state(operator=operator)
            return {'success': True, 'task_is_done': task.is_done, 'task_state': task.state, 'operator_name': operator.name}

        elif action_type == 'complete_stage':
            stage_tasks = rec.task_ids.filtered(lambda t: t.stage_id == rec.stage_id and t.state != '1_done')
            for t in stage_tasks:
                t.with_context(auto_workflow_sync=True).write({
                    'state': '1_done',
                    'is_done': True,
                    'completed_by_operator_id': operator.id,
                    'completed_date': fields.Datetime.now(),
                })
            rec._check_and_auto_advance_stage(rec.stage_id, operator=operator)
            return {'success': True, 'message': f"Opérations validées par {operator.name}."}

        elif action_type == 'send_diagnostic_note':
            note = kwargs.get('diagnostic_note', '')
            if note:
                rec.diagnostic_parts_note = note
            rec.action_send_note_to_stock()
            return {'success': True, 'message': f"Note transmise au stock par {operator.name}."}

        elif action_type == 'advance_stage':
            next_stage = request.env['garage.workshop.stage'].sudo().search(
                [('sequence', '>', rec.stage_id.sequence)], order='sequence, id', limit=1
            )
            if next_stage:
                rec.write({'stage_id': next_stage.id})
                return {'success': True, 'new_stage': next_stage.name}
            return {'success': False, 'error': "Dernière étape déjà atteinte."}

        return {'success': False, 'error': "Action non reconnue."}

    # =========================================================================
    # 2. REST HTTP JSON API (COMPATIBILITÉ ANDROID WorkshopApiClient.kt)
    # =========================================================================

    @http.route('/api/workshop/tasks', type='http', auth='none', methods=['GET', 'OPTIONS'], csrf=False)
    def api_get_workshop_tasks(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        stages = request.env['garage.workshop.stage'].sudo().search([], order='sequence, id')
        receptions = request.env['garage.reception'].sudo().search(
            [('state', 'not in', ('delivered', 'cancel'))],
            order='stage_sequence asc, date_reception desc'
        )

        stages_list = []
        for s in stages:
            count = len(receptions.filtered(lambda r: r.stage_id == s))
            stages_list.append({
                'id': s.id,
                'seq': (s.sequence // 10) if s.sequence else 1,
                'name': s.name,
                'vehicle_count': count,
            })

        tasks_list = [_reception_to_vehicle_card(r) for r in receptions]

        return _json_response({
            'stages': stages_list,
            'tasks': tasks_list,
        })

    @http.route('/api/workshop/task/<int:task_id>', type='http', auth='none', methods=['GET', 'OPTIONS'], csrf=False)
    def api_get_vehicle_detail(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'error': f"Vehicle task #{task_id} not found"}, status=404)

        return _json_response(_reception_to_vehicle_detail(rec))

    @http.route('/api/workshop/task/<int:task_id>/subtask/<int:subtask_id>/state', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_update_subtask_state(self, task_id, subtask_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        subtask = request.env['garage.reception.task'].sudo().browse(subtask_id)
        if not subtask.exists() or subtask.reception_id.id != rec.id:
            return _json_response({'status': 'error', 'message': f"Subtask #{subtask_id} not found"}, status=404)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        target_state = body.get('state', '1_done')
        state_map = {
            'done': '1_done',
            '1_done': '1_done',
            'in_progress': '01_in_progress',
            '01_in_progress': '01_in_progress',
            'waiting': '04_waiting_normal',
            '04_waiting_normal': '04_waiting_normal',
        }
        clean_state = state_map.get(target_state, '1_done')

        prev_stage_seq = (rec.stage_sequence // 10) if rec.stage_sequence else 1

        if clean_state == '1_done':
            subtask.with_context(auto_workflow_sync=True).action_toggle_state()
        else:
            subtask.with_context(auto_workflow_sync=True).write({
                'state': clean_state,
                'is_done': (clean_state == '1_done'),
                'completed_date': False if clean_state != '1_done' else fields.Datetime.now(),
            })

        new_stage_seq = (rec.stage_sequence // 10) if rec.stage_sequence else 1
        advanced = (new_stage_seq > prev_stage_seq)

        advance_info = None
        if advanced:
            advance_info = {
                'advanced': True,
                'previous_seq': prev_stage_seq,
                'new_seq': new_stage_seq,
                'new_stage_name': rec.stage_id.name or '',
            }

        return _json_response({
            'status': 'ok',
            'stage_advanced': advanced,
            'advance_info': advance_info,
            'task': _reception_to_vehicle_detail(rec),
        })

    @http.route('/api/workshop/transcribe', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_transcribe(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        audio_b64 = body.get('audio_base64', '')
        task_id = body.get('task_id', 0)

        rec = request.env['garage.reception'].sudo().browse(task_id) if task_id else None

        if rec and rec.exists():
            res = rec.process_ai_diagnostic(audio_base64=audio_b64)
            return _json_response({
                'status': 'ok',
                'transcription': res.get('transcription', ''),
                'todo_tasks': res.get('todo_tasks', []),
                'is_assurance': res.get('is_assurance', False),
                'workshop_type': res.get('specialty', 'mecanique'),
            })

        dummy_rec = request.env['garage.reception'].sudo().new({
            'symptoms': 'Diagnostic vocal',
            'customer_id': request.env.ref('base.partner_admin').id if request.env.ref('base.partner_admin', False) else 1,
            'vehicle_id': request.env['fleet.vehicle'].sudo().search([], limit=1).id or 1,
        })
        res = dummy_rec.process_ai_diagnostic(audio_base64=audio_b64)
        return _json_response({
            'status': 'ok',
            'transcription': res.get('transcription', ''),
            'todo_tasks': res.get('todo_tasks', []),
            'is_assurance': res.get('is_assurance', False),
            'workshop_type': res.get('specialty', 'mecanique'),
        })

    @http.route('/api/workshop/checkin', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_checkin(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        images_b64 = body.get('images_base64') or []
        if body.get('image_base64') and body.get('image_base64') not in images_b64:
            images_b64.insert(0, body['image_base64'])

        audio_b64 = body.get('audio_base64')
        audio_note = body.get('audio_note', '')
        todo_tasks = body.get('todo_tasks') or []
        is_assurance = bool(body.get('is_assurance', False))

        # Création ou recherche du partenaire client
        Partner = request.env['res.partner'].sudo()
        customer_name = body.get('customer_name') or "Client Atelier"
        customer = Partner.search([('name', '=', customer_name)], limit=1)
        if not customer:
            customer = Partner.create({'name': customer_name})

        # Création ou recherche du véhicule
        Vehicle = request.env['fleet.vehicle'].sudo()
        model_name = body.get('brand_model') or "Véhicule Atelier"
        plate = body.get('matricule') or f"ATELIER-{fields.Datetime.now().strftime('%M%S')}"

        vehicle_model = request.env['fleet.vehicle.model'].sudo().search([('name', '=', model_name)], limit=1)
        if not vehicle_model:
            brand = request.env['fleet.vehicle.model.brand'].sudo().search([], limit=1)
            if not brand:
                brand = request.env['fleet.vehicle.model.brand'].sudo().create({'name': 'Atelier'})
            vehicle_model = request.env['fleet.vehicle.model'].sudo().create({'name': model_name, 'brand_id': brand.id})

        vehicle = Vehicle.search([('license_plate', '=', plate)], limit=1)
        if not vehicle:
            vehicle = Vehicle.create({
                'license_plate': plate,
                'model_id': vehicle_model.id,
                'customer_id': customer.id,
            })

        # Création de la fiche de réception
        Reception = request.env['garage.reception'].sudo()
        rec_vals = {
            'vehicle_id': vehicle.id,
            'customer_id': customer.id,
            'symptoms': audio_note or "Check-in Atelier",
            'is_assurance': is_assurance,
        }
        rec = Reception.create(rec_vals)

        # Ajout des pièces jointes photos
        if images_b64:
            for idx, img_b64 in enumerate(images_b64):
                try:
                    clean_b64 = img_b64.split(',')[-1].strip()
                    att = request.env['ir.attachment'].sudo().create({
                        'name': f"Photo Checkin #{idx + 1}",
                        'type': 'binary',
                        'datas': clean_b64,
                        'res_model': 'garage.reception',
                        'res_id': rec.id,
                    })
                    rec.write({'attachment_ids': [Command.link(att.id)]})
                except Exception as ie:
                    _logger.warning("Error saving checkin image: %s", ie)

        # Traitement IA pour tâches dynamiques et note pièces
        rec.process_ai_diagnostic(
            audio_base64=audio_b64,
            raw_note=audio_note,
            custom_todos=todo_tasks,
            is_assurance=is_assurance,
        )

        overview_data = self.api_get_workshop_tasks()
        parsed_overview = json.loads(overview_data.response[0]) if hasattr(overview_data, 'response') else {}

        return _json_response({
            'status': 'ok',
            'task_id': rec.id,
            'matricule': plate,
            'brand_model': model_name,
            'customer_name': customer.name,
            'diagnostic_note': rec.diagnostic_parts_note or audio_note,
            'todo_tasks': todo_tasks,
            'is_assurance': rec.is_assurance,
            'message': f"Véhicule [{plate}] réceptionné avec succès !",
            'stages': parsed_overview.get('stages', []),
            'tasks': parsed_overview.get('tasks', []),
        })

    @http.route('/api/workshop/task/<int:task_id>/voice-update', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_voice_update(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        note = body.get('note', '')
        audio_b64 = body.get('audio_base64')
        tech_name = body.get('technician_name', "Chef d'Atelier")

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        if note:
            # Vérifier si c'est une demande de pièce supplémentaire
            if any(w in note.lower() for w in ['supplémentaire', 'pièce en plus', 'devis en plus', 'لقينا', 'خاص تزيد', 'خاص تزاد']):
                rec.submit_supplementary_diagnostic(note, technician_name=tech_name)
            else:
                rec.message_post(body=f"<b>Mise à jour vocale ({tech_name}) :</b> {note}")

        return _json_response({
            'status': 'ok',
            'task': _reception_to_vehicle_detail(rec),
            'transcription': note,
            'message': "Mise à jour enregistrée avec succès.",
        })

    @http.route('/api/workshop/task/<int:task_id>/diagnostic', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_diagnostic(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        diag_note = body.get('diagnostic_note', '')
        w_type = body.get('workshop_type')
        if w_type:
            rec.specialty = w_type
        if diag_note:
            rec.diagnostic_parts_note = diag_note
            rec.action_send_note_to_stock()

        return _json_response({
            'status': 'ok',
            'task': _reception_to_vehicle_detail(rec),
        })

    @http.route('/api/workshop/task/<int:task_id>/assurance', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_assurance(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        is_assur = body.get('is_assurance', False)
        statut_exp = body.get('statut_expertise', '')
        rec.write({
            'is_assurance': is_assur,
            'statut_expertise': statut_exp or rec.statut_expertise,
        })
        return _json_response({
            'status': 'ok',
            'task': _reception_to_vehicle_detail(rec),
        })

    @http.route('/api/workshop/task/<int:task_id>/image', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_image(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        img_b64 = body.get('imageBase64') or body.get('image_base64')
        if img_b64:
            clean_b64 = img_b64.split(',')[-1].strip()
            att = request.env['ir.attachment'].sudo().create({
                'name': f"Photo Atelier {fields.Datetime.now().strftime('%H:%M:%S')}",
                'type': 'binary',
                'datas': clean_b64,
                'res_model': 'garage.reception',
                'res_id': rec.id,
            })
            rec.write({'attachment_ids': [Command.link(att.id)]})

        return _json_response({
            'status': 'ok',
            'task': _reception_to_vehicle_detail(rec),
        })

    @http.route('/api/workshop/task/<int:task_id>/early-exit', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_early_exit(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        reason = body.get('reason', 'Sortie anticipée')
        note = body.get('note', '')
        rec.message_post(body=f"<b>Sortie anticipée du véhicule :</b> {reason}. {note}")
        rec.write({'state': 'delivered'})
        return _json_response({
            'status': 'ok',
            'message': "تم تسجيل خروج المركبة بنجاح",
        })

    @http.route('/api/workshop/task/<int:task_id>/shift-update', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_shift_update(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        rec = request.env['garage.reception'].sudo().browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        shift_name = body.get('shift_name', 'Équipe')
        tech_name = body.get('technician_name', 'Technicien')
        notes = body.get('notes', '')
        rec.message_post(body=f"<b>Pointage {shift_name} ({tech_name}) :</b> {notes}")
        return _json_response({'status': 'ok', 'message': "Shift update recorded"})
