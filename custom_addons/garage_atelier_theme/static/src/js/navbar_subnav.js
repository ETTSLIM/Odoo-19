/** @odoo-module **/

import { NavBar } from "@web/webclient/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { useBus } from "@web/core/utils/hooks";
import { useEffect, useState } from "@odoo/owl";

export const GARAGE_MODULE_SUBNAVS = {
    workshop: {
        parentXmlId: "garage_repair_core.menu_garage_receptions",
        pills: [
            {
                id: "receptions",
                name: "Véhicules à l'Atelier",
                icon: "fa-car",
                action: "garage_repair_core.action_garage_reception",
                models: ["garage.reception"],
            },
            {
                id: "active_orders",
                name: "Ordres de Travaux Actifs",
                icon: "fa-wrench",
                action: "garage_repair_core.action_garage_active_repair_orders",
                models: ["repair.order"],
            },
        ],
    },
    insurance: {
        parentXmlId: "garage_repair_core.menu_garage_insurance_claim",
        pills: [
            {
                id: "claims",
                name: "Dossiers Sinistres",
                icon: "fa-shield",
                action: "garage_repair_core.action_garage_insurance_claim",
                models: ["garage.insurance.claim"],
            },
            {
                id: "claim_orders",
                name: "Devis Sinistres & Assurances",
                icon: "fa-file-text-o",
                action: "garage_repair_core.action_garage_insurance_repair_orders",
                models: [],
            },
        ],
    },
    stock: {
        parentXmlId: "garage_repair_core.menu_garage_stock",
        pills: [
            {
                id: "shelf_stock",
                name: "État du Stock Magasin",
                icon: "fa-cubes",
                action: "garage_repair_core.action_garage_stock_shelf",
                models: ["garage.parts.bl.line"],
            },
            {
                id: "parts_catalog",
                name: "Catalogue Pièces",
                icon: "fa-book",
                action: "garage_repair_core.action_garage_parts_catalog",
                models: ["product.template", "product.product"],
            },
            {
                id: "parts_bl",
                name: "BL Fournisseurs",
                icon: "fa-truck",
                action: "garage_repair_core.action_garage_parts_bl",
                models: ["garage.parts.bl"],
            },
            {
                id: "repair_orders",
                name: "Ordres & Devis (BL)",
                icon: "fa-cogs",
                action: "repair.action_repair_order_tree",
                models: [],
            },
        ],
    },
    finance: {
        parentXmlId: "garage_repair_core.menu_garage_finance",
        pills: [
            {
                id: "payments",
                name: "Journal Caisse Guichet",
                icon: "fa-money",
                action: "garage_repair_core.action_garage_repair_payment",
                models: ["garage.repair.payment"],
            },
            {
                id: "invoices",
                name: "Factures Fiscales (TVA 20%)",
                icon: "fa-file-text",
                action: "garage_repair_core.action_garage_official_invoices",
                models: ["account.move"],
            },
            {
                id: "bank_compliance",
                name: "Contrôle Conformité Bancaire",
                icon: "fa-bank",
                action: "garage_repair_core.action_garage_bank_traceability_compliance",
                models: [],
            },
        ],
    },
    directory: {
        parentXmlId: "garage_repair_core.menu_garage_directory",
        pills: [
            {
                id: "fleet_vehicles",
                name: "Parc Véhicules",
                icon: "fa-car",
                action: "fleet.fleet_vehicle_action",
                models: ["fleet.vehicle"],
            },
            {
                id: "partners",
                name: "Annuaire Contacts",
                icon: "fa-address-book-o",
                action: "garage_repair_core.action_garage_partners_unified",
                models: ["res.partner"],
            },
            {
                id: "vehicle_brands",
                name: "Marques Véhicules",
                icon: "fa-tags",
                action: "fleet.fleet_vehicle_model_brand_action",
                models: ["fleet.vehicle.model.brand"],
            },
            {
                id: "vehicle_models",
                name: "Modèles Véhicules",
                icon: "fa-car",
                action: "fleet.fleet_vehicle_model_action",
                models: ["fleet.vehicle.model"],
            },
        ],
    },
    config: {
        parentXmlId: "garage_repair_core.menu_garage_config",
        pills: [
            {
                id: "users_rights",
                name: "Utilisateurs & Droits",
                icon: "fa-users",
                action: "garage_repair_core.action_res_users_garage",
                models: ["res.users"],
            },
            {
                id: "operators",
                name: "Opérateurs PIN",
                icon: "fa-id-badge",
                action: "garage_repair_core.action_garage_workshop_operator",
                models: ["garage.workshop.operator"],
            },
            {
                id: "stages",
                name: "7 Étapes Atelier",
                icon: "fa-tasks",
                action: "garage_repair_core.action_garage_workshop_stage",
                models: ["garage.workshop.stage"],
            },
            {
                id: "whatsapp",
                name: "Paramètres WhatsApp",
                icon: "fa-whatsapp",
                action: "garage_repair_core.action_garage_whatsapp_settings",
                models: ["res.config.settings"],
            },
            {
                id: "portal_monitor",
                name: "Supervision Canaux",
                icon: "fa-globe",
                action: "garage_repair_core.action_garage_external_portal_monitor",
                models: [],
            },
            {
                id: "ui_kit",
                name: "UI Kit (Debug)",
                icon: "fa-paint-brush",
                action: "garage_repair_core.action_garage_ui_kit",
                models: ["garage.ui.kit"],
            },
        ],
    },
};

patch(NavBar.prototype, {
    setup() {
        super.setup();
        this._userLockKey = null;
        this._userLockPillId = null;
        this._userLockTime = 0;

        this.garageState = useState({
            activeModuleKey: "workshop",
            activePillId: "receptions",
        });

        useBus(this.env.bus, "ACTION_MANAGER:UPDATE", (ev) => {
            // Ignorer la transition intermédiaire BlankComponent
            if (ev && ev.detail && ev.detail.Component && ev.detail.Component.name === "BlankComponent") {
                return;
            }
            this._syncGarageSubnav();
        });

        useBus(this.env.bus, "MENUS:APP-CHANGED", () => {
            this._userLockTime = 0;
            this._syncGarageSubnav();
        });

        useEffect(() => {
            this._updateTopNavActiveDom();
        });

        // Synchro initiale au montage
        this._syncGarageSubnav();
    },

    get isGarageActive() {
        const app = this.menuService.getCurrentApp();
        return Boolean(
            app && (app.xmlid === "garage_repair_core.menu_garage_root" || app.name === "Garage Pro")
        );
    },

    set isGarageActive(_) {},

    get currentGarageSubnavItems() {
        if (!this.isGarageActive || !this.garageState.activeModuleKey) {
            return [];
        }
        const moduleConfig = GARAGE_MODULE_SUBNAVS[this.garageState.activeModuleKey];
        return moduleConfig ? moduleConfig.pills : [];
    },

    set currentGarageSubnavItems(_) {},

    getSectionClass(section) {
        let cls = "o_nav_entry";
        if (this.isGarageActive && this.garageState.activeModuleKey) {
            const targetXmlId = GARAGE_MODULE_SUBNAVS[this.garageState.activeModuleKey]?.parentXmlId;
            if (targetXmlId && section.xmlid === targetXmlId) {
                cls += " active o_garage_tab_active";
            }
        }
        return cls;
    },

    async onNavBarDropdownItemSelection(menu) {
        if (menu && menu.xmlid) {
            for (const [key, conf] of Object.entries(GARAGE_MODULE_SUBNAVS)) {
                if (conf.parentXmlId === menu.xmlid) {
                    this._userLockKey = key;
                    this._userLockPillId = conf.pills[0]?.id || null;
                    this._userLockTime = Date.now();
                    this.garageState.activeModuleKey = key;
                    this.garageState.activePillId = conf.pills[0]?.id || null;
                    this._updateTopNavActiveDom();
                    break;
                }
            }
        }
        return super.onNavBarDropdownItemSelection(menu);
    },

    async onGarageSubnavPillClick(pill) {
        if (!pill || !pill.action) return;
        this._userLockPillId = pill.id;
        this._userLockTime = Date.now();
        this.garageState.activePillId = pill.id;
        await this.actionService.doAction(pill.action, { clearBreadcrumbs: true });
    },

    _syncGarageSubnav() {
        if (!this.isGarageActive) {
            if (this.garageState.activeModuleKey !== null) {
                this.garageState.activeModuleKey = null;
                this.garageState.activePillId = null;
            }
            return;
        }

        // Si l'utilisateur vient de cliquer dans les dernières 2 secondes, verrouiller son choix
        if (this._userLockTime && (Date.now() - this._userLockTime < 2500)) {
            if (this._userLockKey) {
                this.garageState.activeModuleKey = this._userLockKey;
            }
            if (this._userLockPillId) {
                this.garageState.activePillId = this._userLockPillId;
            }
            this._updateTopNavActiveDom();
            return;
        }

        const action = this.actionService.currentController?.action;
        if (!action) {
            if (!this.garageState.activeModuleKey) {
                this.garageState.activeModuleKey = "workshop";
                this.garageState.activePillId = "receptions";
            }
            this._updateTopNavActiveDom();
            return;
        }

        const xmlId = action.xml_id || "";
        const resModel = action.res_model || "";

        // 1. Recherche par XML ID direct de l'action
        let matchedKey = null;
        let matchedPillId = null;

        for (const [key, conf] of Object.entries(GARAGE_MODULE_SUBNAVS)) {
            for (const pill of conf.pills) {
                if (pill.action === xmlId) {
                    matchedKey = key;
                    matchedPillId = pill.id;
                    break;
                }
            }
            if (matchedKey) break;
        }

        // 2. Déduction intelligente par modèle res_model et contexte
        if (!matchedKey) {
            if (resModel === "garage.reception") {
                matchedKey = "workshop";
                matchedPillId = "receptions";
            } else if (resModel === "garage.insurance.claim") {
                matchedKey = "insurance";
                matchedPillId = "claims";
            } else if (resModel === "garage.parts.bl.line") {
                matchedKey = "stock";
                matchedPillId = "shelf_stock";
            } else if (resModel === "product.template" || resModel === "product.product") {
                matchedKey = "stock";
                matchedPillId = "parts_catalog";
            } else if (resModel === "garage.parts.bl") {
                matchedKey = "stock";
                matchedPillId = "parts_bl";
            } else if (resModel === "garage.repair.payment") {
                matchedKey = "finance";
                matchedPillId = "payments";
            } else if (resModel === "account.move") {
                matchedKey = "finance";
                matchedPillId = "invoices";
            } else if (resModel === "fleet.vehicle") {
                matchedKey = "directory";
                matchedPillId = "fleet_vehicles";
            } else if (resModel === "res.partner") {
                matchedKey = "directory";
                matchedPillId = "partners";
            } else if (resModel === "fleet.vehicle.model.brand") {
                matchedKey = "directory";
                matchedPillId = "vehicle_brands";
            } else if (resModel === "fleet.vehicle.model") {
                matchedKey = "directory";
                matchedPillId = "vehicle_models";
            } else if (resModel === "res.users") {
                matchedKey = "config";
                matchedPillId = "users_rights";
            } else if (resModel === "garage.workshop.operator") {
                matchedKey = "config";
                matchedPillId = "operators";
            } else if (resModel === "garage.workshop.stage") {
                matchedKey = "config";
                matchedPillId = "stages";
            } else if (resModel === "res.config.settings") {
                matchedKey = "config";
                matchedPillId = "whatsapp";
            } else if (resModel === "garage.ui.kit") {
                matchedKey = "config";
                matchedPillId = "ui_kit";
            } else if (resModel === "repair.order") {
                const domainStr = JSON.stringify(action.domain || "");
                const ctxStr = JSON.stringify(action.context || "");
                if (domainStr.includes("insurance") || ctxStr.includes("insurance")) {
                    matchedKey = "insurance";
                    matchedPillId = "claim_orders";
                } else if (domainStr.includes("bank_traceable") || domainStr.includes("alert_compliance")) {
                    matchedKey = "finance";
                    matchedPillId = "bank_compliance";
                } else if (domainStr.includes("tracking_token")) {
                    matchedKey = "config";
                    matchedPillId = "portal_monitor";
                } else {
                    matchedKey = "workshop";
                    matchedPillId = "active_orders";
                }
            }
        }

        if (matchedKey) {
            this.garageState.activeModuleKey = matchedKey;
            this.garageState.activePillId = matchedPillId;
        }

        this._updateTopNavActiveDom();
    },

    _updateTopNavActiveDom() {
        if (!this.root || !this.root.el) return;
        const navEntries = this.root.el.querySelectorAll(".o_menu_sections .o_nav_entry");
        if (!navEntries.length) return;

        const targetXmlId = this.isGarageActive && this.garageState.activeModuleKey
            ? GARAGE_MODULE_SUBNAVS[this.garageState.activeModuleKey]?.parentXmlId
            : null;

        navEntries.forEach((el) => {
            const isTarget = targetXmlId && el.getAttribute("data-menu-xmlid") === targetXmlId;
            if (isTarget) {
                el.classList.add("o_garage_tab_active", "active");
            } else {
                el.classList.remove("o_garage_tab_active", "active");
            }
        });
    },
});
