# -*- coding: utf-8 -*-
"""Mon Recours CI — configuration centrale.

REGLE STRUCTURELLE : ce fichier ne contient AUCUNE regle de droit.
Il contient des chemins, des enumerations de statut et le registre des sources
officielles (URLs + roles). Un article, un delai ou une procedure n'a rien a
faire ici : ils n'existent que dans la base de references, avec leurs
metadonnees et leur etat de verification.

Version : voir VERSION.
"""

from pathlib import Path

VERSION = "0.1.0"
NOM_AGENT = "Mon Recours CI"
NOM_TECHNIQUE = "agent-juriste-ci"
PAYS = "Cote d'Ivoire"
LANGUE = "fr"

# --------------------------------------------------------------------------
# Chemins
# --------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
DOSSIERS_DIR = BASE_DIR / "DOSSIERS"
KNOWLEDGE_DIR = BASE_DIR / "KNOWLEDGE"
WORKFLOWS_DIR = BASE_DIR / "WORKFLOWS"
TESTS_DIR = BASE_DIR / "tests"
JOURNAL_DIR = BASE_DIR / "journal"

CHEMIN_DB = KNOWLEDGE_DIR / "corpus_juridique.sqlite3"
CHEMIN_VERIFICATIONS_SOURCES = KNOWLEDGE_DIR / "verifications_sources.json"
CHEMIN_JOURNAL_TECHNIQUE = JOURNAL_DIR / "technique.log"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36"
)

# --------------------------------------------------------------------------
# Enumerations de statut
# --------------------------------------------------------------------------
# Etat d'un texte dans la base. Aucune couche ne promeut un statut :
# seule une verification documentee (URL + empreinte + date) le fait.
STATUTS_VERIFICATION = (
    "VERIFIE",               # texte lu, source officielle, empreinte enregistree
    "PARTIELLEMENT_VERIFIE",  # source accessible mais texte/partie non confirme
    "NON_VERIFIE",           # reference saisie, pas encore verifiee (defaut)
    "NON_CONFIRME",          # source injoignable ou contradictoire
    "OBSOLETE",              # remplace, abroge ou modifie connu
)

# Etat d'un fait dans un dossier. Un fait DECLARE n'est jamais promu DOCUMENTE
# sans piece produite par l'utilisateur.
ETATS_FAIT = (
    "DECLARE_PAR_L_UTILISATEUR",
    "DOCUMENTE",       # piece fournie : nom + empreinte SHA-256 enregistres
    "A_CONFIRMER",     # le recit est ambigu, une piece trancherait
    "MANQUANT",        # information absente : nommee comme telle, jamais supposee
)

# Nature d'une etape du plan d'action.
NATURES_ETAPE = ("automatisable", "manuel", "orientation_humaine")

# Niveaux d'urgence.
NIVEAUX_URGENCE = ("CRITIQUE", "ELEVEE", "NORMALE")

# --------------------------------------------------------------------------
# Domaines juridiques (taxonomie de routage — pas du droit)
# --------------------------------------------------------------------------
DOMAINES_JURIDIQUES = (
    "logement_baux_foncier",
    "travail",
    "famille_mariage_filiation",
    "contrats_dettes_commerce",
    "penal_procedure_penale",
    "consommation",
    "associations_organisations_religieuses",
    "donnees_personnelles_numerique",
    "administratif_voies_de_recours",
    "transport_responsabilite_civile",
    "sante_droits_usagers",
    "indetermine",
)

# --------------------------------------------------------------------------
# Taxonomie de couverture (mission, partie 4 : domaines A a L)
# --------------------------------------------------------------------------
# Correspondance entre la nomenclature de la mission et les cles internes de
# routage. C'est une table de LECTURE : elle ne dit rien du droit, seulement
# comment nommer les memes ensembles. Toute cle interne est unique ; plusieurs
# codes de mission peuvent viser un meme domaine interne quand le corpus et le
# routage ne les distinguent pas encore (a scinder le jour ou un texte propre
# existe).
COUVERTURE_DOMAINES = (
    {"code": "A", "cle": "logement_baux_foncier",
     "libelle": "Logement, baux et foncier"},
    {"code": "B", "cle": "famille_mariage_filiation",
     "libelle": "Famille, couple et enfants"},
    {"code": "C", "cle": "travail",
     "libelle": "Travail, emploi et relations professionnelles"},
    {"code": "D", "cle": "contrats_dettes_commerce",
     "libelle": "Entreprises, commerce et activites economiques"},
    {"code": "E", "cle": "consommation",
     "libelle": "Dettes, argent et consommation"},
    {"code": "F", "cle": "administratif_voies_de_recours",
     "libelle": "Administration et documents officiels"},
    {"code": "G", "cle": "penal_procedure_penale",
     "libelle": "Penal, plaintes et procedures judiciaires"},
    {"code": "H", "cle": "associations_organisations_religieuses",
     "libelle": "Religion, communautes et associations"},
    {"code": "I", "cle": "donnees_personnelles_numerique",
     "libelle": "Numerique, internet et donnees personnelles"},
    {"code": "J", "cle": "transport_responsabilite_civile",
     "libelle": "Transport, accidents et responsabilite civile"},
    {"code": "K", "cle": "sante_droits_usagers",
     "libelle": "Sante et droits des usagers"},
    {"code": "L", "cle": "indetermine",
     "libelle": "Domaines transversaux et cas non classes"},
)

# --------------------------------------------------------------------------
# Statuts de couverture d'un domaine (mission, partie 11)
# --------------------------------------------------------------------------
# Un domaine peut etre TECHNICQUEMENT termine et JURIDIQUEMENT incomplet : ces
# deux faits doivent rester visibles separement, jamais fondus en un « fait ».
STATUTS_DOMAINE = (
    "TERMINE_ET_VERIFIE",              # tous les criteres, y compris revue humaine
    "TERMINE_TECHNIQUEMENT",           # chaine complete, corpus partiel
    "CORPUS_PARTIEL",                  # des textes, mais lacunes identifiees
    "EN_ATTENTE_VALIDATION_HUMAINE",   # rien ne peut avancer sans un juriste
    "BLOQUE_SOURCE",                   # source officielle inaccessible
    "NON_DEMARRE",                     # aucun texte collecte
)

# Institutions officielles hors *.gouv.ci : elles publient elles-memes leurs
# textes. Toute entree doit etre justifiee (un test le verifie) : ce n'est PAS
# une liste de sites « serieux », et un cabinet, un blog ou un agregateur
# commercial n'y entre jamais, meme s'il publie le bon texte.
INSTITUTIONS_HORS_GOUV_CI = (
    "oneci.ci",                 # Office National de l'Etat Civil et de l'Identification
    "mffe.ci",                  # Ministere de la Famille, de la Femme et de l'Enfant
    "autoritedeprotection.ci",  # Autorite de protection des donnees a caractere personnel
    "artci.ci",                 # Autorite de Regulation des Telecommunications/TIC
    "ohada.org",                # Organisation pour l'Harmonisation en Afrique du Droit des Affaires
    "courconstitutionnelle.ci", # Conseil constitutionnel
)

# --------------------------------------------------------------------------
# Registre des sources officielles
# --------------------------------------------------------------------------
# Ce registre est un POINT DE DEPART : l'accessibilite et le contenu de chaque
# URL sont testes au moment de la recherche (voir core/sources.py). Le champ
# "role" decrit l'usage, il n'affirme rien sur la validite des textes.
SOURCES_OFFICIELLES = (
    {
        "id": "SGG",
        "nom": "Secretariat General du Gouvernement de Cote d'Ivoire",
        "url": "https://www.sgg.gouv.ci/",
        "role": "Portail officiel du Gouvernement (textes, Journal officiel)",
        "type": "portail",
    },
    {
        "id": "JORCI",
        "nom": "Portail des Journaux officiels (ONECI)",
        "url": "https://jorci.oneci.ci/",
        "role": "Publication des Journaux officiels",
        "type": "journal_officiel",
    },
    {
        "id": "CNDJ",
        "nom": "Centre National de Documentation Juridique",
        "url": "https://www.cndj.ci/",
        "role": "Documentation juridique nationale",
        "type": "portail",
    },
    {
        "id": "CNDJ_TEXTES",
        "nom": "CNDJ — Textes legislatifs et reglementaires",
        "url": "https://www.cndj.ci/bases-de-recherche/textes-legislatifs-et-reglementaires.html",
        "role": "Base de recherche des textes legislatifs et reglementaires",
        "type": "base_recherche",
    },
    {
        "id": "CNDJ_CODES",
        "nom": "CNDJ — Codes et recueils de textes",
        "url": "https://www.cndj.ci/bases-de-recherche/codes-et-recueils-de-textes.html",
        "role": "Base de recherche des codes et recueils",
        "type": "base_recherche",
    },
    {
        "id": "CNDJ_JURIS",
        "nom": "CNDJ — Jurisprudence nationale",
        "url": "https://www.cndj.ci/bases-de-recherche/jurisprudence-nationale.html",
        "role": "Base de recherche de la jurisprudence nationale",
        "type": "base_recherche",
    },
    {
        "id": "CNDJ_COMMUNAUTAIRE",
        "nom": "CNDJ — Droit communautaire",
        "url": "https://www.cndj.ci/bases-de-recherche/droit-communautaire.html",
        "role": "Base de recherche du droit communautaire (UEMOA, CEDEAO, OHADA)",
        "type": "base_recherche",
    },
    {
        "id": "CNDJ_BIBLIO",
        "nom": "CNDJ — Bibliotheque numerique",
        "url": "https://biblio.cndj.ci",
        "role": "Bibliotheque numerique (acces possiblement payant ou restreint)",
        "type": "bibliotheque",
    },
    # --- Institutions officielles hors *.gouv.ci (verifiees accessibles) -----
    # Elles publient elles-memes leurs textes. Leur presence ici les fait entrer
    # dans le perimetre de core.sources.est_hote_officiel, ce qui autorise (et
    # exige une preuve pour) un etat VERIFIE sur leurs documents.
    {
        "id": "ONECI",
        "nom": "Office National de l'Etat Civil et de l'Identification",
        "url": "https://www.oneci.ci/",
        "role": "Etat civil ; publie les textes relatifs a l'etat civil et a la famille",
        "type": "institution",
    },
    {
        "id": "MFFE",
        "nom": "Ministere de la Famille, de la Femme et de l'Enfant",
        "url": "https://famille.gouv.ci/",
        "role": "Publie les textes relatifs a la famille, a l'enfance et a la protection",
        "type": "ministere",
    },
    {
        "id": "MFFE_SITE_FAMILLE",
        "nom": "MFFE — site Famille (textes juridiques)",
        "url": "https://mffe.ci/MFFE/site_famille/document-dinteret-public/textes-juridiques/",
        "role": "Textes juridiques de la famille et de l'enfance",
        "type": "ministere",
    },
    {
        "id": "AUTORITE_DONNEES",
        "nom": "Autorite de protection des donnees a caractere personnel",
        "url": "https://www.autoritedeprotection.ci/lois/",
        "role": "Lois relatives a la protection des donnees personnelles",
        "type": "autorite",
    },
    {
        "id": "ARTCI",
        "nom": "Autorite de Regulation des Telecommunications/TIC de Cote d'Ivoire",
        "url": "https://www.artci.ci/",
        "role": "Regulation du numerique, des telecommunications et de la cybersecurite",
        "type": "autorite",
    },
    {
        "id": "OHADA",
        "nom": "Organisation pour l'Harmonisation en Afrique du Droit des Affaires",
        "url": "https://ohada.org/",
        "role": "Actes uniformes applicables au droit des affaires (supranational)",
        "type": "organisation_supranationale",
    },
    {
        "id": "CONSEIL_CONSTITUTIONNEL",
        "nom": "Conseil constitutionnel de Cote d'Ivoire",
        "url": "https://courconstitutionnelle.ci/",
        "role": "Decisions et textes constitutionnels",
        "type": "juridiction",
    },
)


def source_par_id(source_id):
    """Retourne la source du registre ou None. Aucune source n'est inventee."""
    for s in SOURCES_OFFICIELLES:
        if s["id"] == source_id:
            return dict(s)
    return None


def dossier_utilisateur(dossier_id):
    """Retourne le chemin du dossier utilisateur, en refusant toute traversee."""
    if not dossier_id or any(c in str(dossier_id) for c in ("/", "\\", "..", "\x00")):
        raise ValueError("identifiant de dossier invalide : %r" % (dossier_id,))
    return DOSSIERS_DIR / str(dossier_id)
