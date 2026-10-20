#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reprise de la collecte (20 octobre 2026) : corrige le manifeste après l'analyse
des échecs du run 39247817113 et ajoute les sources trouvées par recherche.

Diagnostic des 35 échecs (constats KNOWLEDGE/collecte/resultats/*.json) :
  * 30 × HTTP 404 sur civlii.laws.africa / resolver.laws.africa : URL mal formées.
    Le document d'une œuvre CIVLII est servi à `<expression>/source` (sans `.pdf`),
    le scan du Journal officiel à `/en/<expression>/publication` ; les pages
    `/fr/.../publication`, `/fr/legislation/?page=N` (N ≥ 2) et le résolveur
    `?m=pdf` répondent 404. URL correctes relevées dans les résultats de recherche.
  * 2 × 404 famille.gouv.ci (anciennes adresses `public/documents/...`,
    `/publications`), 1 × 404 assnat.ci (`CONSTITUTION.pdf`), 1 × 404 FAOLEX
    (`ivc207091.pdf`) : documents déplacés ou retirés.
  * 1 × 403 emploi.gouv.ci : refus d'accès du serveur (robot), non contourné.
Aucun n'est une erreur temporaire : ces entrées sont DÉSACTIVÉES (conservées,
avec le motif et l'entrée qui les remplace), jamais supprimées.

Le script est idempotent : relancé, il ne duplique rien.

    python3 bin/manifeste_reprise.py
"""

import json
import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFESTE = os.path.join(RACINE, "KNOWLEDGE", "collecte", "manifeste.json")
DATE = "2026-10-20"
TROUVE = "URL relevée par recherche web le %s (résultat de moteur de recherche, puis page vérifiée)." % DATE

CIVLII = "https://civlii.laws.africa/en/akn/ci/act/"


def civlii(cle, expression, titre, numero, date, domaines, notes="", publication=True):
    """Deux entrées par œuvre CIVLII : la reproduction Laws.Africa (texte natif) et le
    scan du Journal officiel hébergé par CIVLII."""
    entrees = [{
        "cle": cle + "_civlii_source", "titre": titre + " — reproduction Laws.Africa / CIVLII",
        "numero_texte": numero, "date_texte": date, "type_texte": "loi",
        "autorite": "Laws.Africa / CIVLII (reproduction, CC BY 4.0)", "domaines": domaines,
        "url": CIVLII + expression + "/source", "categorie_source": "SECONDAIRE_CONSOLIDE",
        "mode": "fichier",
        "notes": ("Version consolidée : sert d'étalon pour mesurer l'OCR des exemplaires officiels et "
                  "à repérer les modifications. Jamais source de référence. " + TROUVE + " " + notes).strip()}]
    if publication:
        entrees.append({
            "cle": cle + "_civlii_jo", "titre": titre + " — Journal officiel (scan hébergé par CIVLII)",
            "numero_texte": numero, "date_texte": date, "type_texte": "loi",
            "autorite": "Journal officiel de la République de Côte d'Ivoire — image hébergée par CIVLII",
            "domaines": domaines, "url": CIVLII + expression + "/publication",
            "categorie_source": "SECONDAIRE_FAC_SIMILE", "mode": "fichier",
            "notes": ("Image du Journal officiel : seconde lecture indépendante du même texte. "
                      + TROUVE).strip()})
    return entrees


def decouverte(cle, url, filtre, notes):
    return {"cle": cle, "titre": "Page de découverte", "numero_texte": None, "date_texte": None,
            "type_texte": "page", "autorite": None, "domaines": [], "url": url,
            "categorie_source": "DECOUVERTE", "mode": "decouverte", "filtre_liens": filtre,
            "notes": notes}


AJOUTS = []
# ---------------------------------------------------------------- 1. Famille
AJOUTS += civlii("mariage_2019_570", "2019/570/eng@2023-10-13", "Loi n° 2019-570 du 26 juin 2019 relative au mariage",
                 "2019-570", "2019-06-26", [2], "Code langue « eng » dans l'URL CIVLII : à contrôler (texte attendu en français).")
AJOUTS += civlii("filiation_2019_571", "2019/571/fra@2023-10-13", "Loi n° 2019-571 du 26 juin 2019 relative à la filiation",
                 "2019-571", "2019-06-26", [2])
AJOUTS += civlii("minorite_2019_572", "2019/572/fra@2023-10-13", "Loi n° 2019-572 du 26 juin 2019 relative à la minorité",
                 "2019-572", "2019-06-26", [2, 22])
AJOUTS += civlii("successions_2019_573", "2019/573/fra@2023-10-13", "Loi n° 2019-573 du 26 juin 2019 relative aux successions",
                 "2019-573", "2019-06-26", [2])
AJOUTS += [
    {"cle": "oneci_jo_special_2019_572_573_575",
     "titre": "Journal officiel, numéro spécial du 16 juillet 2019 : lois n° 2019-572 (minorité), 2019-573 (successions), 2019-575",
     "numero_texte": "2019-572", "date_texte": "2019-06-26", "type_texte": "loi",
     "autorite": "Office National de l'État Civil et de l'Identification (ONECI) — republication du Journal officiel",
     "domaines": [2, 22], "url": "https://oneci.ci/uploads/files/articles/1638789741-loi-n2019-572-573-575-du-26-juin-2019.pdf",
     "categorie_source": "OFFICIEL_INSTITUTION", "mode": "fichier",
     "segment": {"debut": r"(?i)LOI\s+n\s*[°o]\s*2019\s*[-–]\s*572", "fin": r"(?i)LOI\s+n\s*[°o]\s*2019\s*[-–]\s*573"},
     "notes": "JO à plusieurs actes : segment 2019-572 déclaré ; la loi 2019-573 est déclarée dans l'entrée suivante (même fichier). " + TROUVE},
    {"cle": "oneci_jo_special_2019_573",
     "titre": "Loi n° 2019-573 du 26 juin 2019 relative aux successions (Journal officiel, numéro spécial du 16 juillet 2019, via ONECI)",
     "numero_texte": "2019-573", "date_texte": "2019-06-26", "type_texte": "loi",
     "autorite": "Office National de l'État Civil et de l'Identification (ONECI) — republication du Journal officiel",
     "domaines": [2], "url": "https://oneci.ci/uploads/files/articles/1638789741-loi-n2019-572-573-575-du-26-juin-2019.pdf",
     "categorie_source": "OFFICIEL_INSTITUTION", "mode": "fichier",
     "segment": {"debut": r"(?i)LOI\s+n\s*[°o]\s*2019\s*[-–]\s*573", "fin": r"(?i)LOI\s+n\s*[°o]\s*2019\s*[-–]\s*575"},
     "notes": "Même fichier que oneci_jo_special_2019_572_573_575, autre segment (doublon d'empreinte attendu). " + TROUVE},
    {"cle": "famille_minorite_2019_wm", "titre": "Loi n° 2019-572 du 26 juin 2019 relative à la minorité (famille.gouv.ci)",
     "numero_texte": "2019-572", "date_texte": "2019-06-26", "type_texte": "loi",
     "autorite": "Ministère de la Femme, de la Famille et de l'Enfant — famille.gouv.ci (republication)",
     "domaines": [2, 22], "url": "https://famille.gouv.ci/Tmffe/Loi-relative-a-la-minorite-2019WM.pdf",
     "categorie_source": "OFFICIEL_PORTAIL_GOUV", "mode": "fichier", "notes": TROUVE},
    {"cle": "assnat_mariage_2019_570", "titre": "Loi relative au mariage (Assemblée nationale)",
     "numero_texte": "2019-570", "date_texte": "2019-06-26", "type_texte": "loi",
     "autorite": "Assemblée nationale de Côte d'Ivoire", "domaines": [2],
     "url": "https://www.assnat.ci/IMG/pdf/loi_relative_au_mariage.pdf", "categorie_source": "OFFICIEL_INSTITUTION",
     "mode": "fichier", "notes": "Texte voté : possiblement non promulgué, à recouper. " + TROUVE},
]
# ---------------------------------------------------------------- 2. Travail
AJOUTS += civlii("travail_2015_532", "2015/532/fra@2023-08-10", "Loi n° 2015-532 du 20 juillet 2015 portant Code du travail",
                 "2015-532", "2015-07-20", [4])
AJOUTS += civlii("travail_enfants_2010_272", "2010/272/fra@2023-08-10",
                 "Loi n° 2010-272 du 30 septembre 2010 portant interdiction de la traite et des pires formes de travail des enfants",
                 "2010-272", "2010-09-30", [4, 22])
AJOUTS += [{"cle": "travail_2015_532_faolex_210897", "titre": "Loi n° 2015-532 du 20 juillet 2015 portant Code du travail (FAOLEX)",
            "numero_texte": "2015-532", "date_texte": "2015-07-20", "type_texte": "loi",
            "autorite": "FAO — base FAOLEX (reproduction)", "domaines": [4],
            "url": "https://faolex.fao.org/docs/pdf/ivc210897.pdf", "categorie_source": "SECONDAIRE_BASE_INTERNATIONALE",
            "mode": "fichier", "notes": "Lien relevé sur la page LEAP (PNUE) découverte au run 39229656741 ; remplace ivc207091.pdf (404)."}]
# ---------------------------------------------------------------- 3. Pénal
AJOUTS += civlii("code_penal_2019_574", "2019/574/fra@2024-06-23", "Loi n° 2019-574 du 26 juin 2019 portant Code pénal",
                 "2019-574", "2019-06-26", [5])
AJOUTS += civlii("cpp_2018_975", "2018/975/fra@2024-06-23", "Loi n° 2018-975 du 27 décembre 2018 portant Code de procédure pénale",
                 "2018-975", "2018-12-27", [5])
# ---------------------------------------------------------------- Autres domaines
AJOUTS += civlii("consommation_2016_412", "2016/412/fra@2023-06-21", "Loi n° 2016-412 du 15 juin 2016 relative à la consommation",
                 "2016-412", "2016-06-15", [7])
AJOUTS += civlii("nationalite_1961_415", "1961/415/fra@2005-08-29", "Loi n° 61-415 du 14 décembre 1961 portant Code de la nationalité",
                 "1961-415", "1961-12-14", [21], "Numéro CIVLII 1961/415 = loi n° 61-415 ; version consolidée au 29 août 2005.")
AJOUTS += civlii("cpcca_1972_833", "1972/833/fra@2022-05-27",
                 "Loi n° 72-833 du 21 décembre 1972 portant Code de procédure civile, commerciale et administrative",
                 "1972-833", "1972-12-21", [9, 1], "Identité de l'œuvre CIVLII 1972/833 à confirmer à la lecture.")
AJOUTS += civlii("code_civil_droits_civils", "1804/jouissance-et-privation-des-droits-civils-code-civil-napol%C3%A9onien/fra@2023-12-31",
                 "Code civil (1804) — jouissance et privation des droits civils, dispositions applicables en Côte d'Ivoire",
                 None, "1804-03-21", [1], "Code civil de 1804 resté applicable : vérifier pour chaque article qu'il n'est pas abrogé.",
                 publication=False)
AJOUTS += [
    {"cle": "cima_code_2019", "titre": "Code des assurances des États membres de la CIMA (édition 2019)",
     "numero_texte": "CIMA-2019", "date_texte": "2019-01-01", "type_texte": "code",
     "autorite": "Conférence Interafricaine des Marchés d'Assurances (CIMA)", "domaines": [12],
     "url": "https://cima-afrique.org/wp-content/uploads/2023/06/CODE-CIMA-2019.pdf",
     "categorie_source": "OFFICIEL_ORGANISATION", "mode": "fichier",
     "notes": "Édition 2019 : modifications postérieures (règlements du Conseil des ministres) à rechercher. " + TROUVE},
]
# ---------------------------------------------------------------- Découverte
TAXO = "https://civlii.laws.africa/en/taxonomy/cote-divoire-codes/cote-divoire-codes-"
for slug, domaine in (
        ("code-civile-code-des-biens-et-obligations", "1"), ("recueil-de-textes-personnes-familles", "2"),
        ("les-droits-de-lenfant", "22"), ("code-du-travail-et-autres-textes-relatifs-aux-droit-du-travail", "4"),
        ("code-de-prevoyance-sociale", "4"), ("convention-collective-interprofessionnelle", "4"),
        ("code-penal", "5"), ("code-de-procedure-penale", "5"),
        ("acte-uniforme-relatif-au-droit-commercial-general", "6"),
        ("acte-uniforme-revise-relatif-au-droit-des-societes-commerciales-et-du-groupement-dinteret-economique", "6"),
        ("acte-uniforme-portant-organisation-des-procedures-collectives-dapurement-du-passif", "6"),
        ("acte-uniforme-relatif-au-droit-de-larbitrage", "6"), ("acte-uniforme-relatif-a-la-mediation", "6"),
        ("recueil-de-textes-relatifs-a-la-consommation", "7"), ("code-de-procedure-civile-commerciale-et-administrative", "9"),
        ("juridiction", "9"), ("recueil-de-textes-fonction-publique", "9"), ("constitution", "10"),
        ("code-des-douanes", "11"), ("traite-cima", "12"), ("recueil-de-textes-relatifs-aux-transports", "13"),
        ("regulation-du-secteur-pharmaceutique", "15"), ("code-de-lhygiene-et-de-la-salubrite", "15"),
        ("recueil-de-textes-domaine-foncier-rural", "18"), ("code-de-lenvironnement", "19"),
        ("code-de-la-protection-des-oeuvres-de-lesprit", "20"),
        ("code-de-la-nationalite-et-loi-sur-lidentification-des-personnes", "21"),
        ("recueil-de-textes-bail-a-usage-dhabitation-bail-a-usage-professionnel", "3"),
        ("acte-uniforme-portant-organisation-des-procedures-simplifiees-de-recouvrement-et-des-voies-dexecution", "23"),
        ("acte-uniforme-portant-organisation-des-suretes", "23")):
    AJOUTS.append(decouverte("dec_civlii_taxo_" + slug[:60], TAXO + slug, r"/akn/",
                             "Collection CIVLII (domaine %s de la vision) : relève les œuvres et leurs expressions." % domaine))
for page in range(1, 17):
    AJOUTS.append(decouverte("dec_civlii_en_legislation_p%d" % page,
                             "https://civlii.laws.africa/en/legislation/?page=%d" % page, r"/akn/ci/",
                             "Liste complète CIVLII (798 documents au 20/10/2026, 50 par page) ; /fr/ ne pagine pas."))
for n in ("01", "02", "03", "06", "07", "08", "17", "18", "19", "20-pt", "22-pt", "23", "24", "25", "26", "28"):
    AJOUTS.append(decouverte("dec_ohada_jo_n_%s_large" % n, "https://www.ohada.org/journal-officiel-n-%s/" % n,
                             r"wp-content/uploads|\.pdf|drive\.google|download",
                             "Numéro du JO OHADA : filtre élargi (les liens de fichiers n'étaient pas relevés par « .pdf »)."))
AJOUTS += [
    decouverte("dec_ohada_actes_uniformes_large", "https://www.ohada.org/actes-uniformes/",
               r"wp-content/uploads|\.pdf|ohada\.org/[a-z-]+/$", "Index des Actes uniformes (filtre élargi)."),
    decouverte("dec_economie_codes_sectoriels", "https://economie-ivoirienne.ci/investissements/codes-sectoriels.html",
               r"\.pdf|/uploads/|/images/", "Codes sectoriels publiés par le portail économique."),
    decouverte("dec_cndj_biblio_travail", "https://biblio.cndj.ci/search/codes/274", r"\.pdf|/download|/view|/document",
               "CNDJ : recueil Code du travail (accès possiblement restreint : rien n'est contourné)."),
    decouverte("dec_oapi_bangui", "https://oapi.int/en/legal-framework/bangui-agreement/", r"\.pdf|wp-content/uploads",
               "Accord de Bangui : exemplaire officiel de l'OAPI."),
    decouverte("dec_cima_textes", "https://cima-afrique.org/", r"\.pdf|wp-content/uploads", "Textes officiels de la CIMA."),
]

# Entrées en échec définitif : désactivées, avec motif et remplaçante.
DESACTIVER = {
    "civlii_code_penal_source_pdf": "code_penal_2019_574_civlii_source",
    "civlii_cpp_source_pdf": "cpp_2018_975_civlii_source",
    "civlii_travail_enfants_2010_272": "travail_enfants_2010_272_civlii_source",
    "civlii_travail_source_pdf": "travail_2015_532_civlii_source",
    "code_penal_2019_574_civlii": "code_penal_2019_574_civlii_jo",
    "cpp_2018_975_civlii": "cpp_2018_975_civlii_jo",
    "filiation_2019_571_civlii": "filiation_2019_571_civlii_jo",
    "mariage_2019_570_civlii": "mariage_2019_570_civlii_jo",
    "minorite_2019_572_civlii": "minorite_2019_572_civlii_jo",
    "successions_2019_573_civlii": "successions_2019_573_civlii_jo",
    "travail_2015_532_civlii": "travail_2015_532_civlii_jo",
    "travail_2015_532_faolex": "travail_2015_532_faolex_210897",
    "code_penal_2019_574_mffe": "mffe_code_penal_2019_574",
    "assnat_constitution": "mffe_constitution_2016",
    "dec_emploi_gouv": None,
    "dec_famille_gouv_publications": "dec_famille_gouv",
}
for n in range(2, 11):
    DESACTIVER["dec_civlii_legislation_p%d" % n] = "dec_civlii_en_legislation_p%d" % n
for suffixe in ("2015_532_fra@2023-08-10", "2018_975_fra@2024-06-23", "2019_570_eng@2023-10-13",
                "2019_571_fra@2023-10-13", "2019_572_fra@2023-10-13", "2019_573_fra@2023-10-13",
                "2019_574_fra@2024-06-23"):
    DESACTIVER["dec_civlii_publication_" + suffixe] = None
for cle in ("dec_civlii_oeuvre_cpp", "dec_civlii_oeuvre_penal", "dec_civlii_oeuvre_travail"):
    DESACTIVER[cle] = None

# ======================================================================
# Second lot (après le run 39405665599 du 20/10/2026)
# ======================================================================
# Constat : sur CIVLII, les œuvres des grands codes (Code pénal, CPP, Code du
# travail, lois de la famille de 2019, consommation, nationalité) sont réservées
# aux abonnés « My CIVLII » (page d'œuvre : fonctionnalité réservée aux abonnés,
# connexion requise) : `/source` et `/publication` répondent 404 sans
# connexion. C'est une restriction d'accès : elle n'est PAS contournée.
import urllib.parse as _up

MEF = "https://www.economie-ivoirienne.ci/sites/default/files/sites/default/files/inline-files/"
AUTORITE_MEF = ("Ministère de l'Économie et des Finances — portail economie-ivoirienne.ci "
                "(republication ; portail lancé par le ministre, annonce sur finances.gouv.ci)")


def mef(cle, fichier, titre, numero, date, domaines, type_texte="loi", notes=""):
    return {"cle": cle, "titre": titre, "numero_texte": numero, "date_texte": date, "type_texte": type_texte,
            "autorite": AUTORITE_MEF, "domaines": domaines,
            "url": MEF + _up.quote(_up.unquote(fichier), safe="()'_-.,"),
            "categorie_source": "OFFICIEL_PORTAIL_GOUV", "mode": "fichier",
            "notes": ("Lien relevé sur la page « Codes sectoriels » (découverte du run 39405665599). " + notes).strip()}


AJOUTS_2 = [
    mef("mef_code_travail_2015_532", "Loi n° 2015-532 du 20 juillet 2015 portant code du Travail.pdf",
        "Loi n° 2015-532 du 20 juillet 2015 portant Code du travail", "2015-532", "2015-07-20", [4],
        notes="Version d'origine probable : l'ordonnance n° 2021-902 la modifie (entrée suivante)."),
    mef("mef_ord_2021_902_travail", "Ordonnance n°2021-902 du 22 décembre 2021 modifiant la loi n°2015-532 du 20 juillet 2015 portant Code du travail.pdf",
        "Ordonnance n° 2021-902 du 22 décembre 2021 modifiant la loi n° 2015-532 portant Code du travail",
        "2021-902", "2021-12-22", [4], type_texte="ordonnance"),
    mef("mef_jo_code_environnement_2023", "JO%20contenant%20Loi%20portant%20Code%20de%20l%27Environnement%20%20f%C3%A9v%202024.pdf",
        "Loi portant Code de l'environnement (Journal officiel, février 2024)", "2023-900", "2023-11-23", [19],
        notes="Numéro 2023-900 tiré de LEAP (PNUE) : à confirmer à la lecture du JO."),
    mef("mef_jo_code_eau_2023", "JO%20contenant%20Loi%20portant%20Code%20de%20l%27Eau%20%20f%C3%A9v%202024.pdf",
        "Loi portant Code de l'eau (Journal officiel, février 2024)", None, None, [19]),
    mef("mef_code_hygiene_salubrite", "CODE%20HYGIENE%20ET%20DE%20LA%20SALUBRITE_compressed.pdf",
        "Code de l'hygiène et de la salubrité", None, None, [15, 19], type_texte="code"),
    mef("mef_loti_2014_812", "LOI-N%C2%B02014-812-du-16-decembre-2014-dOrientation-du-Transport-InterieurLOTI.pdf",
        "Loi n° 2014-812 du 16 décembre 2014 d'orientation du transport intérieur", "2014-812", "2014-12-16", [13]),
    mef("mef_foncier_rural_2019_868", "2019-10-14%20L2019-868%20modifiant%20L98-750%20Foncier%20rural_compressed.pdf",
        "Loi n° 2019-868 du 14 octobre 2019 modifiant la loi n° 98-750 relative au domaine foncier rural",
        "2019-868", "2019-10-14", [18]),
    mef("mef_loi_finances_2024", "Loi%20de%20finances%20N%C2%B02023-1000%20du%2018%20d%C3%A9cembre%202023%20portant%20budget%20de%20l%E2%80%99Etat%20pour%20l%E2%80%99ann%C3%A9e%202024.pdf",
        "Loi de finances n° 2023-1000 du 18 décembre 2023 portant budget de l'État pour l'année 2024",
        "2023-1000", "2023-12-18", [11]),
    mef("mef_annexe_fiscale_2024", "Annexe fiscale à la Loi de finances N°2023-1000 du 18 décembre 2023.pdf",
        "Annexe fiscale à la loi de finances n° 2023-1000 du 18 décembre 2023", "2023-1000", "2023-12-18", [11],
        notes="Mesures fiscales de l'année : ne remplace pas le Code général des impôts."),
    mef("mef_code_maritime_2017_442", "Loi n° 2017-442 du 30 juin 2017 portant Code maritime.pdf",
        "Loi n° 2017-442 du 30 juin 2017 portant Code maritime", "2017-442", "2017-06-30", [13]),
    mef("mef_echanges_electroniques_2017_500", "Ordonnance%20n%C2%B02017-500%20du%202%20ao%C3%BBt%202017%20relative%20aux%20%C3%A9changes%20%C3%A9lectroniques%20entre%20les%20usagers%20et%20les%20autorit%C3%A9s.pdf",
        "Ordonnance n° 2017-500 du 2 août 2017 relative aux échanges électroniques entre les usagers et les autorités administratives",
        "2017-500", "2017-08-02", [9, 14], type_texte="ordonnance"),
    {"cle": "oapi_accord_bangui_fr", "titre": "Accord de Bangui révisé (Bamako, 14 décembre 2015) — version française",
     "numero_texte": "BANGUI-2015", "date_texte": "2015-12-14", "type_texte": "traite",
     "autorite": "Organisation Africaine de la Propriété Intellectuelle (OAPI)", "domaines": [20],
     "url": "https://www.oapi.int/wp-content/uploads/2023/11/francais.pdf",
     "categorie_source": "OFFICIEL_ORGANISATION", "mode": "fichier",
     "notes": "Lien relevé sur la page officielle de l'OAPI (découverte du run 39405665599)."},
    {"cle": "who_code_prevoyance_sociale_99_477", "titre": "Loi n° 99-477 du 2 août 1999 portant modification du Code de prévoyance sociale (OMS)",
     "numero_texte": "1999-477", "date_texte": "1999-08-02", "type_texte": "loi",
     "autorite": "Organisation mondiale de la santé — répertoire de législation (reproduction)", "domaines": [4],
     "url": "https://extranet.who.int/cpcd/sites/default/files/public_file_repository/CIV_Cote-d-Ivoire_Law-99-477_Social-Insurance-Code_1999.pdf",
     "categorie_source": "SECONDAIRE_BASE_INTERNATIONALE", "mode": "fichier", "notes": TROUVE},
]
AJOUTS_2 += civlii("etat_civil_2018_862", "2018/862/fra@2023-10-13", "Loi n° 2018-862 du 19 novembre 2018 relative à l'état civil",
                   "2018-862", "2018-11-19", [2])
AJOUTS_2 += civlii("violences_2021_894", "2021/894/fra@2023-10-11",
                   "Loi n° 2021-894 du 21 décembre 2021 relative aux mesures de protection des victimes de violences domestiques, de viol et de violences sexuelles autres que domestiques",
                   "2021-894", "2021-12-21", [22, 2, 5],
                   "Le corpus porte ce texte sous le numéro « 202-894 » (faute de la source) : même loi.")
AJOUTS_2 += civlii("prevoyance_sociale_1999_477", "1999/477/fra@2023-11-23", "Loi n° 99-477 du 2 août 1999 portant Code de prévoyance sociale",
                   "1999-477", "1999-08-02", [4])
AJOUTS_2 += civlii("cci_1977", "convention/1977/convention-collective-interprofessionnelle/fra@2024-02-16",
                   "Convention collective interprofessionnelle du 19 juillet 1977", "CCI-1977", "1977-07-19", [4], publication=False)
AJOUTS_2 += civlii("arbitrage_1993_671", "1993/671/fra@2022-05-27", "Loi n° 93-671 du 9 août 1993 relative à l'arbitrage",
                   "1993-671", "1993-08-09", [6, 24])
AJOUTS_2 += civlii("juridictions_2016_1110", "2016/1110/fra@2023-07-06",
                   "Loi n° 2016-1110 du 8 décembre 2016 portant création, organisation et fonctionnement des juridictions de commerce",
                   "2016-1110", "2016-12-08", [6, 9])
AJOUTS_2 += civlii("petits_litiges_2015_904", "2015/904/fra@2022-05-27",
                   "Loi n° 2015-904 du 30 décembre 2015 relative aux procédures spéciales pour le règlement des petits litiges",
                   "2015-904", "2015-12-30", [9, 7])
AJOUTS_2 += civlii("mediation_2014_389", "2014/389/fra@2022-05-27", "Loi n° 2014-389 du 20 juin 2014 relative à la médiation judiciaire et conventionnelle",
                   "2014-389", "2014-06-20", [9, 6])
AJOUTS_2 += civlii("commissaires_justice_2018_974", "2018/974/fra@2023-11-23", "Loi n° 2018-974 du 27 décembre 2018 portant statut des commissaires de justice",
                   "2018-974", "2018-12-27", [23, 9])
AJOUTS_2 += civlii("code_investissements_2018_646", "ord/2018/646/fra@2024-12-27", "Ordonnance n° 2018-646 du 1er août 2018 portant Code des investissements",
                   "2018-646", "2018-08-01", [6])
AJOUTS_2 += civlii("corruption_2013_660", "ord/2013/660/fra@2024-01-17",
                   "Ordonnance n° 2013-660 du 20 septembre 2013 relative à la prévention et à la lutte contre la corruption",
                   "2013-660", "2013-09-20", [5, 9])
for page in ("droit-commercial-general", "droit-des-societes-commerciales-et-du-gie", "procedures-collectives-dapurement-du-passif",
             "droit-de-larbitrage", "acte-uniforme-relatif-a-la-mediation", "droit-des-societes-cooperatives",
             "contrats-de-transport-de-marchandises-par-route",
             "acte-uniforme-relatif-au-droit-comptable-et-a-linformation-financiere-audcif", "organisation-des-suretes",
             "traite-portant-revision-du-traite-relatif-a-lharmonisation-du-droit-des-affaires-en-afrique"):
    AJOUTS_2.append(decouverte("dec_ohada_au_" + page[:50], "https://www.ohada.org/%s/" % page,
                               r"wp-content/uploads/.+\.pdf", "Page de l'Acte uniforme sur ohada.org : relève le PDF officiel."))

# Œuvres CIVLII réservées aux abonnés (404 sans connexion au run 39405665599).
RESTREINTES = (
    "mariage_2019_570_civlii_source", "mariage_2019_570_civlii_jo", "filiation_2019_571_civlii_source",
    "filiation_2019_571_civlii_jo", "minorite_2019_572_civlii_source", "minorite_2019_572_civlii_jo",
    "successions_2019_573_civlii_source", "successions_2019_573_civlii_jo", "travail_2015_532_civlii_source",
    "travail_2015_532_civlii_jo", "travail_enfants_2010_272_civlii_source", "travail_enfants_2010_272_civlii_jo",
    "code_penal_2019_574_civlii_source", "code_penal_2019_574_civlii_jo", "cpp_2018_975_civlii_source",
    "cpp_2018_975_civlii_jo", "consommation_2016_412_civlii_source", "consommation_2016_412_civlii_jo",
    "nationalite_1961_415_civlii_source", "nationalite_1961_415_civlii_jo", "code_civil_droits_civils_civlii_source",
    "cpcca_1972_833_civlii_jo",
    # 404 au run 39407799324 (second lot) : même restriction
    "etat_civil_2018_862_civlii_source", "etat_civil_2018_862_civlii_jo", "violences_2021_894_civlii_source",
    "violences_2021_894_civlii_jo", "prevoyance_sociale_1999_477_civlii_source", "prevoyance_sociale_1999_477_civlii_jo",
    "cci_1977_civlii_source", "arbitrage_1993_671_civlii_jo", "juridictions_2016_1110_civlii_jo",
    "petits_litiges_2015_904_civlii_jo", "mediation_2014_389_civlii_jo", "corruption_2013_660_civlii_jo")
MOTIF_RESTREINT = ("Œuvre CIVLII réservée aux abonnés « My CIVLII » (page d'œuvre : accès réservé, connexion "
                   "requise ; constaté le 20/10/2026) : HTTP 404 sans connexion. Restriction d'accès non contournée.")
DESACTIVER_2 = {cle: None for cle in RESTREINTES}
for n in range(2, 17):
    DESACTIVER_2["dec_civlii_en_legislation_p%d" % n] = None   # la liste ne pagine pas par ?page=N
DESACTIVER_2["famille_minorite_2019_wm"] = "oneci_jo_special_2019_572_573_575"
DESACTIVER_2["ohada_aua_2017_attachement"] = "ohada_aua_2017"
# Run 39418336561 : HTTP 403 (refus du serveur) ; aucune nouvelle tentative.
DESACTIVER_2["refworld_etat_civil_2018_862"] = None
DESACTIVER_2["dec_faolex_notice_210897"] = None


# Segments des Journaux officiels à plusieurs actes (début = en-tête de l'acte,
# en majuscules et suivi de « du », pour ne pas s'arrêter au sommaire).
def _acte(numero):
    annee, rang = numero.split("-")
    return r"L\s?O\s?I\s?n\s*[°o]\s*%s\s*[-–]\s*%s\s+du" % (annee, rang)


SEGMENTS = {
    "oneci_jo_special_2019_572_573_575": {"debut": _acte("2019-572"), "fin": _acte("2019-573")},
    "oneci_jo_special_2019_573": {"debut": _acte("2019-573"), "fin": _acte("2019-575")},
    "mffe_successions_2019_573": {"debut": _acte("2019-573"), "fin": _acte("2019-575")},
    "mffe_pupille_2015_539": {"debut": _acte("2015-539"), "fin": _acte("2015-540")},
    "officiel_famille_loi_no_2015_539_du_20_juillet_2015_portant_statu": {"debut": _acte("2015-539"),
                                                                         "fin": _acte("2015-540")},
    "mariage_2019_570_faolex": {"debut": _acte("2019-570"), "fin": _acte("2019-571")},
    "officiel_famille_loi_n_2019_571_du_26_juin_2019_relative_la_filia": {
        "debut": _acte("2019-571"), "fin": r"D\s?[EÉ]\s?C\s?R\s?E\s?T\s+n\s*[°o]\s*2019\s*[-–]\s*590"},
}
# Lectures OCR d'un numéro d'acte démenties par le document lui-même.
ACTES_OCR_IGNORES = {
    "mffe_cpp_2018_975": {"2018-9735": "titre lu « 2018-9735 » par l'OCR ; le sommaire du même Journal "
                                       "officiel porte « Loi n° 2018-975 » et le document ne contient qu'un acte"},
}


# ======================================================================
# Troisième lot : Actes uniformes OHADA (bibliothèque numérique officielle)
# ======================================================================
# Les pages ohada.org/en/<acte>/ renvoient la « version signée » de chaque Acte
# uniforme vers biblio.ohada.org (bibliothèque numérique de l'OHADA) ; identifiants
# relevés sur ces pages le 20/10/2026.
BIBLIO = "https://biblio.ohada.org/pmb/opac_css/doc_num.php?explnum_id=%d"
OHADA = "Organisation pour l'Harmonisation en Afrique du Droit des Affaires — bibliothèque numérique (version signée)"
AJOUTS_3 = []
for cle, ident, titre, numero, date, domaines in (
        ("ohada_audcg_2010", 481, "Acte uniforme portant sur le droit commercial général (Lomé, 15 décembre 2010)",
         "AUDCG-2010", "2010-12-15", [6]),
        ("ohada_auscgie_2014", 486, "Acte uniforme révisé relatif au droit des sociétés commerciales et du GIE (Ouagadougou, 30 janvier 2014)",
         "AUSCGIE-2014", "2014-01-30", [6]),
        ("ohada_aupcap_2015", 484, "Acte uniforme portant organisation des procédures collectives d'apurement du passif (Grand-Bassam, 10 septembre 2015)",
         "AUPCAP-2015", "2015-09-10", [6, 23]),
        ("ohada_aua_2017", 480, "Acte uniforme relatif au droit de l'arbitrage (Conakry, 23 novembre 2017)",
         "AUA-2017", "2017-11-23", [6, 24]),
        ("ohada_aus_2010", 483, "Acte uniforme portant organisation des sûretés (Lomé, 15 décembre 2010)",
         "AUS-2010", "2010-12-15", [23]),
        ("ohada_aucoop_2010", 487, "Acte uniforme relatif au droit des sociétés coopératives (Lomé, 15 décembre 2010)",
         "AUSCOOP-2010", "2010-12-15", [6]),
        ("ohada_audtmr_2003", 479, "Acte uniforme relatif aux contrats de transport de marchandises par route (Yaoundé, 22 mars 2003)",
         "AUCTMR-2003", "2003-03-22", [13, 6])):
    AJOUTS_3.append({"cle": cle, "titre": titre, "numero_texte": numero, "date_texte": date, "type_texte": "acte_uniforme",
                     "autorite": OHADA, "domaines": domaines, "url": BIBLIO % ident,
                     "categorie_source": "OFFICIEL_ORGANISATION", "mode": "fichier",
                     "notes": "Lien « version signée » de la page ohada.org/en/ de l'Acte (relevé le 20/10/2026)."})
AJOUTS_3 += [
    {"cle": "ohada_aua_2017_attachement", "titre": "Acte uniforme relatif au droit de l'arbitrage (2017) — fichier joint ohada.org",
     "numero_texte": "AUA-2017", "date_texte": "2017-11-23", "type_texte": "acte_uniforme",
     "autorite": "OHADA — site ohada.org (pièce jointe)", "domaines": [6, 24],
     "url": "https://www.ohada.org/attachments/article/2290/Acte-Uniforme-relatif-au-droit-d-arbitrage-2017.pdf",
     "categorie_source": "OFFICIEL_ORGANISATION", "mode": "fichier", "notes": "Relevé sur ohada.org/en/arbitration-law/."},
    {"cle": "senegal_audcg_2010", "titre": "Acte uniforme portant sur le droit commercial général (republication du ministère de la Justice du Sénégal)",
     "numero_texte": "AUDCG-2010", "date_texte": "2010-12-15", "type_texte": "acte_uniforme",
     "autorite": "Ministère de la Justice du Sénégal (État partie OHADA) — republication",
     "domaines": [6], "url": "https://justice.sec.gouv.sn/wp-content/uploads/textes-reglements/OHADA/Acte-uniforme-portant-sur-le-droit-commercial-general-lome-15102010.pdf",
     "categorie_source": "SECONDAIRE_AUTRE", "mode": "fichier",
     "notes": "Administration d'un autre État partie : étalon de recoupement, jamais source de référence. " + TROUVE},
    {"cle": "comores_auscgie_2014", "titre": "Acte uniforme révisé sociétés commerciales et GIE (republication du ministère de la Justice des Comores)",
     "numero_texte": "AUSCGIE-2014", "date_texte": "2014-01-30", "type_texte": "acte_uniforme",
     "autorite": "Ministère de la Justice de l'Union des Comores (État partie OHADA) — republication",
     "domaines": [6], "url": "https://justice.gouv.km/wp-content/uploads/2025/03/ohada-acte-uniforme-2014-droit-societes-commerciales-gie.pdf",
     "categorie_source": "SECONDAIRE_AUTRE", "mode": "fichier", "notes": "Étalon de recoupement. " + TROUVE},
    {"cle": "comores_aupcap_2015", "titre": "Acte uniforme procédures collectives d'apurement du passif (republication du ministère de la Justice des Comores)",
     "numero_texte": "AUPCAP-2015", "date_texte": "2015-09-10", "type_texte": "acte_uniforme",
     "autorite": "Ministère de la Justice de l'Union des Comores (État partie OHADA) — republication",
     "domaines": [6, 23], "url": "https://justice.gouv.km/wp-content/uploads/2025/03/ohada-acte-uniforme-2015-procedures-collectives.pdf",
     "categorie_source": "SECONDAIRE_AUTRE", "mode": "fichier", "notes": "Étalon de recoupement. " + TROUVE},
]


# ======================================================================
# Quatrième lot : versions EN VIGUEUR des Actes uniformes
# ======================================================================
# Constat du 20/10/2026 (lecture des scans) : les liens « version signée » de
# ohada.org/en/<acte>/ renvoient aux versions D'ORIGINE, abrogées :
# AUDCG 1997 (JO n° 1 du 1/10/1997), AUSC 1997, AUPC 1998 (JO du 1/7/1998),
# AUA 1999. Elles ne sont JAMAIS intégrées (marque `version_abrogee`).
VERSIONS_ABROGEES = {
    "ohada_audcg_2010": "Le fichier est l'AUDCG du 17 avril 1997 (JO OHADA n° 1 du 1er octobre 1997), révisé le 15 décembre 2010.",
    "ohada_auscgie_2014": "Le fichier est l'Acte uniforme sociétés commerciales du 17 avril 1997 (JO du 1er octobre 1997), révisé le 30 janvier 2014.",
    "ohada_aupcap_2015": "Le fichier est l'Acte uniforme procédures collectives du 10 avril 1998 (JO du 1er juillet 1998), remplacé le 10 septembre 2015.",
    "ohada_aua_2017": "Le fichier est l'Acte uniforme arbitrage du 11 mars 1999, remplacé le 23 novembre 2017.",
}
PMB = "https://biblio.ohada.org/pmb/opac_css/index.php?"
AJOUTS_4 = [
    decouverte("dec_biblio_ohada_notice_1860", PMB + "lvl=notice_display&id=1860", r"doc_num\.php|explnum",
               "Notice du JO OHADA spécial du 25/09/2015 (AUPC révisé), citée par le Secrétariat permanent."),
    decouverte("dec_biblio_ohada_recherche_jo_2014", PMB + "lvl=more_results&mode=keyword&user_query=journal+officiel+2014",
               r"notice_display|doc_num\.php", "Recherche du JO de février 2014 (AUSCGIE révisé)."),
    decouverte("dec_biblio_ohada_recherche_jo_2017", PMB + "lvl=more_results&mode=keyword&user_query=journal+officiel+2017",
               r"notice_display|doc_num\.php", "Recherche du JO du 15/12/2017 (AUA, médiation)."),
    decouverte("dec_biblio_ohada_recherche_jo_23", PMB + "lvl=more_results&mode=keyword&user_query=journal+officiel+23",
               r"notice_display|doc_num\.php", "Recherche du JO n° 23 du 15/02/2011 (AUDCG, AUS, coopératives)."),
    {"cle": "senegal_auscgie_jo_2014", "titre": "Acte uniforme révisé sociétés commerciales et GIE — JO OHADA de février 2014 (republication du ministère de la Justice du Sénégal)",
     "numero_texte": "AUSCGIE-2014", "date_texte": "2014-01-30", "type_texte": "acte_uniforme",
     "autorite": "Ministère de la Justice du Sénégal (État partie OHADA) — republication",
     "domaines": [6], "url": "https://justice.sec.gouv.sn/wp-content/uploads/textes-reglements/OHADA/Acte-uniforme-relatif-droit-societes-commerciales-gie-auscgie-jo-fevrier-2014.pdf",
     "categorie_source": "SECONDAIRE_AUTRE", "mode": "fichier", "notes": "Étalon de recoupement. " + TROUVE},
]


# Reclassements constatés à la lecture du document.
_CANDIDAT = ("CANDIDAT_OFFICIEL", "Hôte au registre des sources CANDIDATES (config.SOURCES_CANDIDATES) : identité non "
             "établie par une source indépendante ; collecté et analysé, jamais intégré (décision du 20/10/2026)")
RECLASSEMENTS = {
    **{cle: _CANDIDAT for cle in ("cima_code_2019", "mef_code_travail_2015_532", "mef_ord_2021_902_travail",
                                  "mef_jo_code_environnement_2023", "mef_jo_code_eau_2023", "mef_code_hygiene_salubrite",
                                  "mef_loti_2014_812", "mef_foncier_rural_2019_868", "mef_loi_finances_2024",
                                  "mef_annexe_fiscale_2024", "mef_code_maritime_2017_442",
                                  "mef_echanges_electroniques_2017_500")},
    "travail_2015_532_faolex_210897": ("SECONDAIRE_FAC_SIMILE",
        "Image du JO n° 74 du 14/09/2015 hébergée par FAOLEX (analyse : KNOWLEDGE/collecte/analyses/code_travail_2015_faolex.json)"),
}


# ======================================================================
# Cinquième lot (après le run 39414429864)
# ======================================================================
AJOUTS_5 = [
    {"cle": "ohada_jo_aupc_2015_explnum_%d" % n,
     "titre": "Journal officiel de l'OHADA, numéro spécial du 25/09/2015 (AUPC révisé) — fichier %d de la notice 1860" % n,
     "numero_texte": "AUPCAP-2015", "date_texte": "2015-09-10", "type_texte": "acte_uniforme",
     "autorite": "OHADA — bibliothèque numérique (notice 1860, citée par le Secrétariat permanent)", "domaines": [6, 23],
     "url": "https://biblio.ohada.org/doc_num.php?explnum_id=%d" % n, "categorie_source": "OFFICIEL_ORGANISATION",
     "mode": "fichier", "notes": "Fichier relevé sur la notice 1860 au run 39414429864 ; identité à contrôler à la lecture."}
    for n in (16, 17, 18, 19)]
AJOUTS_5 += [
    decouverte("dec_biblio_ohada_notice_1881", PMB + "lvl=notice_display&id=1881",
               r"bulletin_display|doc_num\.php|explnum", "Collection « Journal Officiel » de l'OHADA (liste des numéros)."),
    {"cle": "refworld_etat_civil_2018_862", "titre": "Loi n° 2018-862 du 19 novembre 2018 relative à l'état civil (Refworld, HCR)",
     "numero_texte": "2018-862", "date_texte": "2018-11-19", "type_texte": "loi",
     "autorite": "HCR — base Refworld (reproduction ; source déclarée : autorités nationales)", "domaines": [2],
     "url": "https://www.refworld.org/sites/default/files/legacy-pdf/en/2018-12/5ce3ed834.pdf",
     "categorie_source": "SECONDAIRE_BASE_INTERNATIONALE", "mode": "fichier",
     "notes": "Pour la page 2 illisible des deux exemplaires officiels (art. 5 à 20) : étalon seulement. " + TROUVE},
    decouverte("dec_faolex_notice_210897", "https://www.fao.org/faolex/results/details/fr/c/LEX-FAOC210897/",
               r"\.pdf|faolex", "Notice FAOLEX du fac-similé du Code du travail (provenance)."),
]



# ======================================================================
# Sixième lot (après le run 39418336561) : numéros du Journal officiel de
# l'OHADA relevés sur la notice 1881 (collection « Journal Officiel »),
# pour trouver la publication officielle des Actes uniformes en vigueur
# dont seule la « version signée » abrogée était disponible.
# ======================================================================
AJOUTS_6 = [
    decouverte("dec_biblio_ohada_bulletin_%d" % n, "https://biblio.ohada.org/index.php?lvl=bulletin_display&id=%d" % n,
               r"doc_num\.php|explnum", "Numéro du JO OHADA : %s (notice 1881)." % objet)
    for n, objet in ((1561, "Acte uniforme relatif au droit des sociétés commerciales et du GIE"),
                     (1696, "Acte uniforme relatif à la médiation et Acte uniforme relatif au droit de l'arbitrage"),
                     (1722, "Acte uniforme relatif au droit des sociétés commerciales et du GIE, règlement de procédure de la CCJA"))]


def main():
    manifeste = json.load(open(MANIFESTE, encoding="utf-8"))
    existantes = {s["cle"]: s for s in manifeste["sources"]}
    ajoutees = 0
    for entree in AJOUTS + AJOUTS_2 + AJOUTS_3 + AJOUTS_4 + AJOUTS_5 + AJOUTS_6:
        if entree["cle"] not in existantes:
            entree["ajoutee_le"] = DATE
            manifeste["sources"].append(entree)
            existantes[entree["cle"]] = entree
            ajoutees += 1
    for cle, segment in SEGMENTS.items():
        if cle in existantes and existantes[cle].get("segment") != segment:
            existantes[cle]["segment"] = segment
    for cle, (categorie, motif) in RECLASSEMENTS.items():
        if cle in existantes and existantes[cle]["categorie_source"] != categorie:
            existantes[cle]["reclassement"] = {"le": DATE, "de": existantes[cle]["categorie_source"], "motif": motif}
            existantes[cle]["categorie_source"] = categorie
    for cle, constat in VERSIONS_ABROGEES.items():
        if cle in existantes:
            existantes[cle]["version_abrogee"] = {"le": DATE, "constat": constat,
                                                  "consequence": "jamais intégré au corpus de référence"}
    for cle, ignores in ACTES_OCR_IGNORES.items():
        if cle in existantes:
            existantes[cle]["actes_ocr_ignores"] = ignores
    desactivees = 0
    for cle, remplacante in list(DESACTIVER.items()) + list(DESACTIVER_2.items()):
        source = existantes.get(cle)
        if source is None or source.get("desactivee"):
            continue
        resultat = os.path.join(RACINE, "KNOWLEDGE", "collecte", "resultats", cle + ".json")
        constat = json.load(open(resultat, encoding="utf-8")) if os.path.isfile(resultat) else {}
        if constat.get("statut") in ("TELECHARGE", "DECOUVERTE"):
            continue  # jamais désactiver une entrée qui a abouti
        source["desactivee"] = {
            "le": DATE, "http": constat.get("http"),
            "motif": MOTIF_RESTREINT if cle in RESTREINTES else ("HTTP %s définitif (%s) : URL incorrecte ou document retiré ; non temporaire."
                      % (constat.get("http"), constat.get("date_recuperation", "?")[:10])
                      if constat.get("http") != 403 else
                      "HTTP 403 : refus d'accès du serveur ; aucune tentative de contournement."),
            "remplacee_par": remplacante}
        desactivees += 1
    manifeste["categories"].setdefault(
        "CANDIDAT_OFFICIEL", "Hôte candidat : identité de l'institution non établie de façon indépendante ; jamais intégré")
    manifeste["categories"].setdefault(
        "DESACTIVEE", "Entrée conservée pour mémoire : échec définitif constaté, voir « desactivee »")
    with open(MANIFESTE, "w", encoding="utf-8") as flux:
        json.dump(manifeste, flux, ensure_ascii=False, indent=1)
        flux.write("\n")
    print("ajoutées : %d ; désactivées : %d ; total : %d" % (ajoutees, desactivees, len(manifeste["sources"])))


if __name__ == "__main__":
    main()
