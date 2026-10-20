# -*- coding: utf-8 -*-
"""Génère les définitions de fiches OHADA (AUPCAP 2015, AUSCOOP 2010).

Ce script ne crée aucune fiche : il produit les fichiers de définitions lus par
`bin/ajouter_fiches.py`, qui les revalide contre la base avant toute écriture.

Point clé : les bornes de citation sont EXTRAITES du texte indexé, jamais
retapées à la main. La recherche tolère les apostrophes typographiques
(’ / ‘ / ') parce que l'OCR mélange les deux ; la borne émise est ensuite la
sous-chaîne EXACTE du texte, faute de quoi `extraire_citation` la refuserait.

Chaque `lecture` sépare explicitement ce que le texte dit de ce qui reste une
interprétation à valider par un juriste.
"""

import json
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402

SORTIE = os.path.join(RACINE, "KNOWLEDGE", "fiches_sources")
APOSTROPHES = {"\u2019": "'", "\u2018": "'", "\u02bc": "'", "\u00b4": "'"}


def _normaliser(texte):
    for source, cible in APOSTROPHES.items():
        texte = texte.replace(source, cible)
    return texte


def _article(conn, numero_texte, numero):
    ligne = conn.execute(
        "SELECT a.texte FROM articles_corpus a JOIN documents d ON a.doc_id = d.doc_id "
        "WHERE d.numero_texte = ? AND a.numero = ? LIMIT 1", (numero_texte, str(numero))).fetchone()
    if ligne is None:
        raise SystemExit("article introuvable : %s art. %s" % (numero_texte, numero))
    return " ".join((ligne[0] or "").split())


def _bornes(texte, debut, fin):
    """Renvoie (debut_exact, fin_exact) tels qu'ils apparaissent dans le texte."""
    tn = _normaliser(texte)
    dn, fn = _normaliser(" ".join(debut.split())), _normaliser(" ".join(fin.split()))
    if tn.count(dn) != 1:
        raise SystemExit("borne de début absente ou ambiguë (%d) : %r" % (tn.count(dn), debut))
    i = tn.index(dn)
    j = tn.find(fn, i)
    if j < 0:
        raise SystemExit("borne de fin absente après le début : %r" % fin)
    # Même longueur avant/après normalisation : on peut découper le texte d'origine.
    return texte[i:i + len(dn)], texte[j:j + len(fn)]


AUPCAP = {
    "domaine": "contrats_dettes_commerce",
    "numero_texte": "AUPCAP-2015",
    "fiches": [
        {
            "id": "OHADA_AUPCAP_CESSATION",
            "article": "1",
            "titre": "Entreprise en cessation des paiements : définition",
            "declencheurs": ["cessation des paiements", "ne peut plus payer ses dettes",
                             "societe en difficulte", "entreprise en difficulte",
                             "redressement judiciaire", "liquidation des biens", "impayes entreprise"],
            "debut": "« cessation des paiements » : l",
            "fin": "lui permettent de faire face à son passif exigible",
            "lecture": ("Le texte définit la cessation des paiements comme l'impossibilité de faire face "
                        "au passif exigible avec l'actif disponible. Les crédits ou délais accordés par "
                        "les créanciers excluent cette qualification. Ce que le texte dit s'arrête là : "
                        "les conséquences procédurales (déclaration, délais, tribunal compétent) ne sont "
                        "pas établies par cet article et restent à vérifier. Interprétation à valider par "
                        "un juriste ; source OCR non recoupée."),
            "faits_requis": [["entreprise", "S'agit-il d'une entreprise, d'un commerçant ou d'une société "
                                            "(et non d'un particulier endetté) ?"]],
            "etape_plan": "Lister les dettes exigibles et l'actif disponible, puis consulter un professionnel",
        },
        {
            "id": "OHADA_AUPCAP_SALAIRES",
            "article": "95",
            "titre": "Salaires impayés : super privilège en cas de procédure collective",
            "declencheurs": ["salaires impayes", "super privilege", "privilège des salaires",
                             "employeur en liquidation", "employeur en redressement",
                             "salaire non paye procedure collective"],
            "debut": "Les créances résultant du contrat de travail",
            "fin": "par le super privilège des salaires",
            "lecture": ("Les créances nées du contrat de travail ou d'apprentissage sont garanties par le "
                        "super privilège des salaires lorsque l'employeur est en redressement judiciaire "
                        "ou en liquidation des biens. Le texte ne dit PAS ici comment déclarer la créance "
                        "ni dans quel délai : ces démarches ne sont pas établies par cet article. "
                        "Interprétation à valider par un juriste ; source OCR non recoupée."),
            "faits_requis": [["employeur_procedure", "Votre employeur fait-il l'objet d'une procédure "
                                                      "collective (redressement ou liquidation) ?"]],
            "etape_plan": "Réunir les bulletins de salaire et la preuve de la procédure collective",
        },
    ],
}

AUSCOOP = {
    "domaine": "contrats_dettes_commerce",
    "numero_texte": "AUSCOOP-2010",
    "fiches": [
        {
            "id": "OHADA_AUSCOOP_DEFINITION",
            "article": "4",
            "titre": "Qu'est-ce qu'une société coopérative",
            "declencheurs": ["cooperative", "societe cooperative", "creer une cooperative",
                             "cooperative agricole", "groupement cooperatif", "cooperative d'habitat"],
            "debut": "La société coopérative est un groupement autonome",
            "fin": "où le pouvoir est exercé démocratiquement et selon les principes coopératifs",
            "lecture": ("La coopérative est un groupement autonome de personnes volontairement réunies "
                        "pour satisfaire des besoins communs, dont la propriété et la gestion sont "
                        "collectives et le pouvoir exercé démocratiquement. Le texte ajoute qu'elle peut "
                        "traiter avec des usagers non coopérateurs dans les limites fixées par les "
                        "statuts. Les formalités de création ne sont pas traitées ici. Interprétation à "
                        "valider par un juriste ; source OCR non recoupée."),
            "faits_requis": [],
            "etape_plan": "Rassembler le projet de statuts et le nombre de coopérateurs fondateurs",
        },
        {
            "id": "OHADA_AUSCOOP_PARTS",
            "article": "208",
            "titre": "Parts sociales d'une coopérative",
            "declencheurs": ["parts sociales", "capital social cooperative", "part de cooperative",
                             "valeur nominale", "souscrire des parts"],
            "debut": "Le capital social est divisé en parts sociales égales",
            "fin": "dont la valeur nominale est fixée par les statuts",
            "lecture": ("Le capital d'une coopérative est divisé en parts sociales égales ; leur valeur "
                        "nominale est fixée par les statuts. Le texte ne fixe donc aucun montant : "
                        "chercher un chiffre légal serait une erreur. Interprétation à valider par un "
                        "juriste ; source OCR non recoupée."),
            "faits_requis": [],
            "etape_plan": "Lire les statuts pour la valeur nominale et le nombre de parts",
        },
        {
            "id": "OHADA_AUSCOOP_ENGAGEMENTS",
            "article": "62",
            "titre": "Coopérative : augmentation des engagements des coopérateurs",
            "declencheurs": ["augmentation des engagements", "engagements des cooperateurs",
                             "cooperative demande plus d'argent", "appel de fonds cooperative"],
            "debut": "Sauf décision contraire spécialement motivée",
            "fin": "ne peut être décidée sans leur consentement",
            "lecture": ("Aucune augmentation des engagements d'un coopérateur envers la société ne peut "
                        "être décidée sans son consentement, sauf décision contraire spécialement motivée "
                        "de la juridiction compétente statuant à bref délai. L'exception est étroite : "
                        "son application concrète relève du juge. Interprétation à valider par un juriste ; "
                        "source OCR non recoupée."),
            "faits_requis": [],
            "etape_plan": "Conserver la convocation et le procès-verbal de l'assemblée",
        },
        {
            "id": "OHADA_AUSCOOP_RESERVE",
            "article": "114",
            "titre": "Coopérative : réserve générale prélevée sur les excédents",
            "declencheurs": ["reserve generale", "excedents", "affectation des excedents",
                             "benefices cooperative", "ristourne cooperative"],
            "debut": "Les statuts prévoient, avant toute autre affectation",
            "fin": "excédents nets d'exploitation",
            "lecture": ("Les statuts doivent prévoir, avant toute autre affectation, la constitution d'une "
                        "réserve générale par prélèvements annuels sur les excédents nets d'exploitation. "
                        "Le taux et les autres affectations (dont l'éventuelle ristourne) ne sont pas "
                        "fixés par cet article. Interprétation à valider par un juriste ; source OCR "
                        "non recoupée."),
            "faits_requis": [],
            "etape_plan": "Demander les statuts et le rapport financier de l'exercice",
        },
    ],
}


def construire(conn, definition):
    resultat = {"domaine": definition["domaine"],
                "numero_texte": definition["numero_texte"], "fiches": []}
    for fiche in definition["fiches"]:
        texte = _article(conn, definition["numero_texte"], fiche["article"])
        debut, fin = _bornes(texte, fiche["debut"], fiche["fin"])
        resultat["fiches"].append({
            "id": fiche["id"], "article": fiche["article"], "titre": fiche["titre"],
            "declencheurs": fiche["declencheurs"],
            "citation_debut": debut, "citation_fin": fin,
            "lecture": fiche["lecture"], "faits_requis": fiche["faits_requis"],
            "etape_plan": fiche["etape_plan"]})
        extrait = texte[texte.index(debut):texte.index(fin) + len(fin)]
        print("  %-28s art.%-4s %3d car. : %s..." % (fiche["id"], fiche["article"],
                                                     len(extrait), extrait[:78]))
    return resultat


def main():
    os.makedirs(SORTIE, exist_ok=True)
    conn = sqlite3.connect(config.CHEMIN_DB)
    for nom, definition in (("ohada_procedures_collectives", AUPCAP),
                            ("ohada_cooperatives", AUSCOOP)):
        print("== %s (%s) ==" % (nom, definition["numero_texte"]))
        contenu = construire(conn, definition)
        chemin = os.path.join(SORTIE, nom + ".json")
        with open(chemin, "w", encoding="utf-8") as flux:
            json.dump(contenu, flux, ensure_ascii=False, indent=1)
            flux.write("\n")
        print("   écrit : %s (%d fiches)\n" % (os.path.relpath(chemin, RACINE), len(contenu["fiches"])))
    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
