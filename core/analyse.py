# -*- coding: utf-8 -*-
"""Étape 3 et 4 — Analyse structurée et VALIDATION anti-invention.

Séparation stricte des quatre natures d'énoncé (spec §3, §9, §16) :

    FAIT       ce que l'utilisateur déclare ou ce qu'une pièce établit
    REGLE      ce que dit un texte — TOUJOURS rattaché à une référence vérifiée
    ANALYSE    l'application raisonnée de la règle aux faits
    HYPOTHESE  une piste, étiquetée, avec ce qu'il faudrait pour la conclure

`valider()` est le garde mécanique du module. Il refuse :

  REGLE_SANS_SOURCE            une règle sans ref_id
  REF_INCONNUE                 un ref_id qui n'existe pas dans le corpus
  REF_VIDE                      un ref_id sans aucun texte ni article enregistré
  APPLICATION_SANS_REGLE       une analyse qui n'appuie sur aucune règle
  APPLICATION_SANS_FAIT        une analyse rattachée à aucun fait
  HYPOTHESE_SANS_CONDITION     une hypothèse sans « ce qu'il faudrait pour conclure »
  CITATION_NON_VERIFIABLE      une citation absente de l'extrait enregistré
  INCERTITUDE_NON_DECLAREE     une règle fondée sur une référence non vérifiée,
                               sans incertitude déclarée nommant cette référence

La validation ne juge pas le fond : elle vérifie la traçabilité. C'est ce qui
rend l'exactitude vérifiable au lieu d'être affirmée.
"""

import re

from core.base import normaliser, verifier_citation

CODES_VIOLATION = {
    "REGLE_SANS_SOURCE": "Une règle est énoncée sans référence.",
    "REF_INCONNUE": "La référence citée n'existe pas dans le corpus.",
    "REF_VIDE": "La référence existe mais ne porte aucun contenu enregistré.",
    "APPLICATION_SANS_REGLE": "L'analyse applique une règle qu'elle ne cite pas.",
    "APPLICATION_SANS_FAIT": "L'analyse ne rattache pas la règle aux faits du dossier.",
    "HYPOTHESE_SANS_CONDITION": "Hypothèse sans condition de conclusion.",
    "CITATION_NON_VERIFIABLE": "Citation absente du texte enregistré.",
    "INCERTITUDE_NON_DECLAREE": "Règle fondée sur une référence non vérifiée, sans incertitude déclarée.",
    "DOMAINE_INDETERMINE": "Aucun domaine retenu : la conclusion ne peut pas être formée.",
    "NOMBRE_NON_SOUTENU": "Un nombre (montant, quantité, durée) ne figure ni dans les faits ni dans la référence citée.",
    "AUCUNE_REFERENCE_VERIFIEE": "Aucune règle appuyée sur une référence du corpus.",
    "AUCUNE_APPLICATION_AUX_FAITS": "Les règles ne sont appliquées à aucun fait du dossier.",
}


def nouvelle_analyse(dossier_id, domaines=None):
    return {
        "dossier_id": dossier_id,
        "domaines": list(domaines or []),
        "regles": [],
        "applications": [],
        "hypotheses": [],
        "incertitudes": [],
        "limites": [],
        "validite": None,      # rempli par valider()
        "violations": [],
    }


def ajouter_regle(analyse, ref_id, enonce, articles=None, citation=None):
    """Ajoute une règle rattachée à une référence. `enonce` = paraphrase, jamais une citation."""
    if citation and not re.search(r"[\"«]", citation):
        # Une citation est un passage entre guillemets : on l'exige explicite
        # pour distinguer le texte de la paraphrase.
        raise ValueError("une citation doit être délimitée par des guillemets")
    regle = {
        "ref_id": ref_id,
        "enonce": enonce,
        "articles": articles,
        "citation": citation,
    }
    analyse["regles"].append(regle)
    return regle


def ajouter_application(analyse, enonce, ref_ids, faits_ids):
    application = {
        "enonce": enonce,
        "ref_ids": list(ref_ids or []),
        "faits_ids": list(faits_ids or []),
    }
    analyse["applications"].append(application)
    return application


def ajouter_hypothese(analyse, enonce, pour_conclure):
    hypothese = {"enonce": enonce, "pour_conclure": pour_conclure, "statut": "NON_VERIFIEE"}
    analyse["hypotheses"].append(hypothese)
    return hypothese


def declarer_incertitude(analyse, ref_id, description):
    incertitude = {"ref_id": ref_id, "description": description}
    analyse["incertitudes"].append(incertitude)
    return incertitude


def declarer_limite(analyse, description):
    analyse["limites"].append(description)
    return description


def _nombres(texte):
    """Nombres présents dans un texte, espaces de milliers neutralisées.

    « 50 000 FCFA » et « 50000 FCFA » produisent le même jeton.
    """
    if not texte:
        return set()
    t = str(texte)
    t = re.sub(r"(?<=\d)[\s\u00a0\u202f](?=\d)", "", t)
    return set(re.findall(r"\d+(?:[.,]\d+)?", t))


def valider(analyse, references=None, faits_texte=""):
    """Retourne la liste des violations et renseigne `analyse['validite']`.

    `references` : dict ref_id -> ligne de référence (core.base.obtenir_reference).
    Si une règle cite un ref_id absent de ce dict, c'est REF_INCONNUE.

    `faits_texte` : concaténation des libellés de faits du dossier. Fourni, il
    active le contrôle anti-invention de nombres : tout nombre énoncé dans une
    règle ou une application doit se retrouver dans les faits OU dans la
    référence citée. Un délai ou un montant inventé est donc mécaniquement
    refusé, sans jugement sémantique.
    """
    references = references or {}
    violations = []

    def violer(code, detail):
        violations.append({"code": code, "libelle": CODES_VIOLATION[code], "detail": detail})

    if not analyse.get("domaines") or analyse["domaines"] == ["indetermine"]:
        violer("DOMAINE_INDETERMINE", "domaines = %r" % (analyse.get("domaines"),))

    refs_utilisees = []
    for regle in analyse["regles"]:
        ref_id = regle.get("ref_id")
        if not ref_id:
            violer("REGLE_SANS_SOURCE", "règle %r" % (regle.get("enonce", "")[:60],))
            continue
        refs_utilisees.append(ref_id)
        ref = references.get(ref_id)
        if ref is None:
            violer("REF_INCONNUE", ref_id)
            continue
        contenu = " ".join(str(ref.get(k) or "") for k in ("articles", "extrait_texte", "titre_officiel"))
        if not contenu.strip():
            violer("REF_VIDE", ref_id)
        if regle.get("citation"):
            ok, raison = _verifier_citation_depuis_ref(ref, regle["citation"])
            if not ok:
                violer("CITATION_NON_VERIFIABLE", "%s : %s" % (ref_id, raison))

    for application in analyse["applications"]:
        if not application.get("ref_ids"):
            violer("APPLICATION_SANS_REGLE", application.get("enonce", "")[:60])
        for ref_id in application.get("ref_ids", []):
            if ref_id not in [r.get("ref_id") for r in analyse["regles"]]:
                violer("APPLICATION_SANS_REGLE",
                       "règle %s utilisée mais non énoncée" % ref_id)
        if not application.get("faits_ids"):
            violer("APPLICATION_SANS_FAIT", application.get("enonce", "")[:60])

    for hypothese in analyse["hypotheses"]:
        if not (hypothese.get("pour_conclure") or "").strip():
            violer("HYPOTHESE_SANS_CONDITION", hypothese.get("enonce", "")[:60])

    # Une règle portée par une référence non vérifiée EXIGE une incertitude
    # déclarée qui la nomme. Sinon l'analyse se lit comme définitive.
    refs_incertaines_declarees = {i.get("ref_id") for i in analyse["incertitudes"]}
    for ref_id, ref in references.items():
        if ref_id in refs_utilisees and ref.get("etat_verification") != "VERIFIE":
            if ref_id not in refs_incertaines_declarees:
                violer("INCERTITUDE_NON_DECLAREE",
                       "%s est en état %s" % (ref_id, ref.get("etat_verification")))

    # Contrôle anti-invention de nombres (montants, quantités, durées).
    if faits_texte:
        support = _nombres(faits_texte)
        for ref in references.values():
            support |= _nombres(ref.get("extrait_texte"))
            support |= _nombres(ref.get("articles"))
            support |= _nombres(ref.get("numero_texte"))
            support |= _nombres(ref.get("titre_officiel"))
            support |= _nombres(ref.get("date_publication"))
        for source, enonces in (
            ("règle", [r.get("enonce", "") for r in analyse["regles"]]),
            ("application", [a.get("enonce", "") for a in analyse["applications"]]),
            ("hypothèse", [h.get("enonce", "") for h in analyse["hypotheses"]]),
        ):
            for enonce in enonces:
                for nombre in sorted(_nombres(enonce) - support):
                    violer(
                        "NOMBRE_NON_SOUTENU",
                        "%s %r : le nombre %s n'apparaît ni dans les faits ni dans une "
                        "référence citée" % (source, enonce[:60], nombre),
                    )

    analyse["violations"] = violations
    analyse["validite"] = "CONFORME" if not violations else "REFUSEE"
    return violations


def peut_conclure(analyse, references=None):
    """L'analyse peut-elle porter une conclusion ? (bool, raisons).

    On ne conclut pas sur une analyse refusée, ni sans règle appuyée sur une
    référence, ni sans application aux faits. L'absence est NOMMÉE.
    """
    raisons = []
    violations = analyse.get("violations")
    if violations is None:
        violations = valider(analyse, references=references)
    for violation in violations:
        raisons.append("%s : %s" % (violation["code"], violation["detail"]))
    if not analyse.get("regles"):
        raisons.append("AUCUNE_REFERENCE_VERIFIEE : %s"
                       % CODES_VIOLATION["AUCUNE_REFERENCE_VERIFIEE"])
    if not analyse.get("applications"):
        raisons.append("AUCUNE_APPLICATION_AUX_FAITS : %s"
                       % CODES_VIOLATION["AUCUNE_APPLICATION_AUX_FAITS"])
    return (not raisons), raisons


def _verifier_citation_depuis_ref(ref, citation):
    """Même contrôle que core.base.verifier_citation, sans accès disque."""
    if not ref.get("texte_complet_present"):
        return False, "texte intégral non présent : citation non vérifiable"
    extrait = ref.get("extrait_texte") or ""
    if not extrait:
        return False, "aucun extrait enregistré"
    if normaliser(citation) in normaliser(extrait):
        return True, "citation retrouvée dans l'extrait enregistré"
    return False, "citation absente de l'extrait enregistré"


def exiger_conformite(analyse, references=None):
    """Comme `valider`, mais lève si l'analyse n'est pas conforme.

    Utilisée par l'orchestrateur : aucune analyse non conforme ne sort vers
    l'utilisateur.
    """
    violations = valider(analyse, references=references)
    if violations:
        detail = " ; ".join("%s (%s)" % (v["code"], v["detail"]) for v in violations)
        raise ValueError("analyse refusée par la validation : %s" % detail)
    return analyse
