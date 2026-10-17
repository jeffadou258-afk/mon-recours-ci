#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Démonstration sur corpus réel : l'agent répond, avec références vérifiables.

Situation : un locataire à qui le bailleur réclame trois mois d'avance et une
caution de quatre mois, puis menace d'expulser pour un paiement tardif.

Toutes les règles énoncées ci-dessous sont tirées d'articles RÉELLEMENT indexés
depuis un PDF officiel téléchargé. Le script :

  1. ouvre le dossier (qualification, urgence, questions, verrous) ;
  2. recherche dans le corpus et affiche les articles trouvés avec leur source ;
  3. construit une analyse dont chaque règle porte le numéro d'article réel ;
  4. la VALIDE (traçabilité) et vérifie qu'une conclusion est possible ;
  5. montre les contrôles qui refusent une règle inventée ;
  6. écrit le dossier de traçabilité.

Usage :  python3 bin/demonstration_corpus.py
"""

import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402
from agent import MonRecoursCI  # noqa: E402
from core import analyse as A  # noqa: E402
from core import base, corpus  # noqa: E402

DOMAINE = "logement_baux_foncier"
DOSSIER = "DEMO_CORPUS_BAIL"

DEMANDE = ("Mon bailleur exige trois mois de loyer d'avance et une caution de quatre mois. "
           "J'ai payé mon loyer en retard le mois dernier et il dit qu'il va me faire "
           "expulser. Que dit la loi ivoirienne dans ma situation ?")


def ligne(titre):
    print()
    print("=" * 74)
    print(titre)
    print("=" * 74)


def main():
    agent = MonRecoursCI()

    ligne("ÉTAT DU CORPUS")
    resume = corpus.rapport(domaine=DOMAINE)
    print("Documents : %d (exploitables %d, scans non lisibles %d) | articles : %d"
          % (resume["nb_documents"], resume["nb_documents_exploitables"],
             resume["nb_documents_scans_seulement"], resume["nb_articles_indexes"]))
    for doc in resume["documents"]:
        print("  [%s] %-52s %3d art. | %s" % ("TEXTE" if doc["exploitable"] else "SCAN ",
                                             doc["titre"][:52], doc["articles_indexes"],
                                             doc["sha256"][:22]))
    integrite = corpus.verifier_integrite()
    print("Intégrité : %s (%d empreintes conformes)" % (integrite["verdict"], len(integrite["conformes"])))

    ligne("ÉTAPES 1-2 · QUALIFICATION")
    print("Demande : %s" % DEMANDE)
    dossier = agent.ouvrir_dossier(DOSSIER, DEMANDE, elements_connus=["objectif"])
    print("Statut   : %s" % dossier["statut"])
    print("Urgence  : %s (%s)" % (dossier["urgence"]["niveau"], dossier["urgence"]["priorite"]))
    for declencheur in dossier["urgence"]["declencheurs"]:
        print("   - %r" % declencheur["libelle"])
    print("Domaines : %s" % ", ".join(dossier["qualification"]["domaines_probables"]))
    print("Références candidates trouvées dans le corpus : %d"
          % len(dossier["references_candidates"]))
    print("Verrous humains : %s"
          % (", ".join(v["motif_code"] for v in dossier["verrous_humains"]) or "aucun"))

    ligne("ÉTAPE 3 · RECHERCHE DANS LE CORPUS RÉEL")
    for terme in ("caution dépôt de garantie", "expulsion loyer impayé", "congé bailleur trois mois"):
        resultats = corpus.chercher_articles(terme, domaine=DOMAINE, limite=3)
        print("« %s » -> %d article(s)" % (terme, len(resultats)))
        for r in resultats:
            print("   art. %-6s %-46s %s" % (r["numero"], r["titre"][:46], r["sha256"][:16]))

    ref_id = None
    for ref in base.lister_references(domaine=DOMAINE):
        if ref["numero_texte"] == "2019-576" and ref["etat_verification"] == "VERIFIE":
            ref_id = ref["ref_id"]
            reference = ref
    if ref_id is None:
        print("RÉFÉRENCE VÉRIFIÉE INTROUVABLE — abandon honnête.")
        return 3

    ligne("ÉTAPE 4 · ANALYSE DOCUMENTÉE")
    print("Référence : %s" % reference["titre_officiel"])
    print("Source    : %s" % reference["source_url"][:96])
    print("Consultée : %s | état : %s" % (reference["date_consultation"],
                                          reference["etat_verification"]))

    analyse = A.nouvelle_analyse(DOSSIER, [DOMAINE])
    regles = (
        ("415", "La conclusion du bail à usage d'habitation ne peut être liée au paiement "
                "de sommes autres que celles prévues par le sous-titre, et le bailleur ne "
                "peut exiger plus de deux mois de loyers d'avance."),
        ("416", "Le dépôt de garantie ne peut excéder deux mois de loyer ; un état des lieux "
                "écrit et contradictoire doit être signé au plus tard le jour de l'entrée "
                "en jouissance."),
        ("423", "Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans."),
        ("445", "Lorsque le locataire manque à ses obligations, le bailleur peut demander "
                "l'expulsion forcée devant le juge des référés, sans respecter le délai de "
                "contestation de la résiliation."),
        ("440", "Le bailleur qui souhaite reprendre son immeuble doit donner congé au "
                "locataire au moins trois mois avant la date de reprise, par acte de "
                "Commissaire de justice ou remise de courrier contre décharge."),
    )
    for numero, enonce in regles:
        A.ajouter_regle(analyse, ref_id, enonce, articles="Article %s" % numero)
        controle = corpus.verifier_regle_article(ref_id, numero, enonce)
        print("  art. %-5s énoncé %-26s (%d car. d'article)"
              % (numero, "SOUTENU" if controle["ok"] else "NON SOUTENU",
                 len(corpus.obtenir_article_par_reference(ref_id, numero)["texte"])))
    A.ajouter_regle(analyse, ref_id,
                    "Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans.",
                    articles="Article 423",
                    citation="« Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans. »")
    A.ajouter_application(
        analyse,
        "L'exigence de trois mois d'avance et d'une caution de quatre mois dépasse les "
        "plafonds fixés par les articles 415 et 416 ; la reprise du logement est en outre "
        "soumise au congé de trois mois de l'article 440, et l'expulsion à une décision "
        "de justice (article 445).",
        ref_ids=[ref_id], faits_ids=["F01"])

    references = {ref_id: reference}
    violations = A.valider(analyse, references=references)
    conforme, raisons = A.peut_conclure(analyse, references=references)
    print("Validité  : %s | violations : %d" % (analyse["validite"], len(violations)))
    for violation in violations:
        print("   - %s : %s" % (violation["code"], violation["detail"][:90]))
    print("Conclusion possible : %s" % conforme)
    for raison in raisons:
        print("   - %s" % raison)

    ligne("CONTRÔLES QUI REFUSENT L'INVENTION")
    citation_inventee = "le locataire a droit à une indemnité de cinq ans de loyer"
    ok_cit, raison_cit = base.verifier_citation(ref_id, citation_inventee)
    print("citation inventée         -> %s (%s)" % ("ACCEPTÉE" if ok_cit else "REFUSÉE",
                                                    raison_cit[:70]))
    controle = corpus.verifier_regle_article(ref_id, "423",
                                             "Le plafond est de 95000 FCFA par trimestre.")
    print("montant non soutenu       -> %s (%s)"
          % ("ACCEPTÉ" if controle["ok"] else "REFUSÉ", controle["raison"]))
    ok_ref, raison_ref = base.verifier_citation(ref_id, "« Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans. »")
    print("citation réellement citée -> %s" % ("ACCEPTÉE" if ok_ref else "REFUSÉE"))

    ligne("ÉTAPE 5 · CLÔTURE, PLAN ET TRAÇABILITÉ")
    cloture = agent.clore_dossier(DOSSIER, analyse)
    print("Statut de réponse : %s" % cloture["statut_reponse"])
    controles = cloture["controles_qualite"]
    print("Verrou bloquant les actions externes : %s"
          % ("non" if controles["actions_externes_autorisees"] else "OUI"))
    for raison in controles["raisons_verrous_ouverts"]:
        print("   - %s" % raison)
    print("Plan d'action : %d étapes" % cloture["plan"]["nb_etapes"])
    for etape in cloture["plan"]["etapes"]:
        print("   %d. [%s] %s" % (etape["numero"], etape["nature"], etape["objectif"]))
    trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
    print("Traçabilité : %s" % cloture["traceabilite"])
    print("Champs non renseignés : %s" % ", ".join(trace["champs_non_renseignes"]))
    print("Articles vérifiés : %s" % json.dumps(trace["articles_effectivement_verifies"],
                                                ensure_ascii=False)[:220])

    return 0 if (conforme and cloture["statut_reponse"] == "ANALYSE_CONFORME") else 4


if __name__ == "__main__":
    sys.exit(main())
