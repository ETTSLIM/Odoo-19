# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError

# 6 Workshop Specialties Blueprints & Stage-Bound Micro-Tasks (Ported from Garage AI Workshop & happy-faraday)
WORKSHOP_BLUEPRINTS = {
    'carrosserie': {
        'name': "Tôlerie, Carrosserie & Peinture",
        'tag_color': 1,
        'label_ar': "طولاج، كاروسري وصباغة الفران",
        'keywords': ["carrosserie", "tolerie", "tôlerie", "peinture", "accident", "choc", "pare-chocs", "four", "طولاج", "صباغة", "كسيدة", "حادثة"],
        'subtasks': [
            {'stage_seq': 10, 'name': "[Étape 1 • Réception] Constatation des chocs, photos sinistre & ouverture dossier assurance", 'hours': 1.0,
             'description': "Inspection complète de la carrosserie, prise de photos avant travaux et enregistrement du dossier sinistre."},
            {'stage_seq': 20, 'name': "[Étape 2 • Expertise] Passage de l'expert d'assurance, chiffrage devis & accord de prise en charge", 'hours': 2.0,
             'description': "Expertise contradictoire, validation des éléments à remplacer/redresser et accord de prise en charge."},
            {'stage_seq': 30, 'name': "[Étape 3 • Pièces & Teinte] Commande éléments carrosserie (pare-chocs/ailes/optiques) & formulation code peinture", 'hours': 1.5,
             'description': "Réception des pièces de carrosserie et préparation de la teinte constructeur au spectromètre."},
            {'stage_seq': 40, 'name': "[Étape 4A • Tôlerie] Démontage éléments endommagés, redressage tôle / marbre & alignement châssis", 'hours': 5.0,
             'description': "Dépose des éléments touchés, débosselage, redressage sur marbre et alignement des jeux de carrosserie."},
            {'stage_seq': 40, 'name': "[Étape 4B • Préparation] Masticage, ponçage multi-grains, marouflage & application apprêt garnissant", 'hours': 4.0,
             'description': "Préparation de surface, ponçage fin, protection des zones adjacentes et passage en apprêt."},
            {'stage_seq': 40, 'name': "[Étape 4C • Cabine Four] Application peinture au four italien + vernis haute brillance & cuisson thermique", 'hours': 3.5,
             'description': "Peinture en cabine pressurisée (Four Italien) hors poussière, vernis anti-rayures et étuvage à 60°C."},
            {'stage_seq': 40, 'name': "[Étape 4D • Remontage] Remontage pare-chocs, optiques, agrafes & ajustement précis des jeux", 'hours': 2.5,
             'description': "Assemblage final des éléments peints, branchement des faisceaux optiques et radars de recul."},
            {'stage_seq': 50, 'name': "[Étape 5 • Finition] Lustrage, polissage miroir, contrôle teinte sous lumière & test étanchéité", 'hours': 1.5,
             'description': "Polissage de finition, contrôle d'homogénéité de la teinte et vérification du fonctionnement des ouvrants."},
            {'stage_seq': 60, 'name': "[Étape 6 • Livraison] Lavage complet, photos après travaux, Attestation d'immobilisation & facturation", 'hours': 1.0,
             'description': "Nettoyage intérieur/extérieur, édition de l'attestation d'immobilisation pour l'assurance et remise des clés."},
        ],
    },
    'mecanique': {
        'name': "Mécanique Générale & Moteur",
        'tag_color': 4,
        'label_ar': "ميكانيك عامة، محرك وبواط فيتاس",
        'keywords': ["mecanique", "mécanique", "moteur", "distribution", "embrayage", "culasse", "turbo", "injecteur", "boite", "ميكانيك", "موطور", "محرك", "دبرياج", "شين"],
        'subtasks': [
            {'stage_seq': 10, 'name': "[Étape 1 • Diagnostic Méca] Essai préliminaire, écoute bruit moteur, contrôle niveaux & inspection sur pont", 'hours': 1.0,
             'description': "Contrôle mécanique sur pont élévateur, détection des fuites, jeux et bruits anormaux du groupe motopropulseur."},
            {'stage_seq': 20, 'name': "[Étape 2 • Devis Méca] Chiffrage pièces mécaniques (OEM/Adaptable) + main d'œuvre & accord client", 'hours': 0.5,
             'description': "Établissement du devis détaillé (pièces d'origine ou équivalent premium) et validation client."},
            {'stage_seq': 30, 'name': "[Étape 3 • Pièces Moteur] Commande & contrôle conformité pièces (Kit distribution, embrayage, pompe, joints)", 'hours': 1.0,
             'description': "Vérification des références OEM avec le numéro de châssis (VIN) à la réception des pièces."},
            {'stage_seq': 40, 'name': "[Étape 4A • Démontage] Mise sur pont, vidange fluides, dépose organes mécaniques usés & nettoyage portées", 'hours': 3.5,
             'description': "Dépose méthodique des organes défectueux, dégraissage et contrôle des surfaces d'appui."},
            {'stage_seq': 40, 'name': "[Étape 4B • Montage & Calage] Pose pièces neuves, calage distribution/moteur & serrage au couple constructeur", 'hours': 4.5,
             'description': "Installation des pièces neuves avec piges de calage et clé dynamométrique selon les préconisations constructeur."},
            {'stage_seq': 40, 'name': "[Étape 4C • Mise à Niveau] Remplissage huiles (moteur/boîte), purge circuit refroidissement & hydraulique", 'hours': 1.0,
             'description': "Remplissage des fluides homologués et purge complète de l'air dans les circuits."},
            {'stage_seq': 50, 'name': "[Étape 5 • Essai Routier] Test dynamique sur route en charge, contrôle température 90°C, zéro fuite & scan OBD", 'hours': 1.0,
             'description': "Essai routier complet, contrôle de la montée en température, passage des rapports et absence de suintement."},
            {'stage_seq': 60, 'name': "[Étape 6 • Livraison] Nettoyage compartiment moteur, présentation anciennes pièces au client & facturation", 'hours': 0.5,
             'description': "Lavage véhicule, mise à disposition des pièces remplacées pour transparence totale et remise des clés."},
        ],
    },
    'electricite': {
        'name': "Électricité & Diagnostic OBD",
        'tag_color': 3,
        'label_ar': "كهرباء السيارات والديانوستيك الإلكتروني (لاڤاليز)",
        'keywords': ["electricite", "électricité", "obd", "valise", "calculateur", "ecu", "capteur", "alternateur", "demarreur", "batterie", "abs", "airbag", "ضو", "كهرباء", "ديانوستيك", "لاڤاليز", "كابتور"],
        'subtasks': [
            {'stage_seq': 10, 'name': "[Étape 1 • Scan Valise OBD] Lecture codes défauts (DTC) multi-calculateurs, test batterie/alternateur & analyse symptômes", 'hours': 1.0,
             'description': "Diagnostic électronique complet à la valise constructeur, relevé des trames figées et test du circuit de charge."},
            {'stage_seq': 20, 'name': "[Étape 2 • Devis Élec] Rapport diagnostic électronique détaillé, chiffrage capteurs/ECU/faisceau & accord client", 'hours': 0.5,
             'description': "Chiffrage des composants électroniques et de la main d'œuvre de recherche de panne / programmation."},
            {'stage_seq': 30, 'name': "[Étape 3 • Composants Élec] Approvisionnement composants (Capteurs ABS/ESP, alternateur, démarreur, calculateur, relais)", 'hours': 1.0,
             'description': "Commande des pièces électriques/électroniques avec contrôle strict des références Bosch/Valeo/Continental."},
            {'stage_seq': 40, 'name': "[Étape 4A • Faisceau & Capteurs] Test continuité au multimètre/oscilloscope, réparation faisceau & pose composants", 'hours': 2.5,
             'description': "Contrôle d'isolement et continuité des lignes CAN/LIN, réfection du câblage et remplacement des capteurs/actuateurs."},
            {'stage_seq': 40, 'name': "[Étape 4B • Programmation ECU] Télécodage, adaptation capteurs, mise à jour calculateur (ECU/BSI) & effacement DTC", 'hours': 1.5,
             'description': "Apprentissage des nouveaux composants, calibrage électronique et réinitialisation des calculateurs."},
            {'stage_seq': 50, 'name': "[Étape 5 • Scan Final 0 Défaut] Re-scan complet zéro défaut (0 DTC), test charge électrique & extinction voyants tableau de bord", 'hours': 0.75,
             'description': "Validation finale après essai routier : aucun code défaut récurrent et tous les voyants d'alerte éteints."},
            {'stage_seq': 60, 'name': "[Étape 6 • Livraison] Impression rapport de diagnostic avant/après, lavage & remise véhicule au client", 'hours': 0.5,
             'description': "Remise du rapport de scan électronique imprimé au client avec la facture."},
        ],
    },
    'entretien': {
        'name': "Entretien Rapide, Vidange & Freinage",
        'tag_color': 10,
        'label_ar': "السيرفيس السريع، الڤيدانج والفراناج",
        'keywords': ["entretien", "vidange", "filtre", "frein", "plaquette", "disque", "huile", "service", "revision", "révision", "فيدانج", "ڤيدانج", "فران", "فيلتر", "زيت"],
        'subtasks': [
            {'stage_seq': 10, 'name': "[Étape 1 • Check-up 30 Points] Contrôle visuel rapide : usure plaquettes/disques, état filtres, courroies, pneus & éclairage", 'hours': 0.5,
             'description': "Bilan de sécurité en 30 points dès l'entrée du véhicule sur le pont de service rapide."},
            {'stage_seq': 20, 'name': "[Étape 2 • Forfait Entretien] Validation forfait vidange (viscosité huile 5W30/5W40, 4 filtres, freinage) avec le client", 'hours': 0.25,
             'description': "Confirmation de la norme d'huile constructeur et des éléments d'usure à remplacer."},
            {'stage_seq': 30, 'name': "[Étape 3 • Sortie Magasin] Préparation kit filtres (huile, air, gasoil, habitacle), bidon huile homologuée & plaquettes/disques", 'hours': 0.25,
             'description': "Sortie immédiate du stock magasin des consommables et pièces de freinage."},
            {'stage_seq': 40, 'name': "[Étape 4A • Vidange & 4 Filtres] Vidange huile moteur à chaud, joint bouchon neuf, remplacement filtres huile/air/gasoil/habitacle", 'hours': 1.0,
             'description': "Écoulement complet, nettoyage du bol de filtre, pose du joint cuivre neuf et remplissage à la jauge exacte."},
            {'stage_seq': 40, 'name': "[Étape 4B • Service Freinage] Remplacement plaquettes & disques de frein, nettoyage étriers & purge liquide de frein DOT4", 'hours': 1.25,
             'description': "Dépoussiérage des étriers, graissage des coulisseaux, pose des disques/plaquettes et test d'humidité du liquide de frein."},
            {'stage_seq': 50, 'name': "[Étape 5 • Reset & Test Freins] Remise à zéro indicateur maintenance (Reset Service), appoint lave-glace & test freinage", 'hours': 0.5,
             'description': "Réinitialisation du compteur d'entretien au tableau de bord, rodage initial des freins et contrôle pression pneus."},
            {'stage_seq': 60, 'name': "[Étape 6 • Livraison Express] Pose étiquette kilométrage prochaine vidange, coup d'aspirateur & livraison rapide", 'hours': 0.25,
             'description': "Accrochage de la carte d'entretien avec date et kilométrage de la prochaine révision."},
        ],
    },
    'climatisation': {
        'name': "Climatisation & Refroidissement",
        'tag_color': 8,
        'label_ar': "الكليماتيزاسيون وتبريد المحرك",
        'keywords': ["clim", "climatisation", "gaz", "compresseur", "condenseur", "radiateur", "refroidissement", "froid", "كليم", "كليماتيزاسيون", "التبريد", "رادياتور", "كاز"],
        'subtasks': [
            {'stage_seq': 10, 'name': "[Étape 1 • Diagnostic Clim] Relevé température aérateurs, contrôle pressions BP/HP & détection fuite traceur UV / azote", 'hours': 0.75,
             'description': "Branchement de la station de climatisation, lecture des pressions basse/haute et recherche de fuite sous lampe UV."},
            {'stage_seq': 20, 'name': "[Étape 2 • Devis Clim] Chiffrage recharge gaz (R134a / R1234yf), condenseur, compresseur ou radiateur & accord client", 'hours': 0.5,
             'description': "Devis détaillé selon le type de fluide frigorigène et les organes d'étanchéité à remplacer."},
            {'stage_seq': 30, 'name': "[Étape 3 • Pièces & Gaz] Réception condenseur/compresseur, joints toriques HNBR, filtre habitacle charbon actif & gaz", 'hours': 0.75,
             'description': "Préparation des joints spécifiques climatisation, bouteille déshydratante et filtre d'habitacle."},
            {'stage_seq': 40, 'name': "[Étape 4A • Étanchéité & Vide] Remplacement organes clim défectueux, remplacement joints & tirage au vide profond (45 min)", 'hours': 1.5,
             'description': "Déshydratation complète du circuit frigorifique par tirage au vide prolongé et test de maintien sous vide."},
            {'stage_seq': 40, 'name': "[Étape 4B • Charge & Traitement] Injection gaz réfrigérant au gramme près + huile PAG & désinfection antibactérienne habitacle", 'hours': 1.0,
             'description': "Charge automatique selon la plaque constructeur et traitement purificateur des conduits de ventilation."},
            {'stage_seq': 50, 'name': "[Étape 5 • Test Rendement Froid] Vérification froid (6°C–8°C aux buses), déclenchement motoventilateur & test étanchéité", 'hours': 0.5,
             'description': "Contrôle thermométrique en sortie d'aérateur central et vérification de l'évacuation des condensats."},
            {'stage_seq': 60, 'name': "[Étape 6 • Livraison] Remise ticket imprimé de la station de climatisation & conseils d'utilisation au client", 'hours': 0.25,
             'description': "Remise du rapport de charge (quantité de gaz/huile injectée et test de vide réussi)."},
        ],
    },
    'pneumatique': {
        'name': "Pneumatiques, Suspension & Géométrie 3D",
        'tag_color': 6,
        'label_ar': "الرويض، السوسبانسيون والباراليليزم 3D",
        'keywords': ["pneu", "pneumatique", "geometrie", "géométrie", "parallelisme", "parallélisme", "equilibrage", "équilibrage", "amortisseur", "rotule", "suspension", "رويض", "بنوات", "باراليليزم", "ليكيليبراج", "أمورتيسور"],
        'subtasks': [
            {'stage_seq': 10, 'name': "[Étape 1 • Diagnostic Train Roulant] Mesure profondeur sculpture pneus, contrôle jeu rotules/triangles/amortisseurs & ripage", 'hours': 0.5,
             'description': "Inspection de l'usure irrégulière des pneus et vérification des jeux dans les éléments de direction et suspension."},
            {'stage_seq': 20, 'name': "[Étape 2 • Devis Pneus & Train] Choix manufacturier pneus, chiffrage organes suspension/direction & validation client", 'hours': 0.25,
             'description': "Proposition des pneumatiques adaptés (indice de charge/vitesse) et pièces de train roulant."},
            {'stage_seq': 30, 'name': "[Étape 3 • Pneus & Organes] Réception pneumatiques neufs, valves haute pression/TPMS, rotules, biellettes ou amortisseurs", 'hours': 0.5,
             'description': "Contrôle DOT des pneumatiques neufs et préparation des capteurs de pression TPMS."},
            {'stage_seq': 40, 'name': "[Étape 4A • Suspension & Montage] Remplacement amortisseurs/rotules, montage pneus neufs, valves & équilibrage dynamique", 'hours': 1.75,
             'description': "Montage sans levier, remplacement des valves et équilibrage électronique au gramme près sur les 4 roues."},
            {'stage_seq': 40, 'name': "[Étape 4B • Géométrie Laser 3D] Réglage parallélisme, carrossage et chasse au banc laser 3D (Trains avant & arrière)", 'hours': 1.0,
             'description': "Alignement 3D haute précision selon les angles constructeur avec blocage du volant au point milieu."},
            {'stage_seq': 50, 'name': "[Étape 5 • Essai Tenue de Route] Test routier : alignement volant droit, absence de tirage/vibrations & tarage pression TPMS", 'hours': 0.5,
             'description': "Vérification du comportement routier, réinitialisation du système TPMS et serrage des roues à la clé dynamométrique."},
            {'stage_seq': 60, 'name': "[Étape 6 • Livraison] Remise rapport géométrie 3D avant/après (valeurs en vert) & livraison du véhicule", 'hours': 0.25,
             'description': "Remise de la fiche imprimée du banc de géométrie 3D au client."},
        ],
    },
}

SPECIALTY_BLUEPRINTS = WORKSHOP_BLUEPRINTS


def _build_stage2_subtask_defs(is_assurance=False):
    """Génère les micro-tâches canoniques de l'Étape 2 (Devis & Accord) :
    - 2A (Devis) & 2B (Accord Client) pour dossier normal
    - 2A, 2B et 2C (Accord Expert) pour dossier Assurance/Sinistre.
    """
    stage2_defs = [
        {
            'stage_seq': 20,
            'name': "[Étape 2A • Devis] إعداد وتقييم الدوڤي (Chiffrage & Établissement du Devis)",
            'hours': 0.5,
            'description': "Chiffrage des pièces de rechange et main d'œuvre, établissement du devis détaillé pour le véhicule.",
        },
        {
            'stage_seq': 20,
            'name': "[Étape 2B • Accord Client] موافقة الزبون على الدوڤي والإصلاح (Accord Client)",
            'hours': 0.5,
            'description': "Validation formelle du devis par le client et autorisation de lancement des travaux.",
        },
    ]
    if is_assurance:
        stage2_defs.append({
            'stage_seq': 20,
            'name': "[Étape 2C • Accord Expert] معاينة وموافقة الخبير والتأمين على الدوڤي (Accord Expert / Devis)",
            'hours': 1.5,
            'description': "Passage de l'expert automobile, validation contradictoire et obtention du Bon d'Accord de prise en charge.",
        })
    return stage2_defs


class GarageWorkshopStage(models.Model):
    _name = 'garage.workshop.stage'
    _description = "Étape du Workflow Atelier Automobile (7 Étapes Canoniques)"
    _order = 'sequence, id'

    name = fields.Char(string="Nom de l'Étape", required=True, translate=True)
    sequence = fields.Integer(string="Séquence", default=10, index=True)
    code = fields.Char(string="Code Interne", required=True, index=True)
    mapped_state = fields.Selection([
        ('draft', 'Réception'),
        ('diagnostic', 'Diagnostic'),
        ('quoted', 'Devis / Attente Accord'),
        ('in_repair', 'En Réparation Atelier'),
        ('qc', 'Contrôle Qualité'),
        ('ready', 'Prêt pour Livraison'),
        ('delivered', 'Restitué / Clôturé'),
        ('cancel', 'Annulé'),
    ], string="État Odoo Associé", default='diagnostic', required=True)

    responsible_role = fields.Selection([
        ('receptionist', "Agent d'Accueil / Réceptionniste"),
        ('chef_atelier', "Chef d'Atelier"),
        ('mechanic', "Mécaniciens & Techniciens"),
        ('magasinier', "Magasinier Stock & Chiffrage"),
        ('qc_inspector', "Contrôleur Qualité"),
        ('manager', "Direction / Gérant"),
    ], string="Rôle Responsable de l'Étape", default='chef_atelier', required=True)

    operator_ids = fields.Many2many(
        'garage.workshop.operator', 'garage_stage_operator_rel',
        'stage_id', 'operator_id',
        string="Opérateurs Autorisés (Tablette)"
    )

    fold = fields.Boolean(string="Replié en Vue Kanban", default=False)
    description = fields.Text(string="Description / Instructions pour l'équipe")
    auto_whatsapp_template = fields.Text(
        string="Modèle de Notification WhatsApp Client",
        help="Texte transmis au client par WhatsApp lors de l'entrée dans cette étape."
    )

    @api.model
    def _register_hook(self):
        super()._register_hook()
        try:
            STAGE_NAMES_MAP = {
                'reception': "Réception",
                'devis': "Devis",
                'pieces': "Pièces",
                'travaux': "Travaux",
                'controle': "Contrôle",
                'prete': "Prêt",
                'livree': "Livré",
            }
            for code, short_name in STAGE_NAMES_MAP.items():
                stage = self.search([('code', '=', code)], limit=1)
                if stage and stage.name != short_name:
                    stage.name = short_name

            sel = self.env['ir.model.fields.selection'].search([('field_id.model', '=', 'repair.order'), ('value', '=', 'draft')])
            if sel:
                sel.with_context(lang='fr_FR').name = "Brouillon"
        except Exception:
            pass


class GarageWorkshopOperator(models.Model):
    _name = 'garage.workshop.operator'
    _description = "Opérateur / Intervenant Atelier (Compte Tablette Partagé avec Code PIN)"
    _order = 'name'

    name = fields.Char(string="Nom & Prénom de l'Opérateur", required=True)
    pin_code = fields.Char(string="Code PIN Tablette (4 Chiffres)", required=True, size=4,
                           help="Code PIN personnel pour pointer et valider les tâches sur la tablette partagée de l'atelier.")
    role = fields.Selection([
        ('receptionist', "Agent d'Accueil / Réceptionniste"),
        ('chef_atelier', "Chef d'Atelier"),
        ('mechanic', "Mécanicien Moteur / Boîte"),
        ('bodywork', "Tôlier / Peintre en Cabine"),
        ('electrician', "Électricien & Diagnostic OBD"),
        ('magasinier', "Magasinier / Gestionnaire Pièces"),
        ('qc_inspector', "Contrôleur Qualité"),
        ('manager', "Gérant / Administrateur"),
    ], string="Rôle Atelier", default='mechanic', required=True)

    specialty = fields.Selection([
        ('all', "Toutes Spécialités"),
        ('carrosserie', "🎨 Tôlerie, Carrosserie & Peinture"),
        ('mecanique', "🔧 Mécanique Générale & Moteur"),
        ('electricite', "⚡ Électricité & Diagnostic OBD"),
        ('entretien', "🛢️ Entretien Rapide & Freinage"),
        ('climatisation', "❄️ Climatisation & Refroidissement"),
        ('pneumatique', "🛞 Pneumatiques & Géométrie 3D"),
    ], string="Spécialité Principale", default='all', required=True)

    user_id = fields.Many2one('res.users', string="Utilisateur Odoo Lié (Optionnel)")
    allowed_stage_ids = fields.Many2many(
        'garage.workshop.stage', 'garage_stage_operator_rel',
        'operator_id', 'stage_id',
        string="Étapes Autorisées"
    )
    active = fields.Boolean(string="Actif", default=True)

    _pin_code_uniq = models.Constraint(
        'unique (pin_code)',
        "Le code PIN doit être unique pour chaque opérateur d'atelier !",
    )

    @api.constrains('pin_code')
    def _check_pin_code(self):
        for op in self:
            if not op.pin_code or not op.pin_code.isdigit() or len(op.pin_code) != 4:
                raise ValidationError(_("Le code PIN de l'opérateur '%s' doit comporter exactement 4 chiffres (ex: 1234).", op.name))

    def verify_pin(self, pin_code, target_stage_id=False):
        """Vérifie le code PIN et retourne l'opérateur s'il est valide et autorisé."""
        self.ensure_one()
        if not pin_code or str(pin_code).strip() != str(self.pin_code).strip():
            return False
        if target_stage_id and self.allowed_stage_ids and target_stage_id not in self.allowed_stage_ids.ids:
            if self.role not in ('chef_atelier', 'manager'):
                return False
        return True


class GarageReceptionTask(models.Model):
    _name = 'garage.reception.task'
    _description = "Micro-Tâche / Checklist d'Atelier par Étape"
    _order = 'stage_sequence, sequence, id'

    reception_id = fields.Many2one('garage.reception', string="Fiche Réception", required=True, ondelete='cascade')
    stage_id = fields.Many2one('garage.workshop.stage', string="Grande Étape", required=True, index=True)
    stage_sequence = fields.Integer(related='stage_id.sequence', string="Séquence Étape", store=True, index=True)
    sequence = fields.Integer(string="Ordre", default=10)

    name = fields.Char(string="Titre", required=True)
    description = fields.Text(string="Instructions Pratiques")
    planned_hours = fields.Float(string="Durée Estimée", default=0.5)

    specialty = fields.Selection(related='reception_id.specialty', string="Atelier / Spécialité", store=True, readonly=True)
    is_ai_dynamic = fields.Boolean(string="Tâche Dynamique IA (مخصصة)", default=False, readonly=True)
    diagnostic_task_id = fields.Many2one('garage.diagnostic.log.task', string="Ligne Diagnostic Origine", ondelete='set null')
    damage_item_id = fields.Many2one('garage.damage.item', string="Élément Endommagé Associé", ondelete='set null')
    is_hidden_damage = fields.Boolean(string="Dégât Masqué (Démontage)", default=False)

    state = fields.Selection([
        ('04_waiting_normal', 'En attente'),
        ('01_in_progress', 'En cours'),
        ('1_done', 'Terminé'),
    ], string="État", default='04_waiting_normal', required=True, index=True)

    is_done = fields.Boolean(string="Terminé", default=False, index=True)
    assigned_user_id = fields.Many2one('res.users', string="Assigné")
    completed_by_operator_id = fields.Many2one('garage.workshop.operator', string="Assignés / Réalisé par")
    completed_date = fields.Datetime(string="Date Réalisation")

    def _check_workshop_role_permission(self, operator=False):
        """Vérifie que seul le Mécanicien / Chef d'Atelier ou le Gérant peut modifier les micro-tâches des Étapes 4 et 5."""
        if self.env.context.get('auto_workflow_sync'):
            return True
        user = self.env.user
        if user._is_superuser() or user.has_group('garage_repair_core.group_garage_manager') or user.has_group('garage_repair_core.group_garage_mechanic'):
            return True
        if operator and operator.role in ('mechanic', 'bodywork', 'electrician', 'chef_atelier', 'qc_inspector', 'manager'):
            return True
        raise UserError(_(
            "⛔ ACCÈS VERROUILLÉ :\n\n"
            "Seuls le Mécanicien / Chef d'Atelier ou le Gérant sont habilités à modifier ou valider les sous-tâches d'atelier (Étape 4 & 5)."
        ))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'state' in vals and 'is_done' not in vals:
                vals['is_done'] = (vals['state'] == '1_done')
            elif 'is_done' in vals and 'state' not in vals:
                vals['state'] = '1_done' if vals['is_done'] else '04_waiting_normal'
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals or 'is_done' in vals:
            if 'state' in vals and 'is_done' not in vals:
                vals['is_done'] = (vals['state'] == '1_done')
            elif 'is_done' in vals and 'state' not in vals:
                vals['state'] = '1_done' if vals['is_done'] else '04_waiting_normal'

            for task in self:
                if task.stage_sequence in (40, 50):
                    task._check_workshop_role_permission()

        return super().write(vals)

    def action_toggle_state(self, operator=False, target_state=None):
        """Bascule ou applique l'état de la micro-tâche avec contrôle de rôle, progression séquentielle et avancement d'étape."""
        for task in self:
            if task.stage_sequence in (40, 50):
                task._check_workshop_role_permission(operator=operator)

            # Si target_state est explicite ('1_done' ou '04_waiting_normal'), l'appliquer de façon idempotente
            if target_state:
                turn_done = (target_state in ('1_done', 'done'))
            else:
                turn_done = (task.state != '1_done')

            if not turn_done:
                # Revenir en attente
                task.with_context(auto_workflow_sync=True).write({
                    'state': '04_waiting_normal',
                    'is_done': False,
                    'completed_date': False,
                    'completed_by_operator_id': False,
                })
            else:
                # Marquer comme terminé
                vals = {
                    'state': '1_done',
                    'is_done': True,
                    'completed_date': fields.Datetime.now(),
                }
                if operator:
                    vals['completed_by_operator_id'] = operator.id
                task.with_context(auto_workflow_sync=True).write(vals)

                # Progression séquentielle : activer la prochaine micro-tâche en attente dans la même étape
                next_task = self.search([
                    ('reception_id', '=', task.reception_id.id),
                    ('stage_id', '=', task.stage_id.id),
                    ('state', '=', '04_waiting_normal'),
                    ('id', '!=', task.id),
                ], order='sequence asc, id asc', limit=1)
                if next_task:
                    next_task.with_context(auto_workflow_sync=True).write({'state': '01_in_progress'})

                # Si c'est l'Accord Expert 2C, synchroniser le statut expertise de la réception et du dossier sinistre
                if any(kw in task.name.lower() for kw in ("2c", "accord expert", "موافقة الخبير")):
                    task.reception_id.with_context(auto_workflow_sync=True).write({'statut_expertise': 'accord_valide'})
                    claim = task.reception_id.claim_id
                    if claim and claim.state in ('draft', 'expert_assigned', 'devis_sent'):
                        try:
                            claim.with_context(auto_workflow_sync=True, bypass_interlock=True).action_approve_accord()
                            if claim.client_accord_status != 'approved':
                                claim.with_context(auto_workflow_sync=True).write({'client_accord_status': 'approved'})
                        except Exception:
                            claim.with_context(auto_workflow_sync=True).write({
                                'state': 'accord_approved',
                                'client_accord_status': 'approved',
                            })

                # Vérifier si toutes les micro-tâches de l'étape sont terminées pour avancement d'étape
                if task.reception_id:
                    task.reception_id._check_and_auto_advance_stage(task.stage_id, operator=operator)

        return True

    def toggle_task_done(self, operator=False):
        """Alias rétro-compatible pour la tablette et les flux existants."""
        return self.action_toggle_state(operator=operator)

    def action_open_task_detail(self):
        """Ouvre la vue modale détaillée de la sous-tâche."""
        self.ensure_one()
        return {
            'name': _("Détail de la Sous-tâche : %s", self.name),
            'type': 'ir.actions.act_window',
            'res_model': 'garage.reception.task',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
