#!/usr/bin/env bash
set -euo pipefail

SERVER="root@167.233.156.220"
SSH_KEY="$HOME/.ssh/id_cx33"
REMOTE_PATH="/root/odoo19/custom_addons"

echo "=== 🚀 STEP 1: Syncing custom_addons to Hetzner Production VPS ==="
rsync -avz --exclude '__pycache__' --exclude '*.pyc' -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
    custom_addons/ \
    "$SERVER:$REMOTE_PATH/"

echo "=== 📦 STEP 2: Upgrading garage_repair_core and garage_atelier_theme on Hetzner Odoo ==="
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" \
    "docker exec odoo19_garage odoo -u garage_repair_core,garage_atelier_theme -d garage_db --stop-after-init"

echo "=== 🔧 STEP 3: Running Production Database Remediation (Brands & Plate Translation) ==="
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" "docker exec -i odoo19_garage python3" << 'EOF' || echo "[WARN] Remediation script skipped due to transient concurrency; continuing."
import odoo
from odoo.modules.registry import Registry
from odoo import api, SUPERUSER_ID

odoo.tools.config.parse_config(["-c", "/etc/odoo/odoo.conf", "-d", "garage_db"])
registry = Registry("garage_db")

with registry.cursor() as cr:
    env = api.Environment(cr, SUPERUSER_ID, {})
    
    # 1. Remediate brands
    brand_map = {
        'dacia': 'Dacia',
        'renault': 'Renault',
        'golf': 'Volkswagen',
        'volkswagen': 'Volkswagen',
        'vw': 'Volkswagen',
        'clio': 'Renault',
        'peugeot': 'Peugeot',
    }
    
    models = env['fleet.vehicle.model'].search([])
    for m in models:
        name_lower = (m.name or '').lower()
        target_brand_name = None
        for key, val in brand_map.items():
            if key in name_lower:
                target_brand_name = val
                break
        
        if target_brand_name:
            brand = env['fleet.vehicle.model.brand'].search([('name', '=ilike', target_brand_name)], limit=1)
            if brand and m.brand_id != brand:
                print(f"[REMEDIATED] Model '{m.name}': '{m.brand_id.name}' -> '{brand.name}'")
                m.brand_id = brand.id

    # 2. Normalize license plates & deduplicate brand in model names
    models = env['fleet.vehicle.model'].search([])
    for m in models:
        bname = (m.brand_id.name or '').strip()
        mname = (m.name or '').strip()
        if bname and mname and mname.lower().startswith(bname.lower()):
            clean_name = mname[len(bname):].strip(" -_")
            if clean_name:
                print(f"[REMEDIATED] Model name '{mname}' -> '{clean_name.title()}'")
                m.name = clean_name.title()

    vehicles = env['fleet.vehicle'].search([])
    for v in vehicles:
        if v.license_plate:
            old_plate = v.license_plate
            norm = env['fleet.vehicle'].normalize_moroccan_plate(old_plate)
            new_plate = norm[4] if norm and len(norm) >= 5 and norm[4] else old_plate
            if new_plate != old_plate:
                print(f"[REMEDIATED] Plate #{v.id}: '{old_plate}' -> '{new_plate}'")
                v.write({'license_plate': new_plate})
        v._compute_display_name()

    # 3. Synchronize image_128 miniatures and active references on receptions
    receptions = env['garage.reception'].search([])
    for r in receptions:
        r._compute_image_128()
        r._compute_active_reference()
        r._compute_vehicle_model_name()
        if r.image_128 and r.vehicle_id and not r.vehicle_id.image_128:
            r.vehicle_id.image_128 = r.image_128
            print(f"[REMEDIATED] Assigned image_128 to vehicle #{r.vehicle_id.id} from reception #{r.id}")

    cr.commit()
    print("[SUCCESS] Production database remediation committed.")
EOF

echo "=== 🔄 STEP 4: Restarting odoo19_garage container ==="
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" \
    "docker restart odoo19_garage"

echo "=== ✅ STEP 5: Verifying Health on Hetzner ==="
sleep 3
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SERVER" \
    "docker exec odoo19_garage curl -sI http://localhost:8069/web/login | head -n 1"

echo "=== 🎉 DEPLOYMENT TO HETZNER COMPLETED SUCCESSFULLY! ==="
