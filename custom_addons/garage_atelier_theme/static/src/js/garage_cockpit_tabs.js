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
