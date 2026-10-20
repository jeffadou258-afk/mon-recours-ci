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


def main():
    manifeste = json.load(open(MANIFESTE, encoding="utf-8"))
    existantes = {s["cle"]: s for s in manifeste["sources"]}
    ajoutees = 0
    for entree in AJOUTS:
        if entree["cle"] not in existantes:
            entree["ajoutee_le"] = DATE
            manifeste["sources"].append(entree)
            existantes[entree["cle"]] = entree
            ajoutees += 1
    desactivees = 0
    for cle, remplacante in DESACTIVER.items():
        source = existantes.get(cle)
        if source is None or source.get("desactivee"):
            continue
        resultat = os.path.join(RACINE, "KNOWLEDGE", "collecte", "resultats", cle + ".json")
        constat = json.load(open(resultat, encoding="utf-8")) if os.path.isfile(resultat) else {}
        if constat.get("statut") in ("TELECHARGE", "DECOUVERTE"):
            continue  # jamais désactiver une entrée qui a abouti
        source["desactivee"] = {
            "le": DATE, "http": constat.get("http"),
            "motif": ("HTTP %s définitif (%s) : URL incorrecte ou document retiré ; non temporaire."
                      % (constat.get("http"), constat.get("date_recuperation", "?")[:10])
                      if constat.get("http") != 403 else
                      "HTTP 403 : refus d'accès du serveur ; aucune tentative de contournement."),
            "remplacee_par": remplacante}
        desactivees += 1
    manifeste["categories"].setdefault(
        "DESACTIVEE", "Entrée conservée pour mémoire : échec définitif constaté, voir « desactivee »")
    with open(MANIFESTE, "w", encoding="utf-8") as flux:
        json.dump(manifeste, flux, ensure_ascii=False, indent=1)
        flux.write("\n")
    print("ajoutées : %d ; désactivées : %d ; total : %d" % (ajoutees, desactivees, len(manifeste["sources"])))


if __name__ == "__main__":
    main()
