# -*- coding: utf-8 -*-
{
    'name': 'Garage Pro Atelier UX - Thème Token-Based & Design System',
    'version': '19.0.2.0.0',
    'category': 'Themes/Backend',
    'summary': 'Design System Token-Based, Palette Titanium & Racing Blue, Navigation Monochrome & Composants Atelier',
    'description': """
Thème Haute Précision pour Atelier & Garage Automobile (Odoo 19)
================================================================
Design System basé sur des tokens sémantiques réutilisables:
* Tokens compilés (Primitifs, Sémantiques, Mapping Odoo 19)
* Injection en tête de bundle (Zéro fuite violette #71639e)
* Variables CSS runtime (:root) pour composants et mode tactile
* Barre de navigation sobre B2B avec icônes filaires monochromes
* Badge plaque d'immatriculation marocaine (.o_garage_plate)
* Bandeau Hero Véhicule & Cartes KPI financiers
* Barres d'état statut à une seule ligne avec étape active contrastée
    """,
    'author': 'Senior Odoo Architect',
    'license': 'LGPL-3',
    'depends': [
        'web',
        'garage_repair_core',
    ],
    'data': [],
    'assets': {
        'web._assets_primary_variables': [
            ('prepend', 'garage_atelier_theme/static/src/tokens/_odoo_mapping.scss'),
            ('prepend', 'garage_atelier_theme/static/src/tokens/_semantic.scss'),
            ('prepend', 'garage_atelier_theme/static/src/tokens/_primitives.scss'),
        ],
        'web.assets_backend': [
            'garage_atelier_theme/static/src/scss/root_vars.scss',
            'garage_atelier_theme/static/src/scss/navbar.scss',
            'garage_atelier_theme/static/src/scss/components.scss',
            'garage_atelier_theme/static/src/scss/views.scss',
            'garage_atelier_theme/static/src/js/navbar_subnav.js',
            'garage_atelier_theme/static/src/js/garage_cockpit_tabs.js',
            'garage_atelier_theme/static/src/xml/navbar_subnav.xml',
        ],
        'web.assets_frontend': [
            'garage_atelier_theme/static/src/scss/root_vars.scss',
            'garage_atelier_theme/static/src/scss/components.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
