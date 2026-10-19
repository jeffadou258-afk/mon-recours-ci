# -*- coding: utf-8 -*-
"""Étape 1 et 2 — Qualification de la demande et collecte ciblée des faits.

Ce module route et questionne. Il ne dit JAMAIS ce que dit la loi : c'est le
rôle de core/analyse.py, alimenté par des références vérifiées.

Deux sorties :
  * `qualifier(texte)` : domaines juridiques probables (scores + incertitude),
    nature de la demande, urgence déléguée à core/urgence.py ;
  * `questions_a_poser(...)` : les questions dont la réponse MANQUE, une seule
    fois, sans questionnaire-fleuve.

Aucun délai, aucune sanction, aucune procédure n'est mentionné ici.
"""

import re

from config import DOMAINES_JURIDIQUES
from core.garde_fous import normaliser
from core.urgence import detecter as detecter_urgence

# Mots-clés de routage (taxonomie, pas du droit).
_MOTS_CLES = {
    "logement_baux_foncier": (
        "bail", "bailleur", "locataire", "loyer", "caution", "expulsion", "logement",
        "maison", "terrain", "foncier", "proprietaire", "titre foncier", "acd", "quittance",
        "etat des lieux", "syndic", "copropriete", "construction", "permis de construire",
        "depot de garantie", "expropriation", "exproprier", "domaine public", "urbanisme",
        "deguerpissement", "lotissement", "expulser",
    ),
    "travail": (
        "employeur", "salarie", "contrat de travail", "licenciement", "salaire", "paie",
        "preavis", "cdd", "cdi", "conge", "patron", "inspection du travail", "cnps",
        "heures supplementaires", "faute", "mise a pied", "solde de tout compte",
    ),
    "famille_mariage_filiation": (
        "mariage", "divorce", "separation", "enfant", "filiation", "pension alimentaire",
        # « garde » SEUL ne suffit pas : « mon bailleur garde ma caution » n'est pas une
        # question de garde d'enfant. Il faut la formulation complète — même leçon que
        # « menace » / « menacer » : un mot courant ne doit pas capturer un domaine.
        "garde des enfants", "droit de garde", "garde alternee", "garde exclusive",
        "residente", "dot", "concubinage", "adoption", "tutelle", "succession", "heritage",
        "acte de mariage", "autorite parentale",
        # État civil : le texte de référence (loi n° 2018-862) est rangé dans ce
        # domaine dans le corpus. « naissance » seul reste trop large.
        "etat civil", "acte de naissance", "declaration de naissance",
        "declarer la naissance", "reconnaitre l'enfant", "reconnaissance de l'enfant",
        "paternite", "desaveu", "desavouer",
    ),
    "contrats_dettes_commerce": (
        "contrat", "dette", "pret", "facture", "impaye", "remboursement", "creancier",
        "debiteur", "societe", "commercant", "bail commercial", "reconnaissance de dette",
        "cheque", "traite", "garantie", "interet",
        "porter caution", "cautionnement", "pret bancaire", "hypotheque", "nantissement",
        "surete", "suretes", "ohada",
        "injonction de payer", "saisie", "saisie attribution", "saisie sur salaire",
        "saisie des remunerations", "titre executoire", "formule executoire", "huissier",
        "commissaire de justice", "mesure conservatoire",
    ),
    "penal_procedure_penale": (
        "plainte", "police", "gendarmerie", "vol", "escroquerie", "agression", "infraction",
        "procureur", "garde a vue", "violence", "arnaque", "menace", "diffamation",
        "corruption", "stupéfiant", "stupefiant", "detention",
    ),
    "consommation": (
        "achat", "produit defectueux", "garantie", "remboursement", "fournisseur",
        "abonnement", "service", "prix", "publicite trompeuse", "panne", "reparation",
    ),
    "associations_organisations_religieuses": (
        "association", "eglise", "mosquee", "culte", "ong", "statuts", "assemblee generale",
        "agrement", "pasteur", "imam", "fidele", "paroisse",
    ),
    "donnees_personnelles_numerique": (
        "donnees personnelles", "artci", "internet", "reseaux sociaux", "image", "vie privee",
        "photo", "diffusion", "usurpation", "compte bloque", "harcèlement numerique",
        "harcelement numerique",
    ),
    # Domaines présents dans config.DOMAINES_JURIDIQUES mais sans mots-clés
    # jusqu'au 19/10/2026 : ils ne pouvaient JAMAIS être reconnus (audit).
    "transport_responsabilite_civile": (
        "accident", "conduite", "conducteur", "volant", "permis de conduire", "code de la route",
        "telephone au volant", "taxi", "gbaka", "moto", "vehicule", "responsabilite civile",
        "dommages et interets",
    ),
    "sante_droits_usagers": (
        "hopital", "clinique", "medecin", "erreur medicale", "dossier medical", "soins",
        "patient", "pharmacie", "infirmier", "cmu",
    ),
    "administratif_voies_de_recours": (
        "mairie", "prefecture", "permis", "etat civil", "acte de naissance", "service public",
        "recours administratif", "impots", "taxe", "amende", "fonctionnaire", "administration",
        "dossier refuse", "decision",
    ),
}

# Nature de la demande (spec §5).
_NATURES = (
    ("comprendre_un_document", ("comprendre", "explique", "signification", "que veut dire",
                                "j'ai recu", "je viens de recevoir", "il m'a donne")),
    ("preparer_une_demarche", ("comment faire", "comment proceder", "quelle demarche",
                               "je veux faire", "preparer", "ecrire", "rediger")),
    ("connaitre_ses_droits", ("ai-je le droit", "est-ce legal", "mes droits", "que dit la loi",
                              "suis-je oblige", "a-t-il le droit")),
    ("verifier_une_affirmation", ("est-il vrai", "on m'a dit que", "verifier", "c'est vrai que")),
    ("suivre_un_dossier", ("mon dossier", "ou en est", "suivi", "relance")),
    ("situation_de_conflit", ("conflit", "litige", "different", "conteste", "refuse",
                              "ne veut pas", "m'a chasse", "m'a pousse")),
)


def _distance_un(gauche, droite):
    """Vrai si les deux mots diffèrent d'au plus une opération.

    Bornée volontairement à 1 : au-delà, on rapprocherait des mots sans rapport
    et le routage deviendrait une devinette. Sert à comprendre « baeilleur »
    pour « bailleur » — l'utilisateur n'a pas à écrire correctement pour être
    compris.
    """
    if gauche == droite:
        return True
    if abs(len(gauche) - len(droite)) > 1:
        return False
    if len(gauche) > len(droite):
        gauche, droite = droite, gauche
    if len(gauche) == len(droite):
        return sum(1 for a, b in zip(gauche, droite) if a != b) <= 1
    i = j = ecarts = 0
    while i < len(gauche) and j < len(droite):
        if gauche[i] == droite[j]:
            i += 1
            j += 1
        else:
            ecarts += 1
            j += 1
            if ecarts > 1:
                return False
    return True


# Mots très courants qui ne doivent JAMAIS servir de troncature : « pas » ne
# désigne pas « pasteur », « mon » pas « monnaie ». Constaté : « il n'a pas
# d'acte de naissance » orientait vers les associations religieuses.
_MOTS_VIDES = frozenset((
    "pas", "mon", "ton", "son", "mes", "tes", "ses", "nos", "vos", "les", "des", "une",
    "par", "pour", "sur", "est", "ont", "sont", "dit", "fait", "tout", "tous", "elle",
    "ils", "nous", "vous", "que", "qui", "car", "mais", "donc", "avec", "sans", "dans",
    "chez", "plus", "moins", "tres", "bien", "peu", "ans", "jour", "mois", "fois",
))


def _mot_approchant(mot, mots_du_texte):
    """Mot du texte approchant un mot-clé, ou None.

    Deux ponts seulement, et tous deux exigeants :
      * troncature — « bai » pour « bail » (le mot-clé commence par le mot saisi) ;
      * une faute — « baeilleur » pour « bailleur », sur les mots de 5 lettres
        ou plus uniquement.
    """
    if len(mot) < 4:
        return None
    for candidat in mots_du_texte:
        if (len(candidat) >= 3 and len(candidat) < len(mot) and mot.startswith(candidat)
                and candidat not in _MOTS_VIDES):
            return candidat
    for candidat in mots_du_texte:
        if (len(candidat) >= 4 and len(mot) >= 4 and candidat.startswith(mot)):
            return candidat
        if len(candidat) >= 5 and len(mot) >= 5 and _distance_un(candidat, mot):
            return candidat
    return None


def qualifier(texte):
    """Route une demande. Retourne domaines, nature, urgence, et ce qui est incertain.

    Un mot-clé reconnu « de près » (faute de frappe, troncature) compte pour un
    demi-point : le routage reste prudent, mais il ne perd plus une situation de
    logement parce que l'utilisateur a écrit « bai » au lieu de « bail ».
    """
    norm = normaliser(texte)
    mots_du_texte = set(re.findall(r"[a-z0-9']+", norm))
    scores = {}
    for domaine, mots in _MOTS_CLES.items():
        score = 0
        detectes = []
        for mot in mots:
            if mot in norm:
                score += 1
                detectes.append(mot)
                continue
            if " " in mot:
                continue
            approchant = _mot_approchant(mot, mots_du_texte)
            if approchant:
                score += 0.5
                detectes.append("%s~%s" % (mot, approchant))
        if score:
            scores[domaine] = {"score": score, "mots_detectes": detectes}

    domaines = sorted(scores.items(), key=lambda kv: (-kv[1]["score"], kv[0]))
    domaines_retenus = [d for d, _ in domaines[:3]] or ["indetermine"]

    nature = "indetermine"
    for nom, motifs in _NATURES:
        if any(m in norm for m in motifs):
            nature = nom
            break

    return {
        "domaines_probables": domaines_retenus,
        "scores_domaines": {d: v for d, v in domaines},
        "nature_demande": nature,
        "urgence": detecter_urgence(texte),
        "domaines_possibles_nombre": len(scores),
        "ambiguite_domaine": len(scores) == 0 or (len(scores) > 1 and
                                                 domaines[0][1]["score"] == domaines[1][1]["score"]),
        "note": (
            "Les domaines listés sont des pistes de routage. Ils ne constituent "
            "pas une qualification juridique."
        ),
    }


# Questions procédurales dont la réponse manque souvent. Aucune n'affirme
# un droit ni un délai : elles cherchent un élément de fait.
_QUESTIONS_BASE = (
    ("dates", "Quelles sont les dates exactes des faits (réception, signature, refus) ?"),
    ("ecrit", "Existe-t-il un écrit (contrat, lettre, reçu, message) ? Si oui, de quelle date ?"),
    ("montants", "Y a-t-il des montants en jeu ? Lesquels, et sont-ils justifiés par une pièce ?"),
    ("demarches", "Quelles démarches ont déjà été faites, et quelles réponses ont été reçues ?"),
    ("objectif", "Quel est votre objectif concret (obtenir, contester, faire cesser, être indemnisé) ?"),
)

_QUESTIONS_DOMAINE = {
    "logement_baux_foncier": (
        ("qualite", "Êtes-vous locataire, bailleur, occupant sans titre, ou propriétaire ?"),
        ("caution", "Un dépôt de garantie a-t-il été versé, et un reçu existe-t-il ?"),
        ("etat_des_lieux", "Un état des lieux a-t-il été établi, signé des deux parties ?"),
    ),
    "travail": (
        ("contrat", "Quelle est la forme du contrat (écrit, verbal, CDD, CDI, durée) ?"),
        ("anciennete", "Quelle est la date d'embauche et la date de fin éventuelle ?"),
        ("ecrits_employeur", "Avez-vous reçu un écrit de l'employeur (lettre, notification, message) ?"),
    ),
    "famille_mariage_filiation": (
        ("situation", "Quel est l'état civil de chacun et le régime du mariage s'il existe ?"),
        ("enfants", "Y a-t-il des enfants ? Quel est leur âge et qui les a en charge ?"),
        ("decision", "Existe-t-il une décision ou une convention écrite déjà établie ?"),
    ),
    "contrats_dettes_commerce": (
        ("preuve_dette", "Quelle pièce matérialise la dette (reconnaissance, facture, contrat) ?"),
        ("echeance", "Quelle est la date d'exigibilité indiquée sur la pièce ?"),
        ("relances", "Des relances écrites ont-elles été envoyées ? À quelle date ?"),
    ),
    "penal_procedure_penale": (
        ("depot", "Une plainte a-t-elle été déposée ? Où et à quelle date ?"),
        ("pieces", "Quelles pièces avez-vous (certificat, captures, témoignages, reçus) ?"),
        ("statut", "Y a-t-il une convocation, une audition ou une décision en cours ?"),
    ),
    "consommation": (
        ("preuve_achat", "Quelle pièce prouve l'achat (facture, ticket, capture de commande) ?"),
        ("reclamation", "Une réclamation écrite a-t-elle été adressée au vendeur ?"),
    ),
    "associations_organisations_religieuses": (
        ("statuts", "Disposez-vous des statuts ou du règlement intérieur de l'organisation ?"),
        ("decision_contestee", "Quelle décision est contestée, par qui, et à quelle date ?"),
    ),
    "donnees_personnelles_numerique": (
        ("support", "Sur quel support la donnée ou l'image a-t-elle été publiée ?"),
        ("demande_retrait", "Une demande de retrait a-t-elle été adressée à l'auteur ou à la plateforme ?"),
    ),
    "administratif_voies_de_recours": (
        ("decision", "Quelle est la décision contestée, sa date et son auteur ?"),
        ("notification", "Comment vous a-t-elle été notifiée (remise, courrier, affichage) ?"),
    ),
}


def questions_a_poser(domaines, elements_connus=()):
    """Questions à poser : base + domaine, en retirant ce qui est déjà fourni.

    `elements_connus` est une liste de clés (ex. ["dates", "ecrit"]). Une clé
    connue retire la question correspondante — on ne repose pas une question.
    """
    connus = set(elements_connus or ())
    questions = []
    for cle, question in _QUESTIONS_BASE:
        if cle not in connus:
            questions.append({"cle": cle, "question": question, "origine": "base"})
    for domaine in domaines or []:
        for cle, question in _QUESTIONS_DOMAINE.get(domaine, ()):
            if cle not in connus:
                questions.append({"cle": cle, "question": question, "origine": domaine})
    return questions


def domaines_valides():
    return list(DOMAINES_JURIDIQUES)
