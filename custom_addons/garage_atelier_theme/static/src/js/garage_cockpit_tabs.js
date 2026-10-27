/** @odoo-module **/

import { Notebook } from "@web/core/notebook/notebook";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

patch(Notebook.prototype, {
    setup() {
        super.setup(...arguments);
        try {
            this.notification = useService("notification");
        } catch {
            this.notification = null;
        }
    },
    computeActivePage(defaultPage, activateDefault) {
        if (this.pages && this.pages.length) {
            const pages = this.pages.filter((e) => e[1].isVisible).map((e) => e[0]);
            // Auto-focus de l'onglet actif correspondant au stade du cycle de vie véhicule
            const isGarageCockpit = pages.includes("tab_intake") && pages.some((p) => typeof p === "string" && p.endsWith("_active"));
            if (isGarageCockpit && (!this.state || !this.state.currentPage)) {
                const stageTabs = [
                    "tab_facturation_active",
                    "tab_travaux_active",
                    "tab_pieces_active",
                    "tab_devis_active",
                ];
                for (const sTab of stageTabs) {
                    if (pages.includes(sTab)) {
                        return sTab;
                    }
                }
            }
        }
        return super.computeActivePage(defaultPage, activateDefault);
    },
    async activatePage(pageIndex) {
        const page = this.pages.find((e) => e[0] === pageIndex);
        const title = page && page[1] && (page[1].title || page[1].name || "");
        if (typeof title === "string" && title.includes("🔒")) {
            if (this.notification) {
                this.notification.add(
                    _t("Cette étape n'est pas encore prête pour ce véhicule."),
                    {
                        type: "info",
                        title: _t("Étape Non Atteinte"),
                        sticky: false,
                    }
                );
            }
            return;
        }
        return super.activatePage(pageIndex);
    },
});
