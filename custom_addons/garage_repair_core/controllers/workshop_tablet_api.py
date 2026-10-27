# -*- coding: utf-8 -*-
import json
import base64
import os
import re
import requests
import logging
from odoo import http, fields, Command, _, SUPERUSER_ID
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

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

    images = []
    for att in r.attachment_ids:
        images.append(f"/web/image/{att.id}")

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

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
        if not rec.exists():
            return _json_response({'error': f"Vehicle task #{task_id} not found"}, status=404)

        return _json_response(_reception_to_vehicle_detail(rec))

    @http.route('/api/workshop/task/<int:task_id>/subtask/<int:subtask_id>/state', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_update_subtask_state(self, task_id, subtask_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
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
        operator_id = body.get('operator_id')
        pin_code = body.get('pin_code')
        operator = None
        if operator_id:
            try:
                op_record = request.env['garage.workshop.operator'].sudo().browse(int(operator_id))
                if op_record.exists():
                    operator = op_record
                    if pin_code and not operator.verify_pin(pin_code, target_stage_id=subtask.stage_id.id):
                        return _json_response({
                            'status': 'error',
                            'message': f"Code PIN invalide pour l'opérateur {operator.name}."
                        }, status=403)
            except Exception:
                operator = None

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

        try:
            subtask.with_context(auto_workflow_sync=True).action_toggle_state(
                operator=operator, target_state=clean_state
            )
        except (UserError, ValidationError) as ue:
            return _json_response({
                'status': 'interlock_locked',
                'interlock_message': str(ue),
                'message': str(ue),
                'stage_advanced': False,
                'task': _reception_to_vehicle_detail(rec),
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
        context_hint = body.get('context_hint') or body.get('contextHint') or ''

        if not audio_b64:
            return _json_response({
                'status': 'ok',
                'transcription': '',
                'transcription_summary': '',
                'todo_tasks': [],
                'is_assurance': False,
                'workshop_type': 'mecanique',
            })

        try:
            admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
            rec = request.env['garage.reception'].with_user(admin_user).browse(task_id) if task_id else None

            if rec and rec.exists():
                res = rec.process_ai_diagnostic(audio_base64=audio_b64, raw_note=context_hint)
                return _json_response({
                    'status': 'ok',
                    'transcription': res.get('transcription', ''),
                    'transcription_summary': res.get('transcription_summary', ''),
                    'todo_tasks': res.get('todo_tasks', []),
                    'is_assurance': res.get('is_assurance', False),
                    'workshop_type': res.get('specialty', 'mecanique'),
                })

            dummy_rec = request.env['garage.reception'].sudo().new({
                'symptoms': 'Diagnostic vocal',
                'customer_id': request.env.ref('base.partner_admin').id if request.env.ref('base.partner_admin', False) else 1,
                'vehicle_id': request.env['fleet.vehicle'].sudo().search([], limit=1).id or 1,
            })
            res = dummy_rec.process_ai_diagnostic(audio_base64=audio_b64, raw_note=context_hint)
            return _json_response({
                'status': 'ok',
                'transcription': res.get('transcription', ''),
                'transcription_summary': res.get('transcription_summary', ''),
                'todo_tasks': res.get('todo_tasks', []),
                'is_assurance': res.get('is_assurance', False),
                'workshop_type': res.get('specialty', 'mecanique'),
            })
        except Exception as e:
            _logger.exception("Error in /api/workshop/transcribe: %s", e)
            return _json_response({
                'status': 'ok',
                'transcription': '',
                'todo_tasks': [],
                'is_assurance': False,
                'workshop_type': 'mecanique',
                'warning': str(e),
            })

    @http.route('/api/workshop/ocr-document', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_ocr_document(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        img_b64 = body.get('image_base64') or body.get('imageBase64') or ''
        doc_type = body.get('doc_type') or 'carte_grise'

        if not img_b64:
            return _json_response({
                'status': 'error',
                'message': 'No image provided',
                'matricule': '',
                'brand_model': '',
                'vin': '',
                'customer_name': '',
                'odometer': None,
            })

        clean_b64 = img_b64.split(',')[-1].strip()
        img_mime = "image/jpeg"
        try:
            raw_bytes = base64.b64decode(clean_b64[:64])
            if raw_bytes.startswith(b'\x89PNG'):
                img_mime = 'image/png'
            elif raw_bytes.startswith(b'RIFF') and b'WEBP' in raw_bytes[:16]:
                img_mime = 'image/webp'
        except Exception:
            pass

        gemini_api_key = os.environ.get('GEMINI_API_KEY') or request.env['ir.config_parameter'].sudo().get_param('garage.gemini_api_key', '')

        if not gemini_api_key:
            _logger.warning("Gemini API key not configured for OCR")
            return _json_response({
                'status': 'ok',
                'message': 'Gemini API key not configured',
                'matricule': '',
                'brand_model': '',
                'vin': '',
                'customer_name': '',
                'odometer': None,
            })

        prompt = (
            "CRITICAL AUTOMOTIVE DOCUMENT OCR & VEHICLE REGISTRATION PROTOCOL (MOROCCO):\n"
            "You are an expert AI OCR specialist for Moroccan vehicle documents (Carte Grise - Certificat d'Immatriculation), "
            "insurance certificates (Attestation d'Assurance Automobile / Carte Verte), "
            "and vehicle odometer dashboards (Compteur Kilométrique).\n"
            "Examine this image carefully and extract all relevant vehicle and insurance data.\n\n"
            "RULES FOR MOROCCAN CARTE GRISE (RECTO OU VERSO):\n"
            "1. 'matricule': Registration plate number in standard Moroccan format (e.g. '12345 | أ | 6' or '12345-A-6' or 'WW 123456'). Keep the Arabic character (e.g. أ, ب, د, هـ, etc.) if visible, or its letter code.\n"
            "2. 'brand_model': Combined Make and Model (e.g. 'DACIA DUSTER', 'RENAULT CLIO 4', 'PEUGEOT 208', 'VOLKSWAGEN GOLF 7'). Look at D.1 (Marque) and D.3 (Dénomination commerciale / Modèle).\n"
            "3. 'vin': Exact 17-character Vehicle Identification Number (NIV / Numéro de châssis / E). Example: 'VF1HSD...'.\n"
            "4. 'customer_name': Full Name of the owner / titulaire (Nom et prénom du propriétaire / C.1 / C.4.1).\n"
            "5. 'odometer': Total mileage if indicated on the document, otherwise null.\n\n"
            "RULES FOR MOROCCAN ATTESTATION D'ASSURANCE (CARTE VERTE / POLICE):\n"
            "1. 'compagnie_assurance': Exact company name (e.g. 'Wafa Assurance', 'RMA', 'AtlantaSanad', 'AXA Assurance Maroc', 'Sanlam', 'MAMDA', 'MCMA', 'Allianz Maroc').\n"
            "2. 'num_police': Policy or certificate reference number (Numéro de Police / Attestation).\n"
            "3. 'matricule', 'brand_model', 'customer_name': Extract if clearly present on the insurance certificate.\n\n"
            "RULES FOR ODOMETER DASHBOARD (COMPTEUR KILOMÉTRIQUE):\n"
            "1. 'odometer': Integer value of total accumulated kilometers (e.g. 142500). Ignore trip meters (Trip A / Trip B) unless it is the only displayed mileage.\n"
            "2. 'matricule', 'brand_model', 'vin', 'customer_name': null unless clearly visible.\n\n"
            "Return STRICTLY a JSON object matching this schema:\n"
            "{\n"
            "  'status': 'ok',\n"
            "  'doc_type': 'carte_grise' | 'assurance' | 'compteur' | 'other',\n"
            "  'matricule': 'string or empty',\n"
            "  'brand_model': 'string or empty',\n"
            "  'vin': 'string or empty',\n"
            "  'customer_name': 'string or empty',\n"
            "  'compagnie_assurance': 'string or empty',\n"
            "  'num_police': 'string or empty',\n"
            "  'odometer': integer or null,\n"
            "  'confidence': float between 0.0 and 1.0\n"
            "}"
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"inline_data": {"mime_type": img_mime, "data": clean_b64}},
                        {"text": prompt}
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "response_mime_type": "application/json"
                }
            }
            res = requests.post(url, json=payload, timeout=25)
            if res.status_code == 200:
                text_resp = res.json().get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '{}')
                m = re.search(r'\{.*\}', text_resp, re.DOTALL)
                if m:
                    p_data = json.loads(m.group(0))
                    odo_val = p_data.get('odometer')
                    if odo_val is not None:
                        try:
                            odo_val = int(odo_val)
                        except Exception:
                            odo_val = None
                    return _json_response({
                        'status': 'ok',
                        'doc_type': p_data.get('doc_type', doc_type),
                        'matricule': p_data.get('matricule') or '',
                        'brand_model': p_data.get('brand_model') or '',
                        'vin': p_data.get('vin') or '',
                        'customer_name': p_data.get('customer_name') or '',
                        'compagnie_assurance': p_data.get('compagnie_assurance') or '',
                        'num_police': p_data.get('num_police') or '',
                        'odometer': odo_val,
                        'confidence': p_data.get('confidence', 0.95),
                        'message': 'Extraction OCR réussie',
                    })
            else:
                _logger.warning("Gemini OCR HTTP error %s: %s", res.status_code, res.text[:200])
        except Exception as e:
            _logger.exception("Error in /api/workshop/ocr-document: %s", e)

        return _json_response({
            'status': 'ok',
            'matricule': '',
            'brand_model': '',
            'vin': '',
            'customer_name': '',
            'odometer': None,
            'message': 'Échec de lecture automatique',
        })

    @http.route('/api/workshop/checkin', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_checkin(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        try:
            images_b64 = body.get('images_base64') or []
            if body.get('image_base64') and body.get('image_base64') not in images_b64:
                images_b64.insert(0, body['image_base64'])

            audio_b64 = body.get('audio_base64')
            audio_note = body.get('audio_note', '')
            todo_tasks = body.get('todo_tasks') or []
            is_assurance = bool(body.get('is_assurance', False))

            admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
            env = request.env(user=admin_user)

            # Création ou recherche du partenaire client
            Partner = env['res.partner']
            customer_name = (body.get('customer_name') or '').strip() or "Client Atelier"
            customer = Partner.search([('name', '=', customer_name)], limit=1)
            if not customer:
                customer = Partner.create({'name': customer_name})

            # Création ou recherche du véhicule
            Vehicle = env['fleet.vehicle']
            model_name = (body.get('brand_model') or '').strip() or "Véhicule Atelier"
            plate = (body.get('matricule') or '').strip() or f"ATELIER-{fields.Datetime.now().strftime('%M%S')}"
            vin = (body.get('vin') or '').strip()
            clean_vin = re.sub(r'[\s\-]', '', vin).upper() if vin else ''
            odometer_val = body.get('odometer')
            categorized_images = body.get('categorized_images') or []

            # Extraction de la photo avatar principale du véhicule (Face avant du véhicule en priorité absolue)
            primary_image_b64 = None
            if categorized_images:
                # Priorité 1 : Photo Face Avant / Choc Avant du véhicule
                for item in categorized_images:
                    c_type = (item.get('doc_type') or item.get('category') or '').lower()
                    c_b64 = item.get('image_base64') or item.get('imageBase64')
                    if c_b64 and c_type in ('choc_avant', 'face_avant', 'avant', 'front'):
                        primary_image_b64 = c_b64.split(',')[-1].strip()
                        break
                # Priorité 2 : Autres photos carrosserie (choc_arriere, choc_cote, choc)
                if not primary_image_b64:
                    for item in categorized_images:
                        c_type = (item.get('doc_type') or item.get('category') or '').lower()
                        c_b64 = item.get('image_base64') or item.get('imageBase64')
                        if c_b64 and c_type in ('choc_arriere', 'choc_cote', 'choc'):
                            primary_image_b64 = c_b64.split(',')[-1].strip()
                            break
                # Priorité 3 : Première photo non administrative
                if not primary_image_b64:
                    for item in categorized_images:
                        c_type = (item.get('doc_type') or item.get('category') or '').lower()
                        c_b64 = item.get('image_base64') or item.get('imageBase64')
                        if c_b64 and c_type not in ('carte_grise', 'carte_grise_recto', 'carte_grise_verso', 'permis', 'constat', 'assurance'):
                            primary_image_b64 = c_b64.split(',')[-1].strip()
                            break
            if not primary_image_b64 and images_b64:
                primary_image_b64 = images_b64[0].split(',')[-1].strip()

            # Extraction intelligente de la marque et du modèle (Élimination du bug d'injection Abarth)
            clean_brand_model = model_name.strip()
            known_brands = [
                'DACIA', 'RENAULT', 'PEUGEOT', 'VOLKSWAGEN', 'CITROEN', 'CITROËN',
                'HYUNDAI', 'KIA', 'TOYOTA', 'FORD', 'FIAT', 'MERCEDES-BENZ', 'MERCEDES',
                'BMW', 'AUDI', 'SEAT', 'SKODA', 'NISSAN', 'OPEL', 'JEEP', 'LAND ROVER',
                'RANGE ROVER', 'VOLVO', 'SUZUKI', 'HONDA', 'MITSUBISHI', 'CHEVROLET',
                'ALFA ROMEO', 'PORSCHE', 'DS', 'CUPRA', 'MG', 'GEELY', 'CHERY', 'BYD'
            ]
            extracted_brand_name = None
            extracted_model_name = clean_brand_model
            upper_bm = clean_brand_model.upper()
            for kb in sorted(known_brands, key=len, reverse=True):
                if upper_bm.startswith(kb):
                    extracted_brand_name = clean_brand_model[:len(kb)].strip()
                    remainder = clean_brand_model[len(kb):].strip(' -_')
                    if remainder:
                        extracted_model_name = remainder
                    break

            if not extracted_brand_name:
                words = clean_brand_model.split()
                if len(words) >= 2:
                    extracted_brand_name = words[0].strip()
                    extracted_model_name = " ".join(words[1:]).strip()
                else:
                    extracted_brand_name = clean_brand_model or "Atelier"
                    extracted_model_name = clean_brand_model or "Véhicule"

            Brand = env['fleet.vehicle.model.brand']
            brand = Brand.search([('name', '=ilike', extracted_brand_name)], limit=1)
            if not brand:
                brand = Brand.create({'name': extracted_brand_name.title()})

            vehicle_model = env['fleet.vehicle.model'].search([
                ('name', '=ilike', extracted_model_name),
                ('brand_id', '=', brand.id)
            ], limit=1)
            if not vehicle_model:
                vehicle_model = env['fleet.vehicle.model'].create({
                    'name': extracted_model_name,
                    'brand_id': brand.id
                })

            # Normalisation et recherche du véhicule par plaque NARSA bilingue
            num_p, lat_p, ar_p, reg_p, canonical_p = Vehicle.normalize_moroccan_plate(plate)
            search_plate = canonical_p if canonical_p else plate
            vehicle = Vehicle.search(['|', ('license_plate', '=', plate), ('license_plate', '=', search_plate)], limit=1)
            if not vehicle and num_p and reg_p and lat_p:
                vehicle = Vehicle.search([
                    ('plate_number_part', '=', num_p),
                    ('plate_region_part', '=', reg_p),
                    ('plate_letter_part', '=', lat_p)
                ], limit=1)

            vehicle_vals = {
                'license_plate': search_plate,
                'model_id': vehicle_model.id,
                'customer_id': customer.id,
            }
            if num_p and reg_p and lat_p:
                vehicle_vals['plate_number_part'] = num_p
                vehicle_vals['plate_region_part'] = reg_p
                vehicle_vals['plate_letter_part'] = lat_p
            if primary_image_b64:
                vehicle_vals['image_128'] = primary_image_b64
            if vin:
                if 'vin_sn' in Vehicle._fields:
                    vehicle_vals['vin_sn'] = clean_vin or vin
                if 'vin_number' in Vehicle._fields and 5 <= len(clean_vin) <= 17:
                    vehicle_vals['vin_number'] = clean_vin
            if odometer_val is not None:
                try:
                    vehicle_vals['odometer'] = float(odometer_val)
                except Exception:
                    pass

            if not vehicle:
                vehicle = Vehicle.create(vehicle_vals)
            else:
                upd_vals = {}
                if primary_image_b64:
                    upd_vals['image_128'] = primary_image_b64
                if vin:
                    if 'vin_sn' in Vehicle._fields and not vehicle.vin_sn:
                        upd_vals['vin_sn'] = clean_vin or vin
                    if 'vin_number' in Vehicle._fields and not vehicle.vin_number and 5 <= len(clean_vin) <= 17:
                        upd_vals['vin_number'] = clean_vin
                if odometer_val is not None and 'odometer' in Vehicle._fields:
                    try:
                        upd_vals['odometer'] = float(odometer_val)
                    except Exception:
                        pass
                if upd_vals:
                    vehicle.write(upd_vals)

            # Mode A vs Mode B : Détection intake réceptionniste (sans audio ni tâches) vs mécanicien
            is_mode_a_receptionist = not audio_b64 and not audio_note and not todo_tasks

            # Création de la fiche de réception
            Reception = env['garage.reception']
            rec_vals = {
                'vehicle_id': vehicle.id,
                'customer_id': customer.id,
                'symptoms': audio_note or ("En attente de diagnostic mécanicien" if is_mode_a_receptionist else "Check-in Atelier"),
                'is_assurance': is_assurance,
                'stock_status': 'attente_diag' if is_mode_a_receptionist else 'envoye_stock',
                'insurance_company_custom': (body.get('compagnie_assurance') or body.get('insurance_company') or '').strip(),
            }
            if odometer_val is not None:
                try:
                    rec_vals['odometer_in'] = int(odometer_val)
                except Exception:
                    pass
            rec = Reception.create(rec_vals)

            # Ajout des pièces jointes photos catégorisées
            categorized_images = body.get('categorized_images') or []
            if categorized_images:
                name_map = {
                    'carte_grise_recto': "Carte Grise (Face Avant)",
                    'carte_grise_verso': "Carte Grise (Face Arrière)",
                    'carte_grise': "Carte Grise (Checkin)",
                    'permis': "Permis de Conduire (Checkin)",
                    'constat': "Constat Amiable (Checkin)",
                    'assurance': "Attestation Assurance (Checkin)",
                    'choc_avant': "Photo Véhicule (Face Avant / Choc)",
                    'choc_arriere': "Dégât / Choc Arrière (Checkin)",
                    'choc_cote': "Dégât / Choc Côtés (Checkin)",
                    'compteur': "Compteur Kilométrique (Checkin)",
                    'choc': "Photo Dégât Atelier (Checkin)",
                }
                for item in categorized_images:
                    try:
                        c_b64 = item.get('image_base64') or item.get('imageBase64')
                        c_type = (item.get('doc_type') or item.get('category') or 'choc').lower()
                        if c_b64:
                            clean_b64 = c_b64.split(',')[-1].strip()
                            att_name = name_map.get(c_type, f"Photo Checkin ({c_type})")

                            att = env['ir.attachment'].create({
                                'name': att_name,
                                'type': 'binary',
                                'datas': clean_b64,
                                'res_model': 'garage.reception',
                                'res_id': rec.id,
                            })
                            rec.write({'attachment_ids': [Command.link(att.id)]})
                            if c_type in ('carte_grise', 'carte_grise_recto', 'carte_grise_verso'):
                                rec.write({'carte_grise_ids': [Command.link(att.id)]})
                            elif c_type == 'permis':
                                rec.write({'permis_ids': [Command.link(att.id)]})
                            elif c_type == 'constat':
                                rec.write({'constat_ids': [Command.link(att.id)]})
                            elif c_type == 'assurance':
                                rec.write({'assurance_ids': [Command.link(att.id)]})
                    except Exception as ie:
                        _logger.warning("Error saving categorized checkin image: %s", ie)

            if images_b64 and not categorized_images:
                for idx, img_b64 in enumerate(images_b64):
                    try:
                        clean_b64 = img_b64.split(',')[-1].strip()
                        att = env['ir.attachment'].create({
                            'name': f"Photo Checkin #{idx + 1}",
                            'type': 'binary',
                            'datas': clean_b64,
                            'res_model': 'garage.reception',
                            'res_id': rec.id,
                        })
                        rec.write({'attachment_ids': [Command.link(att.id)]})
                    except Exception as ie:
                        _logger.warning("Error saving checkin image: %s", ie)

            # Affectation de l'image miniature du véhicule (Face avant)
            if primary_image_b64:
                try:
                    rec.write({'image_128': primary_image_b64})
                    vehicle.write({'image_128': primary_image_b64})
                except Exception as ime:
                    _logger.warning("Error assigning primary vehicle image: %s", ime)

            # Traitement IA uniquement si note ou tâches ou audio fourni (Mode B Mécanicien)
            if not is_mode_a_receptionist:
                rec.process_ai_diagnostic(
                    audio_base64=audio_b64,
                    raw_note=audio_note,
                    custom_todos=todo_tasks,
                    is_assurance=is_assurance,
                )

            # Initialisation automatique du dossier Sinistre & Assurance si coché à la réception
            if is_assurance and not rec.claim_id:
                try:
                    rec.action_create_or_view_claim()
                except Exception as ce:
                    _logger.warning("Error auto-initiating insurance claim in checkin: %s", ce)

            # Création de l'ordre de réparation (1:1)
            rec.action_create_or_view_repair_order()
            ro = rec.repair_order_id

            # Maintien strict du véhicule à l'étape 10 Réception dans le Kanban atelier (pas de saut vers Devis)
            stage_reception = env['garage.workshop.stage'].search([('sequence', '=', 10)], limit=1)
            if stage_reception and rec.stage_id.id != stage_reception.id:
                rec.write({'stage_id': stage_reception.id})

            overview_data = self.api_get_workshop_tasks()
            parsed_overview = json.loads(overview_data.response[0]) if hasattr(overview_data, 'response') else {}

            return _json_response({
                'status': 'ok',
                'task_id': rec.id,
                'reception_id': rec.id,
                'repair_order_id': ro.id if ro else False,
                'repair_order_name': ro.name if ro else '',
                'matricule': plate,
                'brand_model': model_name,
                'vin': vin or (vehicle.vin_sn if hasattr(vehicle, 'vin_sn') else ''),
                'customer_name': customer.name,
                'odometer': rec.odometer_in if hasattr(rec, 'odometer_in') else odometer_val,
                'diagnostic_note': rec.diagnostic_parts_note or audio_note,
                'todo_tasks': todo_tasks,
                'is_assurance': rec.is_assurance,
                'message': f"Véhicule [{plate}] réceptionné et Ordre de Réparation {ro.name if ro else ''} initialisé avec succès !",
                'stages': parsed_overview.get('stages', []),
                'tasks': parsed_overview.get('tasks', []),
            })
        except Exception as e:
            _logger.exception("Error in /api/workshop/checkin: %s", e)
            return _json_response({
                'status': 'error',
                'message': str(e),
            }, status=400)

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

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        if audio_b64:
            # Traitement complet multimodal du diagnostic audio mécanicien
            try:
                res = rec.process_ai_diagnostic(audio_base64=audio_b64, raw_note=note)
                note = res.get('transcription') or note
            except Exception as ae:
                _logger.warning("Error processing voice update audio: %s", ae)
        elif note:
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

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
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

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
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

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        img_b64 = body.get('imageBase64') or body.get('image_base64')
        doc_type = (body.get('doc_type') or body.get('photo_category') or body.get('category') or 'atelier').lower()
        if img_b64:
            clean_b64 = img_b64.split(',')[-1].strip()
            now_str = fields.Datetime.now().strftime('%d/%m %H:%M')
            if doc_type == 'carte_grise':
                att_name = f"Carte Grise ({now_str})"
            elif doc_type == 'permis':
                att_name = f"Permis de Conduire ({now_str})"
            elif doc_type == 'constat':
                att_name = f"Constat Amiable ({now_str})"
            elif doc_type == 'assurance':
                att_name = f"Attestation Assurance ({now_str})"
            elif doc_type in ('choc', 'damage', 'compteur'):
                att_name = f"Photo Choc / Dégât ({now_str})"
            else:
                att_name = f"Photo Atelier {fields.Datetime.now().strftime('%H:%M:%S')}"

            att = request.env['ir.attachment'].sudo().create({
                'name': att_name,
                'type': 'binary',
                'datas': clean_b64,
                'res_model': 'garage.reception',
                'res_id': rec.id,
            })
            rec.write({'attachment_ids': [Command.link(att.id)]})

            if doc_type == 'carte_grise':
                rec.write({'carte_grise_ids': [Command.link(att.id)]})
                if rec.claim_id:
                    rec.claim_id.write({'carte_grise_ids': [Command.link(att.id)]})
            elif doc_type == 'permis':
                rec.write({'permis_ids': [Command.link(att.id)]})
                if rec.claim_id:
                    rec.claim_id.write({'permis_ids': [Command.link(att.id)]})
            elif doc_type == 'constat':
                rec.write({'constat_ids': [Command.link(att.id)]})
                if rec.claim_id:
                    rec.claim_id.write({'constat_ids': [Command.link(att.id)]})
            elif doc_type == 'assurance':
                rec.write({'assurance_ids': [Command.link(att.id)]})
                if rec.claim_id:
                    rec.claim_id.write({'assurance_ids': [Command.link(att.id)]})

        return _json_response({
            'status': 'ok',
            'task': _reception_to_vehicle_detail(rec),
        })

    @http.route('/api/workshop/task/<int:task_id>/early-exit', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_early_exit(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        reason = body.get('reason', 'Sortie anticipée')
        note = body.get('note', '')
        rec.message_post(body=f"<b>Sortie anticipée du véhicule :</b> {reason}. {note}")
        stage_delivered = request.env['garage.workshop.stage'].sudo().search([('sequence', '=', 70)], limit=1)
        vals = {'state': 'delivered'}
        if stage_delivered:
            vals['stage_id'] = stage_delivered.id
        rec.write(vals)
        return _json_response({
            'status': 'ok',
            'message': "تم تسجيل خروج المركبة بنجاح",
        })

    @http.route('/api/workshop/task/<int:task_id>/cancel', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_cancel_task(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
        if not rec.exists():
            return _json_response({'status': 'error', 'message': f"Vehicle #{task_id} not found"}, status=404)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        reason = body.get('reason', 'Annulation / Retrait du tableau')
        rec.message_post(body=f"<b>Véhicule retiré du tableau atelier :</b> {reason}")
        rec.action_cancel()
        return _json_response({
            'status': 'ok',
            'message': "تم سحب المركبة من لوحة التحكم بنجاح",
        })

    @http.route('/api/workshop/task/<int:task_id>/shift-update', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_shift_update(self, task_id, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        admin_user = request.env['res.users'].sudo().browse(SUPERUSER_ID)
        rec = request.env['garage.reception'].with_user(admin_user).browse(task_id)
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

    @http.route('/api/workshop/operators', type='http', auth='none', methods=['GET', 'OPTIONS'], csrf=False)
    def api_get_operators(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        operators = request.env['garage.workshop.operator'].sudo().search([('active', '=', True)], order='name asc')
        data = [{
            'id': op.id,
            'name': op.name,
            'role': op.role or 'mechanic',
            'specialty': op.specialty or 'general',
            'pin_code': op.pin_code or '',
        } for op in operators]
        return _json_response({
            'status': 'ok',
            'operators': data,
        })

    @http.route('/api/admin/chat', type='http', auth='none', methods=['POST', 'OPTIONS'], csrf=False)
    def api_admin_chat(self, **kwargs):
        if request.httprequest.method == 'OPTIONS':
            return _json_response({}, status=200)

        try:
            body = json.loads(request.httprequest.data or '{}')
        except Exception:
            body = {}

        message = body.get('message', '').strip()
        if not message:
            return _json_response({'reply': "أهلاً بك! كيف يمكنني مساعدتك في ورشة السيارات اليوم؟"})

        receptions = request.env['garage.reception'].sudo().search(
            [('state', 'not in', ('delivered', 'cancel'))],
            order='stage_sequence asc, date_reception desc',
            limit=25
        )
        context_lines = []
        for r in receptions:
            st_name = r.stage_id.name if r.stage_id else "Réception"
            context_lines.append(
                f"- السيارة [{r.license_plate}] ({r.vehicle_id.name if r.vehicle_id else 'Atelier'}), "
                f"الزبون: {r.customer_id.name if r.customer_id else ''}, المرحلة: {st_name}, "
                f"حالة القطع: {r.stock_status or 'عادية'}, تقدم المهام: {int(r.checklist_progress)}%"
            )
        active_fleet_summary = "\n".join(context_lines) if context_lines else "لا توجد سيارات حالياً في الورشة."

        gemini_api_key = os.environ.get('GEMINI_API_KEY') or request.env['ir.config_parameter'].sudo().get_param('garage.gemini_api_key', '')
        if not gemini_api_key:
            return _json_response({
                'reply': f"مرحباً! وضعية السيارات النشطة في ورشة Odoo 19:\n{active_fleet_summary}\n(يرجى إدخال GEMINI_API_KEY في إعدادات Odoo للتواصل الذكي الكامل)."
            })

        system_instruction = (
            "أنت المساعد الذكي ورئيس العمليات التقني لورشة تصليح السيارات (Chef d'Atelier Copilot) في المغرب.\n"
            "تتحدث بالدارجة المغربية المهنية الممزوجة بالمصطلحات التقنية الفرنسية الخاصة بالسيارات.\n"
            "إليك الوضعية الحالية للسيارات النشطة في ورشة Odoo 19:\n"
            f"{active_fleet_summary}\n\n"
            "أجب باقتضاب واحترافية ودقة على أسئلة المشرف أو الميكانيكي."
        )

        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}"
            payload = {
                "contents": [{"role": "user", "parts": [{"text": message}]}],
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 600}
            }
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=12)
            if resp.status_code == 200:
                res_data = resp.json()
                reply_text = res_data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                return _json_response({'reply': reply_text or "تم فحص الورشة بنجاح."})
            else:
                return _json_response({'reply': f"حالة السيارات في الورشة:\n{active_fleet_summary}"})
        except Exception as ge:
            _logger.error("Gemini Copilot exception: %s", ge)
            return _json_response({'reply': f"حالة السيارات في الورشة:\n{active_fleet_summary}"})
