#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Prépare les fiches A_VALIDER_PAR_JURISTE pour la consommation et les associations.

Le contenu juridique de chaque fiche (titre, lecture, démarche, déclencheurs) est
rédigé ici, mais la CITATION n'est jamais retapée : elle est lue dans
`articles_corpus` et recopiée telle quelle, avec son empreinte. Si l'article
n'existe pas, le script échoue — aucun doute possible sur la provenance.

Les fiches produites vont dans `KNOWLEDGE/catalogue_a_valider.json`, JAMAIS dans
`catalogue.json` que lit le moteur : elles ne répondent à aucun citoyen tant
qu'un juriste ne les a pas validées.

Usage : ./.venv-corpus/bin/python bin/preparer_fiches_a_valider.py
"""
import json
import os
import re
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from config import CHEMIN_DB  # noqa: E402

SORTIE = os.path.join(RACINE, "KNOWLEDGE", "catalogue_a_valider.json")
STATUT = "A_VALIDER_PAR_JURISTE"

# Chaque entrée décrit ce que la fiche AFFIRME. Les valeurs sont volontairement
# sobres : rien qui ne soit écrit dans l'article cité. Ce que le texte renvoie à
# un décret absent est marqué INFORMATION_NON_ETABLIE.
FICHES = [
    # ---------------------------------------------------------------- consommation
    {
        "id": "CONSO_11_RETOUR_VENTE_DISTANCE",
        "domaine": "consommation",
        "numero_texte": "2016-412",
        "article": "11",
        "titre": "Vente à distance : délai de dix jours pour retourner le produit",
        "declencheurs": ["vente à distance", "achat en ligne", "commande par internet",
                         "retour du produit", "je veux retourner", "délai de retour",
                         "achat par correspondance", "vente hors établissement"],
        "lecture": ("Pour une vente à distance ou hors établissement, l'acheteur dispose de dix jours "
                    "ouvrables à compter de la livraison pour retourner le produit au vendeur, en vue "
                    "d'un échange ou d'un remboursement, sans pénalités autres que les frais de retour."),
        "faits_requis": [["achat_distance", "L'achat a-t-il été fait à distance ou hors établissement ?"],
                         ["date_livraison", "À quelle date le produit a-t-il été livré ?"]],
        "etape_plan": ("Conserver la preuve d'achat et la date de livraison, puis adresser au vendeur "
                       "une demande écrite de retour dans les dix jours ouvrables."),
        "informations_non_etablies": [],
    },
    {
        "id": "CONSO_3_INFORMATION_PREALABLE",
        "domaine": "consommation",
        "numero_texte": "2016-412",
        "article": "3",
        "titre": "Information à communiquer avant la conclusion du contrat",
        "declencheurs": ["information avant achat", "le vendeur ne m'a rien dit",
                         "caractéristiques du produit", "prix affiché", "informations obligatoires",
                         "vendeur qui cache", "conditions de vente"],
        "lecture": ("Avant la conclusion d'un contrat de vente ou de fourniture de service, le "
                    "professionnel doit communiquer de façon lisible les caractéristiques du bien ou "
                    "du service, le prix, le délai de livraison ou d'exécution, son identité et les "
                    "garanties applicables."),
        "faits_requis": [["contrat_conclu", "Le contrat est-il déjà conclu ?"],
                         ["information_recue", "Quelles informations le professionnel vous a-t-il remises ?"]],
        "etape_plan": ("Rassembler les documents remis avant l'achat (devis, bon de commande, publicité) "
                       "et comparer avec la liste d'informations que l'article 3 impose."),
        "informations_non_etablies": [],
    },
    {
        "id": "CONSO_6_RETARD_LIVRAISON",
        "domaine": "consommation",
        "numero_texte": "2016-412",
        "article": "6",
        "titre": "Retard de livraison : dénonciation du contrat au-delà de sept jours",
        "declencheurs": ["retard de livraison", "je n'ai pas reçu ma commande", "livraison en retard",
                         "produit jamais livré", "date de livraison dépassée", "annuler ma commande"],
        "lecture": ("Lorsque la livraison n'est pas immédiate et que le prix dépasse un seuil fixé par "
                    "décret, le professionnel doit indiquer une date limite ; le consommateur peut "
                    "dénoncer le contrat par lettre recommandée si le dépassement excède sept jours, "
                    "sauf force majeure."),
        "faits_requis": [["prix_achat", "Quel est le prix de la commande ?"],
                         ["date_prevue", "Quelle date de livraison avait été indiquée ?"]],
        "etape_plan": ("Vérifier la date limite annoncée, puis adresser une lettre recommandée avec "
                       "accusé de réception dénonçant le contrat."),
        "informations_non_etablies": [
            "Le seuil de prix à partir duquel l'article 6 s'applique est fixé par décret pris en "
            "Conseil des Ministres : ce décret n'est pas dans le corpus. INFORMATION_NON_ETABLIE.",
        ],
    },
    {
        "id": "CONSO_45_RETRACTATION_OFFRE",
        "domaine": "consommation",
        "numero_texte": "2016-412",
        "article": "45",
        "titre": "Rétractation dans les dix jours suivant l'acceptation de l'offre",
        "declencheurs": ["je veux me rétracter", "rétractation", "annuler mon achat",
                         "j'ai signé une offre", "délai de réflexion", "changer d'avis"],
        "lecture": ("L'acceptation de l'offre résulte de sa signature, précédée de la mention "
                    "manuscrite « lu et approuvé », de la date et du lieu ; le consommateur peut se "
                    "rétracter dans les mêmes formes pendant dix jours à compter de l'envoi de "
                    "l'offre acceptée, sans indemnité ni frais, hors frais tarifés déjà engagés."),
        "faits_requis": [["offre_signee", "Avez-vous signé une offre ?"],
                         ["date_envoi", "À quelle date l'offre acceptée a-t-elle été envoyée ?"]],
        "etape_plan": ("Retrouver l'offre signée et sa date d'envoi, puis notifier la rétractation "
                       "par écrit dans les mêmes formes que l'acceptation."),
        "informations_non_etablies": [],
    },
    {
        "id": "CONSO_62_PRATIQUE_TROMPEUSE",
        "domaine": "consommation",
        "numero_texte": "2016-412",
        "article": "62",
        "titre": "Pratique commerciale trompeuse",
        "declencheurs": ["publicité mensongère", "on m'a menti sur le produit", "fausse promotion",
                         "produit différent de la publicité", "prix barré faux", "arnaque",
                         "pratique trompeuse", "allégations fausses"],
        "lecture": ("Une pratique commerciale est trompeuse lorsqu'elle crée une confusion avec un "
                    "autre bien, service ou signe distinctif, ou lorsqu'elle repose sur des "
                    "allégations fausses ou de nature à induire en erreur, notamment sur l'existence, "
                    "la nature ou les caractéristiques essentielles du bien ou du service."),
        "faits_requis": [["preuve_publicite", "Disposez-vous de la publicité ou de l'annonce (capture, tract) ?"],
                         ["ecart", "En quoi le produit reçu diffère-t-il de ce qui était annoncé ?"]],
        "etape_plan": ("Conserver la publicité et la preuve d'achat, puis signaler la pratique au "
                       "service compétent ; l'article 62 énumère les circonstances, il ne fixe pas "
                       "lui-même de démarche."),
        "informations_non_etablies": [
            "L'article 62 définit la pratique trompeuse. La sanction et l'autorité compétente figurent "
            "dans d'autres articles de la loi, non retenus dans cette fiche : INFORMATION_NON_ETABLIE ici.",
        ],
    },
    {
        "id": "CONSO_96_SERVICE_APRES_VENTE",
        "domaine": "consommation",
        "numero_texte": "2016-412",
        "article": "96",
        "titre": "Service après-vente et information sur la réparation",
        "declencheurs": ["service après-vente", "réparation", "panne", "sav",
                         "réparation forfaitaire", "pièces remplacées"],
        "lecture": ("Le service après-vente couvre les services fournis après la vente ; lorsque le "
                    "professionnel facture une réparation forfaitaire, il doit informer par écrit "
                    "l'acheteur de l'origine de la panne, de la nature de l'intervention et des "
                    "pièces remplacées."),
        "faits_requis": [["facture", "La réparation a-t-elle été facturée ?"],
                         ["ecrit_recu", "Avez-vous reçu une information écrite sur la panne ?"]],
        "etape_plan": ("Réclamer par écrit l'information sur l'origine de la panne et les pièces "
                       "remplacées, en joignant la facture."),
        "informations_non_etablies": [],
    },
    # ---------------------------------------------------------------- associations
    {
        "id": "ASSO_7_DECLARATION",
        "domaine": "associations_organisations_religieuses",
        "numero_texte": "2024-368",
        "article": "7",
        "titre": "Déclaration préalable d'une organisation de la société civile",
        "declencheurs": ["créer une association", "déclarer une association", "monter une association",
                         "association non déclarée", "association cultuelle", "ong", "déclaration en préfecture"],
        "lecture": ("Une OSC doit faire l'objet d'une déclaration préalable à la direction compétente "
                    "du ministère en charge de l'Administration du Territoire, à la préfecture ou à "
                    "la sous-préfecture du siège social ; la déclaration est écrite, sur papier libre "
                    "ou en ligne, et fait connaître la nature, le titre, l'objet, l'adresse, le siège "
                    "et les responsables."),
        "faits_requis": [["siege", "Où se situe le siège social de l'association ?"],
                         ["forme", "S'agit-il d'une association, d'une ONG ou d'une organisation cultuelle ?"]],
        "etape_plan": ("Préparer la déclaration écrite indiquant la nature, le titre, l'objet, le "
                       "siège et les responsables, puis la déposer à la préfecture ou à la "
                       "sous-préfecture du siège."),
        "informations_non_etablies": [],
    },
    {
        "id": "ASSO_10_PIECES_DOSSIER",
        "domaine": "associations_organisations_religieuses",
        "numero_texte": "2024-368",
        "article": "10",
        "titre": "Pièces à joindre à la déclaration",
        "declencheurs": ["pièces du dossier association", "quels documents pour créer une association",
                         "dossier de déclaration", "statuts à joindre", "création asso documents"],
        "lecture": ("La déclaration est accompagnée de la preuve du paiement du droit de dépôt, de "
                    "trois exemplaires des statuts et du règlement intérieur signés, de trois "
                    "exemplaires du procès-verbal de l'assemblée générale constitutive, et de trois "
                    "exemplaires de la liste des membres fondateurs et de celle des membres de "
                    "l'organe de direction."),
        "faits_requis": [["assemblee_constitutive", "Une assemblée générale constitutive a-t-elle eu lieu ?"],
                         ["statuts_rediges", "Les statuts sont-ils rédigés et signés ?"]],
        "etape_plan": ("Réunir les pièces en trois exemplaires chacune (statuts, règlement intérieur, "
                       "procès-verbal constitutif, listes des fondateurs et des dirigeants) et "
                       "s'acquitter du droit de dépôt."),
        "informations_non_etablies": [
            "Le montant du droit de dépôt est fixé par voie réglementaire : ce texte n'est pas dans "
            "le corpus. INFORMATION_NON_ETABLIE.",
        ],
    },
    {
        "id": "ASSO_11_CONTENU_STATUTS",
        "domaine": "associations_organisations_religieuses",
        "numero_texte": "2024-368",
        "article": "11",
        "titre": "Contenu obligatoire des statuts",
        "declencheurs": ["rédiger les statuts", "statuts d'association", "que doivent contenir les statuts",
                         "modifier les statuts", "objet de l'association"],
        "lecture": ("Les statuts contiennent le titre, l'objet, la durée, l'adresse et le siège "
                    "social, les conditions d'acquisition et de perte de la qualité de membre, "
                    "l'origine des ressources financières, les règles d'organisation et de "
                    "fonctionnement, les pouvoirs des dirigeants, le quorum et la fréquence des "
                    "sessions de l'organe suprême, ainsi que les conditions de modification des "
                    "statuts et de dissolution."),
        "faits_requis": [["statuts_existants", "Des statuts existent-ils déjà ?"],
                         ["objet_asso", "Quel est l'objet de l'association ?"]],
        "etape_plan": ("Comparer les statuts rédigés à la liste de l'article 11 et compléter les "
                       "mentions absentes avant le dépôt."),
        "informations_non_etablies": [],
    },
    {
        "id": "ASSO_55_UTILITE_PUBLIQUE",
        "domaine": "associations_organisations_religieuses",
        "numero_texte": "2024-368",
        "article": "55",
        "titre": "Conditions pour être reconnue d'utilité publique",
        "declencheurs": ["reconnaissance d'utilité publique", "utilité publique",
                         "devenir association reconnue", "agrément utilité publique"],
        "lecture": ("Pour être reconnue d'utilité publique, une OSC régulièrement déclarée doit "
                    "fonctionner depuis au moins cinq ans, regrouper au moins cent membres adhérents, "
                    "jouir d'une influence dépassant le cadre de la région, exécuter une mission "
                    "d'intérêt général à caractère non lucratif, respecter des principes "
                    "démocratiques de gestion et justifier de ressources propres annuelles d'au "
                    "moins vingt millions de francs."),
        "faits_requis": [["anciennete", "Depuis combien d'années l'association fonctionne-t-elle ?"],
                         ["membres", "Combien de membres adhérents compte-t-elle ?"]],
        "etape_plan": ("Vérifier chacun des critères de l'article 55 (ancienneté, membres, "
                       "rayonnement, ressources propres) avant de présenter une demande."),
        "informations_non_etablies": [
            "La procédure et l'autorité qui prononce la reconnaissance d'utilité publique ne sont pas "
            "établies par l'article 55 : INFORMATION_NON_ETABLIE.",
        ],
    },
    {
        "id": "ASSO_133_MISE_EN_CONFORMITE",
        "domaine": "associations_organisations_religieuses",
        "numero_texte": "2024-368",
        "article": "133",
        "titre": "Associations créées sous la loi de 1960 : délai de mise en conformité",
        "declencheurs": ["association de 1960", "ancienne association", "mise en conformité",
                         "loi 60-315", "association existante nouvelle loi", "amende association"],
        "lecture": ("Les OSC constituées conformément à la loi n° 60-315 du 21 septembre 1960 doivent "
                    "se conformer à la présente ordonnance dans un délai de douze mois, sous peine "
                    "d'une amende d'un million de francs ; trois mois après le prononcé de l'amende, "
                    "la dissolution peut intervenir."),
        "faits_requis": [["date_creation", "À quelle date l'association a-t-elle été déclarée ?"],
                         ["conformite", "Une mise en conformité a-t-elle déjà été engagée ?"]],
        "etape_plan": ("Vérifier la date de déclaration initiale, puis engager la mise en conformité "
                       "auprès de l'autorité où la déclaration a été reçue."),
        "informations_non_etablies": [],
    },
]


def normaliser(texte):
    return " ".join((texte or "").split())


def citation(conn, numero_texte, article):
    ligne = conn.execute(
        """SELECT a.texte, a.sha256_article, a.origine_texte, a.recoupe, a.confiance_ocr,
                  j.titre_officiel, j.source_url, j.date_publication, j.etat_verification
             FROM articles_corpus a
             JOIN documents d ON d.doc_id = a.doc_id
             JOIN references_juridiques j ON j.ref_id = d.ref_id
            WHERE j.numero_texte = ? AND a.numero = ?""",
        (numero_texte, article),
    ).fetchone()
    if not ligne:
        raise SystemExit("article introuvable : %s art. %s" % (numero_texte, article))
    return ligne


def construire():
    conn = sqlite3.connect(CHEMIN_DB)
    fiches = []
    for modele in FICHES:
        texte, sha, origine, recoupe, confiance, titre_ref, url, date_pub, etat_ref = citation(
            conn, modele["numero_texte"], modele["article"]
        )
        corps = normaliser(texte)
        # L'OCR de la source colle parfois un tiret de mise en page en tête
        # d'article : il n'appartient pas à la disposition, il est retiré de la
        # citation. Le texte complet reste lisible dans le corpus.
        corps = re.sub(r"^[\s\u2010-\u2015\-]+", "", corps)
        fiche = {
            "id": modele["id"],
            "domaine": modele["domaine"],
            "numero_texte": modele["numero_texte"],
            "article": modele["article"],
            "titre": modele["titre"],
            "declencheurs": modele["declencheurs"],
            "citation": corps,
            "lecture": modele["lecture"],
            "faits_requis": modele["faits_requis"],
            "etape_plan": modele["etape_plan"],
            "informations_non_etablies": modele["informations_non_etablies"],
            "etat_verification": STATUT,
            "origine_texte": origine,
            "recoupe": bool(recoupe),
            "confiance_ocr": confiance,
            "sha256_article": sha,
            "reference": {
                "titre_officiel": titre_ref,
                "date_publication": date_pub,
                "url_source": url,
                "etat_reference": etat_ref,
            },
        }
        fiches.append(fiche)
    return fiches


def main():
    fiches = construire()
    contenu = {
        "genere_le": __import__("datetime").date.today().isoformat(),
        "statut": STATUT,
        "avertissement": (
            "Fiches préparées à partir des textes du corpus, NON validées par un juriste. "
            "Elles ne sont pas lues par le moteur : elles ne répondent à aucun citoyen."
        ),
        "fiches": fiches,
    }
    with open(SORTIE, "w", encoding="utf-8") as flux:
        json.dump(contenu, flux, ensure_ascii=False, indent=2)
        flux.write("\n")
    par_domaine = {}
    for fiche in fiches:
        par_domaine[fiche["domaine"]] = par_domaine.get(fiche["domaine"], 0) + 1
    print("  écrit : %s" % SORTIE)
    for domaine, nombre in sorted(par_domaine.items()):
        print("   %-46s %d fiches" % (domaine, nombre))
    print("   total : %d fiches, statut %s" % (len(fiches), STATUT))


if __name__ == "__main__":
    main()
