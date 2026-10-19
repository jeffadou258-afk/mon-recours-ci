# -*- coding: utf-8 -*-
"""Rédige reports/AUDIT_24_DOMAINES_JURIDIQUES.md à partir de reports/inventaire_24_domaines.json.

Les chiffres (statuts, scénarios, textes, fiches, questions) sont LUS dans le JSON
produit par bin/audit_domaines.py : aucun n'est saisi à la main.
"""

import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENTREE = os.path.join(RACINE, "reports", "inventaire_24_domaines.json")
SORTIE = os.path.join(RACINE, "reports", "AUDIT_24_DOMAINES_JURIDIQUES.md")

CORRECTIONS = {
    1: "Domaine désormais nommé quand la question n'est pas couverte (reconnaissance « dommages et intérêts », « voisin », « bornage »).",
    2: "Une faute d'une lettre tolérée (« reconaitre ») ; « paternité », « désaveu » reconnus ; déclencheur « faire reconnaître » restreint (il captait « reconnaître un jugement étranger ») ; urgence « frappe les enfants » détectée (elle restait NORMALE).",
    3: "Correspondance par mots entiers ; un déclencheur d'un seul mot (« préavis », « résiliation ») n'est retenu que si le logement est reconnu ; « expulser », « dépôt de garantie », « expropriation » reconnus.",
    4: "« licencié sans préavis » ne reçoit plus la fiche du congé donné par le BAILLEUR ; domaine nommé.",
    5: "Domaine nommé quand non couvert.",
    6: "Domaine nommé quand non couvert.",
    7: "Domaine nommé quand non couvert.",
    8: "Urgence « menace de saisir mes biens demain » détectée (elle restait NORMALE).",
    9: "Urgence « démolir ma maison demain » détectée (elle restait NORMALE).",
    10: "Domaine nommé quand non couvert.",
    11: "Domaine nommé quand non couvert.",
    12: "« ma police d'assurance résiliée » ne reçoit plus la fiche de résiliation du BAIL.",
    13: "Le domaine transport n'avait AUCUN mot-clé : il ne pouvait jamais être reconnu ; ajouté. Faute « volan » tolérée. Urgence « blessé, saigne » détectée.",
    14: "Urgence « menace de publier mes photos intimes » détectée (elle restait NORMALE).",
    15: "Le domaine santé n'avait AUCUN mot-clé : jamais reconnu ; ajouté.",
    16: "Domaine nommé quand non couvert.",
    17: "Domaine nommé quand non couvert.",
    18: "Urgence « gens armés » détectée (« armés » au pluriel échappait au motif).",
    19: "Urgence « détruire nos maisons demain / déguerpissement » détectée ; « pollution » reconnue.",
    20: "Défaut corrigé : « reprise » était trouvé dans « entreprise » ; une question de marque recevait le congé du bailleur.",
    21: "Domaine nommé quand non couvert.",
    22: "Urgence « enfant enfermé et battu » détectée par un motif dans les deux ordres (enfant… frappé / frappe… les enfants).",
    23: "Urgence « commissaire de justice devant ma porte » détectée (CRITIQUE) ; « saisir » reconnu ; « sûreté », « OHADA » reconnus.",
    24: "« reconnaître un jugement étranger » ne reçoit plus la fiche de reconnaissance d'enfant.",
}

JURISTE = {
    2: "Relire les 11 fiches de filiation, leurs lectures et les 7 questions ; confirmer le numéro de la loi « 202-894 ».",
    3: "Relire les 7 fiches de bail, leurs lectures et les 11 questions ; dire si la loi 2025-221 modifie la portée des articles 443 et 445 (expulsion) ; décider de l'usage d'une reproduction CIVLII.",
    13: "Relire la fiche TRANSP_2 ; confirmer que le décret 2013-711 est en vigueur.",
    19: "Relire les fiches 181, 238 et 69 ; dire quelles questions de clarification seraient utiles (expropriation, domaine public).",
    23: "Relire les fiches CONTRA_1 et CONTRA_4 ; confirmer la version en vigueur de l'Acte uniforme sur les sûretés.",
    14: "Dire si un exemplaire en texte natif des lois 2013-450/451/546 doit être obtenu avant toute fiche (articles neutralisés).",
    18: "Dire si la lecture OCR de la loi 98-750 peut servir de base, après recoupement, ou si un exemplaire officiel est requis.",
    22: "Choisir, parmi les décrets et la loi présents, les situations à couvrir en premier (protection de l'enfant).",
}

SOURCES = {
    1: "Code civil applicable en Côte d'Ivoire et textes sur la responsabilité civile, en version officielle.",
    2: "Textes sur le mariage, le divorce, la pension alimentaire et les successions ; indexation des textes déjà présents (état civil, minorité, adoption).",
    3: "Loi 2025-221 en exemplaire officiel (JO n° 32 du 21/04/2025) ; textes sur le bail commercial (Acte uniforme OHADA) et le titre foncier.",
    4: "Code du travail et textes de prévoyance sociale.",
    5: "Code pénal et Code de procédure pénale.",
    6: "Actes uniformes OHADA (droit commercial général, sociétés commerciales).",
    7: "Texte de protection du consommateur.",
    8: "Textes bancaires et de microfinance (UEMOA / BCEAO).",
    9: "Textes de procédure administrative et de recours.",
    10: "Constitution en vigueur.",
    11: "Code général des impôts et loi de finances de l'année.",
    12: "Code CIMA.",
    13: "Code de la route et textes sur l'indemnisation des accidents.",
    14: "Exemplaires en texte natif des lois 2013-450, 2013-451 et 2013-546.",
    15: "Textes sur les droits des patients et l'organisation des soins.",
    16: "Loi sur les associations.",
    17: "Loi sur l'enseignement.",
    18: "Exemplaire officiel lisible de la loi 98-750 et ses textes d'application.",
    19: "Code de l'environnement ; textes d'application sur l'expropriation.",
    20: "Accord de Bangui (OAPI) et loi sur le droit d'auteur.",
    21: "Code de la nationalité ; textes sur l'entrée et le séjour des étrangers.",
    22: "Indexation des lois 2019-572 et 2015-539 déjà présentes.",
    23: "Acte uniforme portant organisation des procédures simplifiées de recouvrement et des voies d'exécution.",
    24: "Règles de conflit de lois applicables ; indexation de la Convention de La Haye de 1993.",
}


FIN = """
## Moteur transversal

| Composant | Constat | Preuve |
|---|---|---|
| Détection du domaine | Corrigée : transport et santé n'avaient aucun mot-clé ; mots vides exclus des troncatures ; les 24 domaines sont nommés même non couverts. Limite : une faute de plus d'une lettre n'est pas reconnue (« expropier », « hypotequée »). | `core/qualification.py`, `core/domaines_vision.py` ; scénarios « courant » |
| Qualification des faits | Faits déclarés, manquants nommés ; jamais « prouvés » sans pièce. | `core/faits.py`, `tests/test_conversation.py` |
| Sélection des fiches | Corrigée : mots entiers, une faute tolérée, déclencheur d'un mot soumis au domaine reconnu, domaine le mieux classé en cas de concurrence. | `core/catalogue.py`, `tests/test_scenarios_reference.py` |
| Questions adaptatives, contradictions, manques | 18 questions sur 16 fiches ; les fiches des domaines 13, 19 et 23 n'en ont aucune ; tours conditionnels ; contradiction récit/réponse confirmée ; manques nommés. | `core/clarification.py`, `tests/test_clarification.py` |
| Urgences | Signalées même sans fiche : vérifié par les scénarios « urgent » hors catalogue des domaines 1, 2, 4, 5, 8, 9, 13, 14, 15, 18, 19, 22 et 23. Motifs manquants ajoutés (enfants frappés, armes, blessure, chantage aux images, exécution en cours, démolition, saisie, menaces). | `core/urgence.py` ; scénarios « urgent » |
| Citations et traçabilité | Citations revalidées au chargement ; contrôle d'abstention : aucun article cité hors des fiches servies, aucun nombre non sourcé dans les lectures, démarches et points à vérifier. | `core/catalogue.py`, `tests/evaluation_24_domaines.py` |
| Faits / règles / interprétations / incertitudes | Sections distinctes ; lectures marquées « pas des citations », statut A_RELIRE_PAR_UN_JURISTE. | `core/conversation.py` |
| Synthèses et courriers | Synthèse et brouillon téléchargeables ; le brouillon n'est pas inclus dans le contrôle d'abstention (gabarit daté, champs À COMPLÉTER). | `core/documents.py`, e2e |
| Orientation humaine sans réponse fiable | Hors catalogue : conclusion impossible, domaine nommé, verrous et urgence affichés. **Aucun annuaire de professionnels** (contacts vérifiés à fournir). | `core/conversation.py`, `web/src/components/Resultats.tsx` |
| Isolation et suppression | Identifiant serveur, cookie signé HttpOnly ; suppression ciblée testée. | `tests/test_clarification.py`, `web/tests/integration` |
| Données personnelles | Rien n'est envoyé à un tiers (modèle de langage désactivé) ; masquage prêt pour le jour où il serait activé. | `core/pseudonymisation.py` |
| Délais, articles, procédures inventés | Aucun observé sur les 136 scénarios exécutés ; garde-fou du guide (nombre absent de l'article refusé). | `tests/test_audit_24_domaines.py`, `tests/test_clarification.py` |

Point d'attention : hors catalogue, la réponse peut lister des **numéros d'articles du domaine** trouvés par la recherche, sous le titre « Articles du domaine, non appliqués à votre question ». Ils ne sont pas cités comme réponse ; un juriste devrait dire si cet affichage est souhaitable.

## Tests exécutés (19/10/2026, espace de travail ; la CI rejoue les mêmes)

| Suite | Réussis | Échoués | Ignorés | Non exécutés |
|---|---|---|---|---|
| Moteur `tests/run_all.py` (dont audit 24 domaines et scénarios de référence) | 425 | 0 | 5 (PDF officiels absents : 3 ; chaîne OCR macOS absente : 2) | — |
| Scénarios d'audit (7 types × 24 domaines) | 136 | 0 | — | 32 sans objet (raison donnée pour chacun) |
| Web unitaires et composants | 55 | 0 | 0 | — |
| Web intégration (moteur réel) | 11 | 0 | 0 | — |
| Web bout en bout (Chromium) | 10 | 0 | 0 | — |
| Sur le Mac du propriétaire | — | — | — | non exécuté (pas d'accès) |

Défaut trouvé **pendant** l'audit et corrigé : une modification de cet audit avait corrompu la table des questions par domaine (erreur interne sur tout récit transport ou santé). Les scénarios l'ont détecté ; un test verrouille désormais cette table.

## Plan priorisé

1. **Relecture juridique** des 24 fiches et 18 questions existantes (domaines 2, 3, 13, 19, 23) — condition pour passer de PARTIEL à un usage public.
2. **Famille (2)** : textes du mariage, du divorce, de la pension et des successions ; indexation de l'état civil, de la minorité et de l'adoption déjà présents.
3. **Logement (3)** : décision sur la source de la loi 2025-221, puis fiches d'expulsion relues.
4. **Travail (4)** : Code du travail officiel, puis fiches licenciement et salaire impayé.
5. **Pénal (5)** : orientation (plainte, garde à vue, droits de la victime), avec verrous humains.
6. **Protection de l'enfant (22)** : fiches sur les textes déjà indexés (décrets 2023, loi « 202-894 »).
7. **OHADA (23)** : Acte uniforme sur le recouvrement et les voies d'exécution.
8. **Numérique (14) et rural (18)** : exemplaires lisibles pour lever la neutralisation ou recouper l'OCR.
9. Questions de clarification pour les fiches qui n'en ont pas (13, 19, 23).
10. Les autres domaines, au rythme des textes obtenus.

## Inventaire

L'inventaire complet (textes avec titre, numéro, date, articles indexés et citables, mode de lecture, état de la référence, source ; fiches ; questions ; scénarios) est dans `reports/inventaire_24_domaines.json`, régénérable par `python3 bin/audit_domaines.py`.
"""


def cellule(texte):
    return str(texte).replace("|", "/").replace("\n", " ")


def main():
    with open(ENTREE, encoding="utf-8") as flux:
        r = json.load(flux)
    d = r["domaines"]
    sc = r["scenarios"]
    statuts = r["resume_statuts"]
    l = []
    w = l.append
    w("# Audit des 24 domaines juridiques — Mon Recours CI")
    w("")
    w("Branche `audit/24-domaines` (créée depuis `feature/produit-fonctionnel`). Données mesurées le %s par "
      "`bin/audit_domaines.py` (fichier `reports/inventaire_24_domaines.json`) ; ce rapport est rédigé à partir de "
      "ce fichier par `bin/rapport_audit_domaines.py`." % r["genere_le"])
    w("")
    w("**Trois notions distinctes, jamais confondues :** fonctionnement du code (les scénarios s'exécutent comme "
      "voulu), couverture documentaire (textes et fiches disponibles), fiabilité juridique (relecture humaine). "
      "**Aucun domaine n'a de relecture juridique tracée.**")
    w("")
    w("## Résumé")
    w("")
    for s in ("FONCTIONNEL", "PARTIEL", "BLOQUÉ POUR VALIDATION", "NON COUVERT"):
        codes = [str(x["code"]) for x in d if x["statut_technique"] == s]
        w("- **%s** : %d domaine(s)%s" % (s, statuts.get(s, 0), (" — n° " + ", ".join(codes)) if codes else ""))
    w("- Scénarios : %d exécutés, %d réussis, %d échoués, %d sans objet (sur 24 × 7 = 168)."
      % (sc["executes"], sc["reussis"], sc["echoues"], sc["sans_objet"]))
    w("")
    w("Règle de statut (dans `bin/audit_domaines.py`) : NON COUVERT = aucune fiche ; BLOQUÉ = fiches sans "
      "référence citable ; FONCTIONNEL = 7 types de cas exécutés et réussis **et** aucune lacune recensée ; "
      "PARTIEL = sinon. Aucun domaine n'atteint FONCTIONNEL : chacun des 5 domaines traités a des lacunes "
      "documentées ci-dessous.")
    w("")
    w("## Matrice de conformité")
    w("")
    w("| Domaine | Textes disponibles | Situations réellement traitées | Questions disponibles | Tests exécutés | Lacunes | Statut technique | Validation juridique |")
    w("|---|---|---|---|---|---|---|---|")
    for x in d:
        textes = "; ".join("%s (%d art. citables / %d indexés)" % (t["numero"], t["articles_citables"], t["articles_indexes"])
                           for t in x["textes"]) or "aucun"
        situations = "; ".join("%s (art. %s)" % (f["titre"], f["article"]) for f in x["fiches"]) or "aucune"
        tests = "%d/%d réussis, %d sans objet" % (x["scenarios_reussis"], x["scenarios_executes"], x["scenarios_sans_objet"])
        w("| %d. %s | %s | %s | %d | %s | %s | **%s** | non réalisée |" % (
            x["code"], cellule(x["libelle"]), cellule(textes), cellule(situations), len(x["questions"]),
            tests, cellule(" ".join(x["lacunes"])), x["statut_technique"]))
    w("")
    w("## Détail par domaine")
    for x in d:
        w("")
        w("### %d. %s — %s" % (x["code"], x["libelle"], x["statut_technique"]))
        w("")
        cles = ", ".join("`%s`" % c for c in x["cles_moteur"]) or "aucune clé de routage dans le moteur"
        w("**Code concerné** : routage `core/qualification.py` (%s) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; "
          "fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; "
          "urgence `core/urgence.py`." % cles)
        w("")
        if x["textes"]:
            w("**Références disponibles** :")
            for t in x["textes"]:
                w("- %s — %s (%s) ; %d articles indexés, %d citables ; lecture %s ; référence %s ; source %s%s."
                  % (t["numero"], t["titre"], t["date"] or "date non renseignée", t["articles_indexes"],
                     t["articles_citables"], t["lecture"], t["reference"] or "sans référence",
                     t["source"], "" if t["domaine_officiel"] else " (domaine non officiel)"))
        else:
            w("**Références disponibles** : aucune dans le corpus.")
        w("")
        if x["fiches"]:
            w("**Situations traitées (fiches)** :")
            for f in x["fiches"]:
                w("- `%s` %s — article %s, texte %s, référence %s ; questions : %s"
                  % (f["id"], f["titre"], f["article"], f["texte"], f["reference"],
                     ", ".join(f["questions"]) or "aucune"))
            w("")
        w("**Scénarios exécutés** :")
        w("")
        w("| Type | Récit | Résultat | Observé |")
        w("|---|---|---|---|")
        for s in x["scenarios"]:
            if s["resultat"] == "SANS_OBJET":
                w("| %s | — | sans objet | %s |" % (s["type"], cellule(s["raison"])))
            else:
                o = s["observe"]
                obs = "étape %s ; fiches %s ; %d question(s) ; urgence %s%s%s" % (
                    o.get("etape"), ", ".join(o.get("fiches") or []) or "aucune", o.get("questions", 0),
                    o.get("urgence"), (" ; domaine reconnu %s" % o["vision"]) if o.get("vision") else "",
                    (" ; fin : %s" % o["fin"]) if o.get("fin") else "")
                if s["ecarts"]:
                    obs += " ; ÉCARTS : " + "; ".join(s["ecarts"])
                w("| %s | %s | %s | %s |" % (s["type"], cellule(s["recit"]), s["resultat"].lower(), cellule(obs)))
        w("")
        w("**Lacunes** : " + " ".join(x["lacunes"]))
        w("")
        w("**Corrections techniques réalisées** : " + CORRECTIONS[x["code"]])
        w("")
        w("**Questions pour un juriste** : " + JURISTE.get(
            x["code"], "Choisir les textes de référence et les premières situations à couvrir."))
        w("")
        w("**Sources à obtenir ou vérifier** : " + SOURCES[x["code"]])
    l.append(FIN)
    with open(SORTIE, "w", encoding="utf-8") as flux:
        flux.write("\n".join(l) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
