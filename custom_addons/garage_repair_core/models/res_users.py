# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command

class ResUsers(models.Model):
    _inherit = 'res.users'

    garage_role_preset = fields.Selection([
        ('mechanic', "Mécanicien / Opérateur Atelier"),
        ('storekeeper', "Magasinier / Gestionnaire Pièces"),
        ('receptionist', "Assistante / Accueil"),
        ('manager', "Gérant / Administrateur"),
        ('custom', "Profil Sur-Mesure"),
    ], string="Profil Métier Garage", compute='_compute_garage_role_preset', inverse='_inverse_garage_role_preset', store=True, default='custom')

    garage_can_workshop = fields.Boolean(
        string="Atelier & Entrées",
        compute='_compute_garage_modules',
        inverse='_inverse_garage_modules',
        store=True,
        help="Accès au Module 1 : Réceptions véhicules, ordres de travaux et tableau atelier"
    )
    garage_can_insurance = fields.Boolean(
        string="Sinistres & Assurances",
        compute='_compute_garage_modules',
        inverse='_inverse_garage_modules',
        store=True,
        help="Accès au Module 2 : Dossiers sinistres, chiffrage d'expertise et avenants d'assurance"
    )
    garage_can_stock = fields.Boolean(
        string="Pièces, Stock & BL",
        compute='_compute_garage_modules',
        inverse='_inverse_garage_modules',
        store=True,
        help="Accès au Module 3 : État du stock magasin (rayon), catalogue et BL d'achat"
    )
    garage_can_finance = fields.Boolean(
        string="Caisse Guichet & Factures Fiscales",
        compute='_compute_garage_modules',
        inverse='_inverse_garage_modules',
        store=True,
        help="Accès au Module 4 : Journal d'encaissements, factures de vente officielles TVA 20%"
    )
    garage_can_directory = fields.Boolean(
        string="Parc Véhicules & Annuaire",
        compute='_compute_garage_modules',
        inverse='_inverse_garage_modules',
        store=True,
        help="Accès au Module 5 : Répertoire du parc véhicules, clients, assureurs et fournisseurs"
    )

    @api.depends('group_ids')
    def _compute_garage_modules(self):
        w_grp = self.env.ref('garage_repair_core.group_garage_access_workshop', False)
        i_grp = self.env.ref('garage_repair_core.group_garage_access_insurance', False)
        s_grp = self.env.ref('garage_repair_core.group_garage_access_stock', False)
        f_grp = self.env.ref('garage_repair_core.group_garage_access_finance', False)
        d_grp = self.env.ref('garage_repair_core.group_garage_access_directory', False)
        for user in self:
            user.garage_can_workshop = bool(w_grp and (w_grp in user.group_ids or w_grp in user.all_group_ids))
            user.garage_can_insurance = bool(i_grp and (i_grp in user.group_ids or i_grp in user.all_group_ids))
            user.garage_can_stock = bool(s_grp and (s_grp in user.group_ids or s_grp in user.all_group_ids))
            user.garage_can_finance = bool(f_grp and (f_grp in user.group_ids or f_grp in user.all_group_ids))
            user.garage_can_directory = bool(d_grp and (d_grp in user.group_ids or d_grp in user.all_group_ids))

    def _inverse_garage_modules(self):
        w_grp = self.env.ref('garage_repair_core.group_garage_access_workshop', False)
        i_grp = self.env.ref('garage_repair_core.group_garage_access_insurance', False)
        s_grp = self.env.ref('garage_repair_core.group_garage_access_stock', False)
        f_grp = self.env.ref('garage_repair_core.group_garage_access_finance', False)
        d_grp = self.env.ref('garage_repair_core.group_garage_access_directory', False)

        for user in self:
            cmds = []
            mapping = [
                (user.garage_can_workshop, w_grp),
                (user.garage_can_insurance, i_grp),
                (user.garage_can_stock, s_grp),
                (user.garage_can_finance, f_grp),
                (user.garage_can_directory, d_grp),
            ]
            for can, grp in mapping:
                if not grp:
                    continue
                if can and grp not in user.group_ids:
                    cmds.append(Command.link(grp.id))
                elif not can and grp in user.group_ids:
                    cmds.append(Command.unlink(grp.id))
            if cmds:
                user.write({'group_ids': cmds})

    @api.depends('group_ids')
    def _compute_garage_role_preset(self):
        m_grp = self.env.ref('garage_repair_core.group_garage_manager', False)
        r_grp = self.env.ref('garage_repair_core.group_garage_receptionist', False)
        s_grp = self.env.ref('garage_repair_core.group_garage_storekeeper', False)
        w_grp = self.env.ref('garage_repair_core.group_garage_mechanic', False)

        for user in self:
            if m_grp and (m_grp in user.group_ids or m_grp in user.all_group_ids):
                user.garage_role_preset = 'manager'
            elif r_grp and (r_grp in user.group_ids or r_grp in user.all_group_ids):
                user.garage_role_preset = 'receptionist'
            elif s_grp and (s_grp in user.group_ids or s_grp in user.all_group_ids):
                user.garage_role_preset = 'storekeeper'
            elif w_grp and (w_grp in user.group_ids or w_grp in user.all_group_ids):
                user.garage_role_preset = 'mechanic'
            else:
                user.garage_role_preset = 'custom'

    def _inverse_garage_role_preset(self):
        m_grp = self.env.ref('garage_repair_core.group_garage_manager', False)
        r_grp = self.env.ref('garage_repair_core.group_garage_receptionist', False)
        s_grp = self.env.ref('garage_repair_core.group_garage_storekeeper', False)
        w_grp = self.env.ref('garage_repair_core.group_garage_mechanic', False)

        for user in self:
            preset = user.garage_role_preset
            if preset == 'custom':
                continue
            cmds = []
            role_groups = [g for g in [m_grp, r_grp, s_grp, w_grp] if g]
            for g in role_groups:
                if g in user.group_ids:
                    cmds.append(Command.unlink(g.id))

            target = None
            if preset == 'mechanic':
                target = w_grp
            elif preset == 'storekeeper':
                target = s_grp
            elif preset == 'receptionist':
                target = r_grp
            elif preset == 'manager':
                target = m_grp

            if target:
                cmds.append(Command.link(target.id))

            if cmds:
                user.write({'group_ids': cmds})

    @api.onchange('garage_role_preset')
    def _onchange_garage_role_preset(self):
        if self.garage_role_preset == 'mechanic':
            self.garage_can_workshop = True
            self.garage_can_insurance = False
            self.garage_can_stock = False
            self.garage_can_finance = False
            self.garage_can_directory = False
        elif self.garage_role_preset == 'storekeeper':
            self.garage_can_workshop = True
            self.garage_can_insurance = False
            self.garage_can_stock = True
            self.garage_can_finance = False
            self.garage_can_directory = False
        elif self.garage_role_preset == 'receptionist':
            self.garage_can_workshop = True
            self.garage_can_insurance = True
            self.garage_can_stock = True
            self.garage_can_finance = True
            self.garage_can_directory = True
        elif self.garage_role_preset == 'manager':
            self.garage_can_workshop = True
            self.garage_can_insurance = True
            self.garage_can_stock = True
            self.garage_can_finance = True
            self.garage_can_directory = True
