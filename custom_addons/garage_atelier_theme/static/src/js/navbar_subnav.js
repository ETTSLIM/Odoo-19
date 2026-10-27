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
                actionId: 483,
                actionName: "Véhicules à l'Atelier",
                models: ["garage.reception"],
            },
            {
                id: "active_orders",
                name: "Ordres de Travaux Actifs",
                icon: "fa-wrench",
                action: "garage_repair_core.action_garage_active_repair_orders",
                actionId: 527,
                actionName: "Ordres de Travaux Actifs",
                models: ["repair.order"],
            },
            {
                id: "tablet_pairing",
                name: "Appairage Tablette (QR)",
                icon: "fa-qrcode",
                action: "garage_repair_core.action_garage_tablet_pairing",
                actionId: 541,
                actionName: "Appairage Tablette Atelier",
                models: ["garage.tablet.pairing.wizard"],
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
                actionId: 494,
                actionName: "Dossiers Sinistres & Assurances",
                models: ["garage.insurance.claim"],
            },
            {
                id: "claim_orders",
                name: "Devis Sinistres & Assurances",
                icon: "fa-file-text-o",
                action: "garage_repair_core.action_garage_insurance_repair_orders",
                actionId: 526,
                actionName: "Devis Sinistres & Assurances",
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
                actionId: 529,
                actionName: "État du Stock Magasin (Rayon)",
                models: ["garage.parts.bl.line"],
            },
            {
                id: "parts_catalog",
                name: "Catalogue Pièces",
                icon: "fa-book",
                action: "garage_repair_core.action_garage_parts_catalog",
                actionId: 530,
                actionName: "Catalogue Pièces Détachées",
                models: ["product.template", "product.product"],
            },
            {
                id: "parts_bl",
                name: "BL Fournisseurs",
                icon: "fa-truck",
                action: "garage_repair_core.action_garage_parts_bl",
                actionId: 490,
                actionName: "Bons de Réception Pièces (BL Fournisseurs)",
                models: ["garage.parts.bl"],
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
                actionId: 523,
                actionName: "Journal Caisse Guichet & Règlements",
                models: ["garage.repair.payment"],
            },
            {
                id: "invoices",
                name: "Factures Fiscales (TVA 20%)",
                icon: "fa-file-text",
                action: "garage_repair_core.action_garage_official_invoices",
                actionId: 524,
                actionName: "Factures Fiscales Clients (TVA 20%)",
                models: ["account.move"],
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
                actionId: 168,
                actionName: "Vehicles",
                models: ["fleet.vehicle"],
            },
            {
                id: "customers",
                name: "Clients Atelier",
                icon: "fa-users",
                action: "garage_repair_core.action_garage_customers",
                actionId: 533,
                actionName: "Clients Atelier (Particuliers & Sociétés)",
                models: ["res.partner"],
            },
            {
                id: "suppliers",
                name: "Fournisseurs Pièces",
                icon: "fa-truck",
                action: "garage_repair_core.action_garage_suppliers",
                actionId: 534,
                actionName: "Fournisseurs de Pièces Auto",
                models: ["res.partner"],
            },
            {
                id: "insurances",
                name: "Assurances",
                icon: "fa-shield",
                action: "garage_repair_core.action_garage_insurances",
                actionId: 536,
                actionName: "Compagnies d'Assurance",
                models: ["res.partner"],
            },
            {
                id: "experts",
                name: "Cabinets d'Expertise",
                icon: "fa-briefcase",
                action: "garage_repair_core.action_garage_experts",
                actionId: 537,
                actionName: "Cabinets d'Expertise Automobile",
                models: ["res.partner"],
            },
            {
                id: "partners",
                name: "Tous les Contacts",
                icon: "fa-address-book-o",
                action: "garage_repair_core.action_garage_partners_unified",
                actionId: 507,
                actionName: "Tous les Contacts Atelier",
                models: ["res.partner"],
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
                actionId: 531,
                actionName: "Équipe Atelier & Permissions Modules",
                models: ["res.users"],
            },
            {
                id: "operators",
                name: "Opérateurs PIN",
                icon: "fa-id-badge",
                action: "garage_repair_core.action_garage_workshop_operator",
                actionId: 501,
                actionName: "Opérateurs Atelier (Codes PIN)",
                models: ["garage.workshop.operator"],
            },
            {
                id: "stages",
                name: "7 Étapes Atelier",
                icon: "fa-tasks",
                action: "garage_repair_core.action_garage_workshop_stage",
                actionId: 500,
                actionName: "Étapes Atelier (7 Étapes)",
                models: ["garage.workshop.stage"],
            },
            {
                id: "whatsapp",
                name: "Paramètres WhatsApp",
                icon: "fa-whatsapp",
                action: "garage_repair_core.action_garage_whatsapp_settings",
                actionId: 532,
                actionName: "Configuration WhatsApp & Canaux",
                models: ["res.config.settings"],
            },
            {
                id: "tablet_pairing_config",
                name: "Appairage Tablette (QR)",
                icon: "fa-qrcode",
                action: "garage_repair_core.action_garage_tablet_pairing",
                actionId: 541,
                actionName: "Appairage Tablette Atelier",
                models: ["garage.tablet.pairing.wizard"],
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
            if (ev && ev.detail && ev.detail.Component && ev.detail.Component.name === "BlankComponent") {
                return;
            }
            this._syncGarageSubnav();
        });

        useBus(this.env.bus, "MENUS:APP-CHANGED", () => {
            this._userLockTime = 0;
            this._syncGarageSubnav();
        });

        const onResize = () => {
            this._alignSubnavUnderActiveModule();
        };
        window.addEventListener("resize", onResize);

        useEffect(() => {
            this._updateTopNavActiveDom();
            this._alignSubnavUnderActiveModule();
        });

        // Synchro initiale au montage
        this._syncGarageSubnav();
    },

    get isGarageActive() {
        const app = this.menuService.getCurrentApp();
        if (app && (app.xmlid === "garage_repair_core.menu_garage_root" || app.name === "Garage Pro")) {
            return true;
        }
        const action = this.actionService.currentController?.action;
        const resModel = action?.res_model || "";
        const xmlId = action?.xml_id || "";
        if (
            resModel.startsWith("garage.") ||
            resModel === "repair.order" ||
            resModel === "fleet.vehicle" ||
            resModel === "fleet.vehicle.model" ||
            resModel === "fleet.vehicle.model.brand" ||
            xmlId.startsWith("garage_repair_core.")
        ) {
            return true;
        }
        return false;
    },

    set isGarageActive(_) {},

    get activeModuleName() {
        const names = {
            workshop: "Atelier & Entrées",
            insurance: "Sinistres & Assurances",
            stock: "Pièces, Stock & BL",
            finance: "Caisse & Factures",
            directory: "Parc & Annuaire",
            config: "Configuration",
        };
        return names[this.garageState.activeModuleKey] || "Atelier & Entrées";
    },

    get activeModuleIcon() {
        const icons = {
            workshop: "fa-car",
            insurance: "fa-shield",
            stock: "fa-cubes",
            finance: "fa-money",
            directory: "fa-book",
            config: "fa-cogs",
        };
        return icons[this.garageState.activeModuleKey] || "fa-car";
    },

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
                    this._alignSubnavUnderActiveModule();
                    break;
                }
            }
        }
        return super.onNavBarDropdownItemSelection(menu);
    },

    async onGarageSubnavPillClick(pill) {
        if (!pill || !pill.action) return;
        // 1-Click Instant Activation: update active state immediately
        let pillModuleKey = this.garageState.activeModuleKey;
        for (const [key, conf] of Object.entries(GARAGE_MODULE_SUBNAVS)) {
            if (conf.pills.some((p) => p.id === pill.id)) {
                pillModuleKey = key;
                break;
            }
        }
        this._userLockKey = pillModuleKey;
        this._userLockPillId = pill.id;
        this._userLockTime = Date.now();
        this.garageState.activeModuleKey = pillModuleKey;
        this.garageState.activePillId = pill.id;
        this._updateTopNavActiveDom();
        this._alignSubnavUnderActiveModule();
        await this.actionService.doAction(pill.action, { clearBreadcrumbs: true });
    },

    _alignSubnavUnderActiveModule() {
        if (!this.root || !this.root.el || !this.isGarageActive) return;
        const subnavBar = this.root.el.querySelector(".o_garage_subnav_bar");
        const wrapper = this.root.el.querySelector(".o_garage_subnav_wrapper");
        if (!subnavBar || !wrapper) return;

        const targetXmlId = this.garageState.activeModuleKey
            ? GARAGE_MODULE_SUBNAVS[this.garageState.activeModuleKey]?.parentXmlId
            : null;
        if (!targetXmlId) {
            wrapper.style.marginLeft = "16px";
            return;
        }

        const activeNavEl = this.root.el.querySelector(
            `.o_menu_sections [data-menu-xmlid="${targetXmlId}"]`
        );
        if (!activeNavEl) {
            wrapper.style.marginLeft = "16px";
            return;
        }

        const navRect = activeNavEl.getBoundingClientRect();
        const barRect = subnavBar.getBoundingClientRect();
        const wrapperRect = wrapper.getBoundingClientRect();
        const wrapperWidth = wrapperRect.width || wrapper.offsetWidth || wrapper.scrollWidth;

        // Horizontally center the subnav wrapper directly on the active module tab
        const navCenterX = (navRect.left - barRect.left) + (navRect.width / 2);
        let targetLeft = Math.round(navCenterX - (wrapperWidth / 2));

        // Keep inside screen bounds with 16px safety margin
        const maxWidth = barRect.width;
        if (wrapperWidth + 32 <= maxWidth) {
            if (targetLeft + wrapperWidth > maxWidth - 16) {
                targetLeft = Math.round(maxWidth - wrapperWidth - 16);
            }
            if (targetLeft < 16) {
                targetLeft = 16;
            }
        } else {
            targetLeft = 16;
        }

        wrapper.style.marginLeft = `${targetLeft}px`;
    },

    _syncGarageSubnav() {
        if (!this.isGarageActive) {
            if (this.garageState.activeModuleKey !== null) {
                this.garageState.activeModuleKey = null;
                this.garageState.activePillId = null;
            }
            return;
        }

        // Si l'utilisateur a cliqué récemment, respecter son choix sans écrasement
        if (this._userLockTime && Date.now() - this._userLockTime < 3500) {
            if (this._userLockKey) {
                this.garageState.activeModuleKey = this._userLockKey;
            }
            if (this._userLockPillId) {
                this.garageState.activePillId = this._userLockPillId;
            }
            this._updateTopNavActiveDom();
            this._alignSubnavUnderActiveModule();
            return;
        }

        const action = this.actionService.currentController?.action;
        if (!action) {
            if (!this.garageState.activeModuleKey) {
                this.garageState.activeModuleKey = "workshop";
                this.garageState.activePillId = "receptions";
            }
            this._updateTopNavActiveDom();
            this._alignSubnavUnderActiveModule();
            return;
        }

        const xmlId = action.xml_id || "";
        const actionId = action.id || null;
        const actionName = action.name || action.display_name || "";
        const resModel = action.res_model || "";

        // 1. Recherche par XML ID, ID numérique ou Nom direct de l'action
        let matchedKey = null;
        let matchedPillId = null;

        for (const [key, conf] of Object.entries(GARAGE_MODULE_SUBNAVS)) {
            for (const pill of conf.pills) {
                if (
                    (xmlId && pill.action === xmlId) ||
                    (actionId && pill.actionId && pill.actionId === actionId) ||
                    (actionName && pill.actionName && pill.actionName === actionName)
                ) {
                    matchedKey = key;
                    matchedPillId = pill.id;
                    break;
                }
            }
            if (matchedKey) break;
        }

        // 2. Déduction intelligente par modèle res_model et contexte
        if (!matchedKey) {
            if (resModel === "garage.reception" || resModel === "garage.damage.item" || resModel === "garage.diagnostic.log") {
                matchedKey = "workshop";
                matchedPillId = "receptions";
            } else if (resModel === "garage.insurance.claim") {
                matchedKey = "insurance";
                matchedPillId = "claims";
            } else if (resModel === "garage.tablet.pairing.wizard") {
                matchedKey = "workshop";
                matchedPillId = "tablet_pairing";
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
                matchedPillId = this.garageState.activePillId || "partners";
            } else if (resModel === "fleet.vehicle.model.brand" || resModel === "fleet.vehicle.model") {
                matchedKey = "directory";
                matchedPillId = "fleet_vehicles";
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
                } else {
                    matchedKey = "workshop";
                    matchedPillId = "active_orders";
                }
            }
        }

        if (matchedKey) {
            this.garageState.activeModuleKey = matchedKey;
            if (matchedPillId) {
                this.garageState.activePillId = matchedPillId;
            }
        }

        this._updateTopNavActiveDom();
        this._alignSubnavUnderActiveModule();
    },

    _updateTopNavActiveDom() {
        if (!this.root || !this.root.el) return;
        const navEntries = this.root.el.querySelectorAll(".o_menu_sections .o_nav_entry, .o_menu_sections [data-menu-xmlid], .o_menu_sections .dropdown-item, .o_menu_sections button");
        if (!navEntries.length) return;

        const targetXmlId =
            this.isGarageActive && this.garageState.activeModuleKey
                ? GARAGE_MODULE_SUBNAVS[this.garageState.activeModuleKey]?.parentXmlId
                : null;

        navEntries.forEach((el) => {
            const xmlid = el.getAttribute("data-menu-xmlid");
            const isTarget = Boolean(targetXmlId && xmlid === targetXmlId);
            if (isTarget) {
                el.classList.add("o_garage_tab_active", "active");
            } else if (xmlid) {
                el.classList.remove("o_garage_tab_active", "active");
            }
        });
    },
});
