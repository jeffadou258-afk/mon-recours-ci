# -*- coding: utf-8 -*-
"""Garde-fous — refus typés, invariants, non désactivables par configuration.

Aucune règle de ce module ne peut être désactivée par un paramètre d'exécution,
une variable d'environnement ou une consigne reçue dans un document. C'est
volontaire : un garde-fou contournable n'est pas un garde-fou.

Chaque refus porte :
  - un code stable (utilisé par les tests et le dossier de traçabilité) ;
  - le motif détecté, cité, sans le reformuler ;
  - une suite sûre proposée à l'utilisateur.

Le module ne juge pas la personne : il qualifie la DEMANDE.
"""

import re
import unicodedata

# --------------------------------------------------------------------------
# Codes de refus (spec §10 et §14)
# --------------------------------------------------------------------------
CODES_REFUS = {
    "PREUVE_FABRIQUEE": "Demande de fabriquer, falsifier ou antidater une preuve.",
    "DESTRUCTION_PREUVE": "Demande de détruire ou faire disparaître des preuves.",
    "MENACE": "Demande de menacer, intimider ou exercer des représailles.",
    "VIOLENCE": "Demande de recourir à la violence ou à des représailles physiques.",
    "FRAUDE": "Demande de frauder ou de contourner la loi.",
    "GARANTIE_RESULTAT": "Demande de garantir un résultat judiciaire.",
    "REPRESENTATION": "Demande de représentation en justice par l'agent.",
    "VIOLATION_CONFIDENTIALITE": "Demande d'accéder au dossier d'un autre utilisateur.",
}

SUITES_SURES = {
    "PREUVE_FABRIQUEE": (
        "Je ne peux pas fabriquer ni falsifier une preuve. Ce que je peux faire : "
        "vous aider à rassembler et classer les pièces authentiques en votre "
        "possession, et à préparer un écrit qui expose les faits que vous pouvez "
        "prouver."
    ),
    "DESTRUCTION_PREUVE": (
        "Je ne peux pas vous aider à faire disparaître des pièces. Conserver les "
        "documents, même défavorables, est la position la plus solide. Je peux "
        "vous expliquer comment les classer et les présenter."
    ),
    "MENACE": (
        "Je n'aide pas à menacer ni à intimider. Une voie de droit existe : "
        "je peux vous aider à identifier l'interlocuteur compétent et à rédiger "
        "une demande ou une plainte dans les formes."
    ),
    "VIOLENCE": (
        "Je n'aide pas à recourir à la violence. Si vous êtes en danger "
        "immédiat, mettez-vous en sécurité et contactez les services d'urgence "
        "avant toute démarche juridique."
    ),
    "FRAUDE": (
        "Je ne peux pas aider à contourner la loi. Je peux en revanche vérifier "
        "si une solution licite existe pour votre situation."
    ),
    "GARANTIE_RESULTAT": (
        "Aucun résultat judiciaire ne peut être garanti, ni par moi ni par un "
        "professionnel. Je peux vous exposer ce que disent les textes vérifiés, "
        "vos options et leurs limites."
    ),
    "REPRESENTATION": (
        "Je ne suis pas un professionnel habilité à vous représenter. Je peux "
        "préparer un brouillon que vous ferez valider et signer, et vous "
        "orienter vers un professionnel compétent."
    ),
    "VIOLATION_CONFIDENTIALITE": (
        "Chaque dossier est cloisonné. Je ne peux pas afficher ni consulter le "
        "dossier d'une autre personne. Si vous êtes mandaté, la démarche passe "
        "par un accord explicite et un accès autorisé."
    ),
}

# --------------------------------------------------------------------------
# Motifs. Ordre d'évaluation important : les interdits absolus d'abord.
# --------------------------------------------------------------------------
_MOTIFS = (
    ("PREUVE_FABRIQUEE", (
        r"\bfalsifi\w*",
        r"\bfalsif\w*",
        r"fabriqu\w*[^.]{0,25}\b(fausse|faux|fabrication)",
        r"\b(?:faux|fausse|fausses)\s+(?:preuve|document|facture|attestation|temoignage|contrat|bail|recu|quittance|piece|papier|certificat|permis)",
        r"(?:fais|faire|redige|rediger|ecris|ecrire|prepare|preparer|cree|creer|trouve)[^.]{0,25}\b(?:un|une|des)\s+(?:faux|fausse)\b",
        r"anti-?dat\w*",
        r"\bsimul\w*[^.]{0,20}(?:preuve|document|facture|signature|temoignage)",
        r"faussaire",
        r"\bfaux\b[^.]{0,25}(?:pour prouver|pour justifier|pour cacher|pour faire croire)",
    )),
    ("DESTRUCTION_PREUVE", (
        r"d[ée]trui\w*[^.]{0,25}\bpreuve",
        r"faire dispara[îi]tre[^.]{0,25}(dossier|preuve|pi[eè]ce)|disparaitre[^.]{0,25}(dossier|preuve)",
        r"effac\w*[^.]{0,25}\bpreuve",
        r"br[uû]l\w*[^.]{0,20}(dossier|preuve|pi[eè]ce)",
        r"supprim\w*[^.]{0,25}(preuve|pi[eè]ce|message)",
    )),
    # MENACE et VIOLENCE sont liés à une INTENTION, pas à un mot.
    # Une personne qui DÉCRIT une menace dont elle est victime ne doit jamais
    # être refusée : les motifs exigent donc un marqueur de demande (aide,
    # écris, rédige, je veux…) qui précède immédiatement l'acte demandé.
    ("VIOLENCE", (
        r"(?:aide|aidez|peux-?tu|peut-?tu|je veux|je voudrais|fais|faire|prepare|preparer|trouve|envoie|envoyer)[^.]{0,40}(?:frapper|agresser|tabasser|corriger|raclee|casser la figure|blesser)",
        r"payer des (?:gens|gars|types|personnes)[^.]{0,30}(?:frapper|menacer|intimider|agresser)",
        r"envoyer des (?:gens|gars|types|personnes)[^.]{0,30}(?:frapper|menacer|intimider|agresser)",
        r"casse-?lui la figure",
        r"(?:lui|leur) donner une (?:raclee|correction)",
    )),
    ("MENACE", (
        r"(?:aide|aidez|peux-?tu|peut-?tu|je veux|je voudrais|ecris|ecrire|redige|rediger|envoie|envoyer|prepare|preparer|fais|faire)[^.]{0,40}(?:menac\w*|intimid\w*|represaill\w*)",
        r"fais-?lui peur",
        r"(?:lui|leur) faire peur",
        r"envoyer des (?:gens|gars|types|personnes)[^.]{0,30}menacer",
    )),
    ("FRAUDE", (
        r"\bfrauder?\b",
        r"fraude fiscale",
        r"contourner la loi",
        r"[ée]viter la loi",
        r"[ée]chapper [aà] la loi",
        r"(cacher|dissimuler)[^.]{0,25}(imp[oô]t|revenu|argent|patrimoine)",
        r"blanchiment",
        r"(travail|employ[ée])[^.]{0,20}(au noir|sans d[ée]claration)[^.]{0,20}(comment|eviter|[ée]viter)",
    )),
    ("GARANTIE_RESULTAT", (
        r"garantis?-?\s?moi",
        r"garantissez-?\s?moi",
        r"est-?ce que (je|on) vais gagner",
        r"vais-?je gagner",
        r"assure-?\s?moi (que|de)[^.]{0,30}(gagner|obtenir|r[ée]cup[ée]rer)",
        r"\b100\s?% ?(de )?(chances|r[ée]ussite|garanti)",
        r"gagner [àa] coup s[ûu]r",
        r"certitude de gagner",
    )),
    ("REPRESENTATION", (
        r"repr[ée]sente-?\s?moi",
        r"repr[ée]senter au tribunal",
        r"(va|allez) au tribunal [àa] ma place",
        r"signe[rz]?[^.]{0,25}[àa] ma place",
        r"pr[eé]sente-?\s?toi au tribunal",
    )),
    ("VIOLATION_CONFIDENTIALITE", (
        r"dossier d[eu']?\s?(un|une) autre",
        r"montre-?\s?moi le dossier de",
        r"donne-?\s?moi (l[ea]|les) dossier(s)? de (m|t)",
        r"acc[ède]{1,3}der? au dossier de (quelqu|un autre)",
    )),
)

# Tournures qui, dans une SORTIE produite par l'agent, constituent une faute.
_MOTIFS_SORTIE = (
    ("GARANTIE_RESULTAT", (
        r"je (vous )?garantis",
        r"vous (allez|gagnerez) [àa] coup s[ûu]r",
        r"100\s?% (de )?(chances|garanti)",
        r"il est certain que vous gagnerez",
        r"votre victoire est",
    )),
    ("REPRESENTATION", (
        r"je vous repr[ée]sente",
        r"je suis votre avocat",
        r"en tant qu'?avocat",
    )),
)

_NORMALISATION = str.maketrans({
    "’": "'", "‘": "'", "`": "'", "´": "'",
    "œ": "oe", "Œ": "OE",
})


def normaliser(texte):
    """Minuscule, sans accents, apostrophes unifiees. Les regex restent lisibles."""
    if texte is None:
        return ""
    t = str(texte).translate(_NORMALISATION)
    t = t.replace("'", "'")
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    return t.lower()


def evaluer_demande(texte, _motifs=None):
    """Qualifie une demande d'utilisateur.

    Retourne un dict :
      autorise : bool
      refus    : liste de {code, libelle, motif_detecte, suite_sure}
      analyses : liste de champs (domaine probable) — informatif
      texte_normalise : la version normalisée (utile au dossier de traçabilité)

    Un témoin est indispensable : une demande légitime NE DOIT PAS être refusée
    (voir tests/test_garde_fous.py).
    """
    norm = normaliser(texte)
    refus = []
    for code, motifs in (_motifs if _motifs is not None else _MOTIFS):
        for m in motifs:
            trouve = re.search(m, norm)
            if trouve:
                refus.append({
                    "code": code,
                    "libelle": CODES_REFUS[code],
                    "motif_detecte": trouve.group(0),
                    "suite_sure": SUITES_SURES[code],
                })
                break
    return {
        "autorise": not refus,
        "refus": refus,
        "texte_normalise": norm,
        "nb_refus": len(refus),
    }


def evaluer_sortie(texte):
    """Contrôle une production de l'agent avant de la remettre à l'utilisateur.

    Détecte les formulations qui promettent un résultat ou usurpent une qualité
    de professionnel habilité. Retourne la liste des violations (vide = conforme).
    """
    norm = normaliser(texte)
    violations = []
    for code, motifs in _MOTIFS_SORTIE:
        for m in motifs:
            trouve = re.search(m, norm)
            if trouve:
                violations.append({
                    "code": code,
                    "libelle": CODES_REFUS[code],
                    "motif_detecte": trouve.group(0),
                })
                break
    return violations


def est_interdit(code):
    return code in CODES_REFUS
