# -*- coding: utf-8 -*-
"""Scénarios d'audit des 24 domaines — partagés par le test et l'outil d'audit.

Pour chaque domaine, les 7 types de cas demandés :

  simple      cas correctement décrit
  courant     français courant, avec fautes
  clarif      cas qui exige des questions de clarification
  ambigu      cas vague : aucune réponse juridique prématurée
  hors        cas hors couverture : signalé honnêtement
  urgent      cas urgent (si le domaine peut mettre une personne en danger)
  abstention  le moteur ne doit fournir ni délai, ni article, ni procédure non vérifiés

`attendu` décrit le COMPORTEMENT voulu du service, jamais une solution de droit :
  etape            "clarification" | "hors_catalogue" | "refus"
  fiches           fiches qui doivent être servies (sous-ensemble)
  interdites       fiches qui ne doivent PAS être servies
  questions_min    nombre minimal de questions posées
  urgence_min      "ELEVEE" | "CRITIQUE"
  vision           code (1-24) du domaine qui doit être reconnu quand aucune fiche ne répond
  abstention       parcours complet + contrôle : aucun nombre (délai, montant, âge) absent
                   des articles cités ou du récit, aucune citation hors catalogue

Un type sans objet est noté `None` avec sa raison : il n'est pas compté comme exécuté.
Les récits sont rédigés pour ce test ; ils ne décrivent aucune personne réelle.
"""

NA = None


def cas(recit, **attendu):
    return {"recit": recit, "attendu": attendu}


def sans_objet(raison):
    return {"sans_objet": raison}


HORS = "hors_catalogue"
CLAR = "clarification"
PAS_DE_FICHE = "aucune fiche dans ce domaine : pas de cas de clarification possible"
PAS_DE_DANGER = "domaine sans risque typique pour la sécurité d'une personne"

SCENARIOS = {
    1: {
        "simple": cas("Mon voisin a construit un mur qui empiète sur ma parcelle, je veux des dommages et intérêts",
                      etape=HORS, vision=1),
        "courant": cas("mon voizin a cassé ma voiture et refuse de payer les domages et interets", etape=HORS, vision=1),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("j'ai un probleme avec quelqu'un", etape=HORS),
        "hors": cas("Je veux faire un bornage avec mon voisin", etape=HORS, vision=1),
        "urgent": cas("mon voisin me menace avec une machette", etape=HORS, urgence_min="CRITIQUE"),
        "abstention": cas("Quel est le délai de prescription pour réclamer une dette à un voisin ?",
                          etape=HORS, abstention=True),
    },
    2: {
        "simple": cas("Le père de mon enfant refuse de le reconnaître", etape=CLAR, fiches={"FAMILL_24"},
                      questions_min=1),
        "courant": cas("le pere de mon enfan refuse de le reconaitre", etape=CLAR, fiches={"FAMILL_24"}),
        "clarif": cas("Je suis le mari et je veux contester la paternité de l'enfant né pendant notre mariage",
                      etape=CLAR, fiches={"FAMILL_4"}, questions_min=1),
        "ambigu": cas("j'ai un souci avec mon mari", etape=HORS),
        "hors": cas("Je veux divorcer de mon mari", etape=HORS, vision=2),
        "urgent": cas("Mon mari frappe les enfants et me menace", urgence_min="CRITIQUE"),
        "abstention": cas("Combien de temps j'ai pour contester la paternité, quel délai ?", etape=CLAR,
                          fiches={"FAMILL_6"}, abstention=True),
    },
    3: {
        "simple": cas("Mon bailleur refuse de me rendre ma caution", etape=CLAR, fiches={"LOGEME_416"},
                      interdites={"CONTRA_4", "CONTRA_1"}, questions_min=2),
        "courant": cas("mon baileur veut pas me rendre ma caution", etape=CLAR, fiches={"LOGEME_416"}),
        "clarif": cas("Mon propriétaire veut augmenter mon loyer", etape=CLAR, fiches={"LOGEME_423"}, questions_min=1),
        "ambigu": cas("j'ai un problème avec mon propriétaire", etape=HORS),
        "hors": cas("Je loue une boutique et le propriétaire veut résilier mon bail commercial", vision=3),
        "urgent": cas("On veut m'expulser demain matin avec la police, le bailleur a changé les serrures",
                      etape=CLAR, fiches={"LOGEME_445"}, urgence_min="ELEVEE"),
        "abstention": cas("Dans combien de jours le bailleur doit me rendre ma caution ?", etape=CLAR,
                          fiches={"LOGEME_416"}, abstention=True),
    },
    4: {
        "simple": cas("Mon employeur ne me paie plus mon salaire depuis trois mois", etape=HORS, vision=4),
        "courant": cas("mon patron veu pas me payé mon salair", etape=HORS, vision=4),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("j'ai des soucis au travail", etape=HORS),
        "hors": cas("On m'a licencié sans préavis, ai-je droit à une indemnité ?", etape=HORS, vision=4),
        "urgent": cas("mon patron m'a frappé au travail et menace de me tuer", etape=HORS, urgence_min="CRITIQUE"),
        "abstention": cas("Combien de mois de salaire mon employeur doit-il me verser après un licenciement ?",
                          etape=HORS, abstention=True),
    },
    5: {
        "simple": cas("Je veux porter plainte pour vol de mon téléphone", etape=HORS, vision=5),
        "courant": cas("on ma volé mon telefone je veu porté plainte", etape=HORS, vision=5),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("la police me cherche", etape=HORS),
        "hors": cas("Quelle est la peine pour escroquerie ?", etape=HORS, vision=5),
        "urgent": cas("mon frere est en garde a vue depuis 3 jours sans avocat", etape=HORS, urgence_min="CRITIQUE"),
        "abstention": cas("Combien de temps la garde à vue peut-elle durer ?", etape=HORS, abstention=True),
    },
    6: {
        "simple": cas("Je veux créer une société et m'inscrire au registre du commerce", etape=HORS, vision=6),
        "courant": cas("je veu cree ma societe et avoir le rccm", etape=HORS, vision=6),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("mon associé ne veut plus travailler", etape=HORS),
        "hors": cas("Comment vendre mon fonds de commerce ?", etape=HORS, vision=6),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Quel capital minimum pour créer une société ?", etape=HORS, abstention=True),
    },
    7: {
        "simple": cas("J'ai acheté un téléphone défectueux et le vendeur refuse de me rembourser", etape=HORS,
                      vision=7),
        "courant": cas("le vendeur veu pa remboursé mon produit defectueux", etape=HORS, vision=7),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("je ne suis pas content de mon achat", etape=HORS),
        "hors": cas("Mon abonnement internet est facturé deux fois", etape=HORS, vision=7),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Combien de jours ai-je pour retourner un produit défectueux ?", etape=HORS, abstention=True),
    },
    8: {
        "simple": cas("La banque refuse de m'accorder un crédit", etape=HORS, vision=8),
        "courant": cas("la banque a bloqué mon compte bancaire sans raison", etape=HORS, vision=8),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("j'ai un souci d'argent", etape=HORS),
        "hors": cas("Le taux d'interet de mon credit a changé", etape=HORS, vision=8),
        "urgent": cas("une société de microfinance menace de saisir tous mes biens demain", etape=CLAR,
                      fiches={"OHADA_28"}, urgence_min="ELEVEE"),
        "abstention": cas("Quel est le taux d'interet maximum autorisé pour un crédit ?", etape=HORS,
                          abstention=True),
    },
    9: {
        "simple": cas("La mairie refuse de me délivrer un document administratif", etape=HORS, vision=9),
        "courant": cas("la mairi veu pa me donner mon papier, c'est l'administration", etape=HORS, vision=9),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("on m'a refusé quelque chose", etape=HORS),
        "hors": cas("Comment faire un recours administratif contre une décision ?", etape=HORS, vision=9),
        "urgent": cas("l'administration va démolir ma maison demain", urgence_min="ELEVEE"),
        "abstention": cas("Quel est le délai pour faire un recours administratif ?", etape=HORS, abstention=True),
    },
    10: {
        "simple": cas("La police a interdit notre manifestation pacifique", etape=HORS, vision=10),
        "courant": cas("on m'a empeché de voter a l'election", etape=HORS, vision=10),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("je trouve que c'est injuste", etape=HORS),
        "hors": cas("Que dit la constitution sur la liberté d'expression ?", etape=HORS, vision=10),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Quel article de la constitution protège la liberté de culte ?", etape=HORS,
                          abstention=True),
    },
    11: {
        "simple": cas("Les impôts me réclament une taxe que je ne dois pas", etape=HORS, vision=11),
        "courant": cas("les impots me demande de payé une patente", etape=HORS, vision=11),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("on me demande de l'argent", etape=HORS),
        "hors": cas("J'ai reçu un redressement fiscal", etape=HORS, vision=11),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Quel est le taux de la TVA ?", etape=HORS, abstention=True),
    },
    12: {
        "simple": cas("Mon assurance refuse d'indemniser mon sinistre", etape=HORS, vision=12),
        "courant": cas("l'assureur veu pa payé apres mon sinistre", etape=HORS, vision=12),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("on ne veut pas me payer", etape=HORS),
        "hors": cas("Mon assureur a résilié ma police d'assurance", etape=HORS, vision=12),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Dans quel délai l'assurance doit-elle payer après un sinistre ?", etape=HORS,
                          abstention=True),
    },
    13: {
        "simple": cas("Un policier m'a arrêté parce que je téléphonais en conduisant", etape=CLAR,
                      fiches={"TRANSP_2"}),
        "courant": cas("la police ma arreté car j'avais le telephone au volan", etape=CLAR, fiches={"TRANSP_2"}),
        "clarif": sans_objet("la fiche TRANSP_2 n'a pas de question de clarification dans le guide"),
        "ambigu": cas("j'ai un souci avec ma voiture", etape=HORS),
        "hors": cas("J'ai eu un accident de voiture, l'autre conducteur refuse de payer", etape=HORS, vision=13),
        "urgent": cas("accident de moto, mon frère est blessé et saigne beaucoup", urgence_min="CRITIQUE"),
        "abstention": cas("Quelle est l'amende pour le téléphone au volant ?", etape=CLAR, fiches={"TRANSP_2"},
                          abstention=True),
    },
    14: {
        "simple": cas("Quelqu'un a publié mes photos sur les réseaux sociaux sans mon accord", etape=HORS,
                      vision=14),
        "courant": cas("on a piraté mon compte facebook", etape=HORS, vision=14),
        "clarif": sans_objet("textes neutralisés (OCR non recoupé) : aucune fiche"),
        "ambigu": cas("j'ai un souci sur internet", etape=HORS),
        "hors": cas("Une entreprise utilise mes données personnelles sans mon accord", etape=HORS, vision=14),
        "urgent": cas("quelqu'un menace de publier mes photos intimes si je ne paie pas", urgence_min="CRITIQUE"),
        "abstention": cas("Quelle est la peine pour piratage informatique ?", etape=HORS, abstention=True),
    },
    15: {
        "simple": cas("L'hôpital refuse de me donner mon dossier médical", etape=HORS, vision=15),
        "courant": cas("le medecin a fait une erreur medicale sur mon operation", etape=HORS, vision=15),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("je ne suis pas bien soigné", etape=HORS),
        "hors": cas("La clinique me facture des soins que je n'ai pas reçus", etape=HORS, vision=15),
        "urgent": cas("mon enfant est très malade et l'hôpital refuse de le soigner sans payer",
                      urgence_min="ELEVEE"),
        "abstention": cas("Combien de temps l'hôpital doit-il garder mon dossier médical ?", etape=HORS,
                          abstention=True),
    },
    16: {
        "simple": cas("Le président de notre association refuse de convoquer l'assemblée générale", etape=HORS,
                      vision=16),
        "courant": cas("le tresorier de l'association a pris l'argent des cotisations", etape=HORS, vision=16),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("il y a des problèmes dans notre groupe", etape=HORS),
        "hors": cas("Comment déclarer une ONG ?", etape=HORS, vision=16),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Combien de membres faut-il pour créer une association ?", etape=HORS, abstention=True),
    },
    17: {
        "simple": cas("L'école a exclu mon enfant sans explication", etape=HORS, vision=17),
        "courant": cas("l'ecole veut pas inscrire mon enfant, les frais de scolarite sont trop cher", etape=HORS,
                       vision=17),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("mon fils a des problèmes", etape=HORS),
        "hors": cas("Mon fils a été recalé au BEPC, peut-on contester ?", etape=HORS, vision=17),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("À quel âge l'école est-elle obligatoire ?", etape=HORS, abstention=True),
    },
    18: {
        "simple": cas("Ma famille conteste mes droits sur une plantation de cacao au village", etape=HORS, vision=18),
        "courant": cas("on veut prendre mon champ au village, j'ai pas de certificat foncier", etape=HORS, vision=18),
        "clarif": sans_objet("loi 98-750 indexée (OCR non recoupé) mais aucune fiche"),
        "ambigu": cas("on se dispute pour une terre", etape=HORS),
        "hors": cas("Comment obtenir un certificat foncier ?", etape=HORS, vision=18),
        "urgent": cas("des gens armés sont venus occuper notre plantation", etape=HORS, urgence_min="CRITIQUE"),
        "abstention": cas("En combien de temps obtient-on un certificat foncier ?", etape=HORS, abstention=True),
    },
    19: {
        "simple": cas("L'État veut exproprier mon terrain pour une route", etape=CLAR, fiches={"LOGEME_238"}),
        # LIMITE CONNUE : « expropier » est à plus d'une lettre des déclencheurs ; le
        # service ne le reconnaît pas et le DIT (hors catalogue), sans fiche erronée.
        "courant": cas("l'etat veut m'expropier pour faire une route", etape=HORS),
        "clarif": sans_objet("les fiches 181, 238 et 69 n'ont pas de question de clarification dans le guide"),
        "ambigu": cas("on construit à côté de chez moi", etape=HORS),
        "hors": cas("Une usine pollue la rivière de notre village", etape=HORS, vision=19),
        "urgent": cas("les bulldozers vont détruire nos maisons demain pour le déguerpissement",
                      urgence_min="ELEVEE"),
        "abstention": cas("Combien l'État doit-il me payer pour l'expropriation ?", etape=CLAR,
                          fiches={"LOGEME_238"}, abstention=True),
    },
    20: {
        "simple": cas("Une entreprise a copié mon logo et ma marque", etape=HORS, vision=20,
                      interdites={"LOGEME_440"}),
        "courant": cas("on a copier ma musique sans payer, c'est de la contrefacon", etape=HORS, vision=20),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("on m'a volé mon idée", etape=HORS),
        "hors": cas("Comment déposer un brevet ?", etape=HORS, vision=20),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Combien d'années dure le droit d'auteur ?", etape=HORS, abstention=True),
    },
    21: {
        "simple": cas("Comment obtenir la nationalité ivoirienne ?", etape=HORS, vision=21),
        "courant": cas("ma carte de sejour a expiré", etape=HORS, vision=21),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("j'ai un problème de papiers", etape=HORS),
        "hors": cas("Je suis étranger, puis-je acheter un terrain ?", vision=21),
        "urgent": sans_objet("aucun cas urgent formulable sans inventer de procédure ; l'expulsion du "
                             "territoire est couverte par la détection générale"),
        "abstention": cas("Après combien d'années de mariage peut-on obtenir la nationalité ?", etape=HORS,
                          abstention=True),
    },
    22: {
        "simple": cas("Un enfant de mon quartier est maltraité par sa tutrice", etape=HORS, vision=22,
                      urgence_min="CRITIQUE"),
        "courant": cas("un enfan travaille dans les champs et va pas a l'ecole, c'est du travail des enfants",
                       etape=HORS, vision=22),
        "clarif": sans_objet("décrets 2023-89, 2023-90 et loi 2021-894 indexés mais aucune fiche"),
        "ambigu": cas("je m'inquiète pour un petit", etape=HORS),
        "hors": cas("Comment devenir famille d'accueil ?", etape=HORS, vision=22),
        "urgent": cas("un enfant est enfermé et battu chez mes voisins", etape=HORS, urgence_min="CRITIQUE"),
        "abstention": cas("Quel est l'âge minimum pour travailler ?", etape=HORS, abstention=True),
    },
    23: {
        "simple": cas("Mon ami m'a demandé de me porter caution pour son prêt bancaire", etape=CLAR,
                      fiches={"CONTRA_4"}, interdites={"LOGEME_416"}),
        # LIMITE CONNUE : « hypotequée » est à plus d'une lettre de « hypothèque » ; le
        # service reconnaît le domaine (23) et l'urgence, sans servir de fiche.
        "courant": cas("la banque veut saisir ma maison hypotequée", etape=HORS, vision=23,
                       urgence_min="ELEVEE"),
        "clarif": cas("J'ai reçu une ordonnance d'injonction de payer et je conteste la dette", etape=CLAR,
                      fiches={"OHADA_10"}, questions_min=1, urgence_min="ELEVEE"),
        "ambigu": cas("quelqu'un me doit de l'argent", etape=HORS),
        "hors": cas("Comment se passe la vente aux enchères d'un immeuble saisi ?", etape=HORS, vision=23),
        "urgent": cas("le commissaire de justice est devant ma porte pour saisir mes meubles",
                      urgence_min="CRITIQUE"),
        "abstention": cas("Combien de temps a le créancier pour vendre les biens saisis ?", abstention=True),
    },
    24: {
        "simple": cas("Je suis marié avec une étrangère et nous voulons divorcer à l'étranger", vision=24),
        "courant": cas("je veu faire reconnaitre un jugement etranger ici", etape=HORS, vision=24),
        "clarif": sans_objet(PAS_DE_FICHE),
        "ambigu": cas("ma famille est à l'étranger", etape=HORS),
        "hors": cas("Comment faire l'exequatur d'une décision étrangère ?", etape=HORS, vision=24),
        "urgent": sans_objet(PAS_DE_DANGER),
        "abstention": cas("Quel est le délai pour une adoption internationale ?", etape=HORS, abstention=True),
    },
}

TYPES = ("simple", "courant", "clarif", "ambigu", "hors", "urgent", "abstention")
