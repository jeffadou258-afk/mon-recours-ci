# -*- coding: utf-8 -*-
"""Couverture juridique par domaine : un statut calcule, jamais declare.

Deux choses differentes, et il ne faut jamais les confondre :

  * la COUVERTURE TECHNIQUE — mesures lues dans la base : combien de documents,
    combien d'articles, par quelle methode de lecture, combien de references
    verifiees. C'est du calcul, pas une opinion ;
  * la COUVERTURE JURIDIQUE — ce que le corpus permet reellement d'affirmer, et
    ce qu'il ne permet pas. Cela ne se calcule pas : c'est declare, domaine par
    domaine, avec ses lacunes et les sources qui ont echoue.

`DECLARATIONS` ne contient que ce qui a ETE MESURE pendant la mission. Une source
qui n'a pas ete appelee n'y figure pas ; un obstacle constate y est ecrit avec son
resultat reel.

Le statut maximal atteignable sans relecture humaine est `TERMINE_TECHNIQUEMENT`.
`TERMINE_ET_VERIFIE` exige une validation humaine tracee : le module refuse de le
rendre tant qu'aucun article ne porte `VERIFIE_MANUELLEMENT`.
"""

import datetime

from config import COUVERTURE_DOMAINES, DOMAINES_JURIDIQUES, STATUTS_DOMAINE
from core import corpus

# --------------------------------------------------------------------------
# Declarations : perimetre vise, sources reellement interrogees, lacunes.
# --------------------------------------------------------------------------
DECLARATIONS = {
    "logement_baux_foncier": {
        "perimetre": [
            "bail d'habitation", "bail professionnel et commercial", "depot de garantie",
            "avances sur loyers", "revision et paiement des loyers", "reparations",
            "conge, resiliation et preavis", "impayes et procedures d'expulsion",
            "propriete immobiliere et titres fonciers", "litiges vendeur/acquereur",
            "conflits de limites et occupation de terrain", "lotissement et amenagement",
            "copropriete", "domaine public", "expropriation", "foncier rural et coutumier",
        ],
        "sources_tentees": [
            {"source": "sgg.gouv.ci", "resultat": "HTTP 200",
             "usage": "portail ; Journal officiel derriere identifiant"},
            {"source": "jorci.oneci.ci", "resultat": "HTTP 503 (maintenance)",
             "usage": "aucun Journal officiel consultable"},
            {"source": "biblio.cndj.ci", "resultat": "mur de connexion, acces payant",
             "usage": "respecte, non contourne"},
            {"source": "dgi.gouv.ci, construction.gouv.ci, sgg.gouv.ci/photo_doc",
             "resultat": "PDF telecharges", "usage": "textes effectivement collectes"},
        ],
        "lacunes": [
            "loi n° 2025-221 (contentieux des baux, execution des expulsions) absente : "
            "aucun exemplaire *.gouv.ci — voir KNOWLEDGE/05_LACUNE_LOI_2025_221.md",
            "textes d'application de la copropriete (decret 2013-225) non collectes",
            "modificatifs du foncier rural (loi 2019-868, ordonnance 2025-85) non collectes",
        ],
        "risque": "ELEVE — expulsion, perte du logement, delais de procedure",
        "validation_humaine": "systematique pour toute menace d'expulsion",
    },
    "famille_mariage_filiation": {
        "perimetre": [
            "mariage civil", "droits et obligations des epoux", "regimes matrimoniaux",
            "separation et divorce", "pension alimentaire", "autorite parentale",
            "garde et residence des enfants", "filiation et reconnaissance",
            "succession et heritage", "donation et partage", "violences familiales",
            "protection de l'enfance", "adoption",
        ],
        "sources_tentees": [
            {"source": "famille.gouv.ci (publications)",
             "resultat": "HTTP 200 — 15 textes juridiques telecharges",
             "usage": "corpus effectivement collecte"},
            {"source": "oneci.ci", "resultat": "HTTP 200",
             "usage": "texte de l'etat civil disponible"},
            {"source": "mffe.ci (site famille)", "resultat": "HTTP 200",
             "usage": "meme texte de loi que famille.gouv.ci"},
        ],
        "lacunes": [
            "loi n° 2019-570 (mariage) presente dans les recueils mais pas encore "
            "indexee comme texte autonome",
            "divorce et regimes matrimoniaux : textes non encore identifies sur un "
            "domaine officiel",
            "successions : aucun exemplaire officiel localise (loi 2019-573 non trouvee)",
            "les deux RECUEILS sont conserves mais volontairement NON indexes : on ne "
            "peut pas rattacher une disposition d'un recueil a son texte d'origine "
            "avec certitude",
            "5 des 11 scans ONT ETE REFUSES par l'OCR, et c'est ecrit sur chaque "
            "document : loi 2019-572 (minorite, 58% des articles 1..160), loi 2018-862 "
            "(etat civil, 49% des articles 1..113), loi 2015-539 (pupille de l'Etat, "
            "50% des articles 1..54) — ces textes MODIFIENT le Code de la famille et "
            "renvoient a des articles d'autres textes : leur decoupage en articles "
            "n'est pas fiable. Convention de La Haye (adoption) et loi relative a "
            "l'adoption : aucun article n'atteint le seuil de similarite 0,80 face a "
            "l'autre copie officielle — divergence a trancher par un humain.",
            "sur ces 5 textes, aucun article n'est citable : ni la loi sur la "
            "minorite, ni celle sur l'etat civil, ni le statut de pupille de l'Etat, "
            "ni les textes sur l'adoption. C'est une part importante du perimetre B "
            "qui reste hors de portee.",
        ],
        "risque": "CRITIQUE quand des enfants ou des personnes vulnerables sont concernes",
        "validation_humaine": "obligatoire des qu'un enfant est implique",
    },
    "donnees_personnelles_numerique": {
        "perimetre": [
            "escroqueries en ligne", "usurpation d'identite", "menaces numeriques",
            "diffusion non autorisee de contenus", "protection des donnees personnelles",
            "comptes compromis", "cyberharcelement", "preuves numeriques",
        ],
        "sources_tentees": [
            {"source": "autoritedeprotection.ci/lois/",
             "resultat": "HTTP 200 — 3 PDF directs : lois 2013-450, 2013-451, 2013-546 "
                         "(exemplaires du Journal officiel sécurisés en HTTP, pas en HTTPS)",
             "usage": "corpus effectivement collecté, lu par OCR (179 articles)"},
            {"source": "telecom.gouv.ci (publications)",
             "resultat": "HTTP 200 — 2 PDF identiques, tous deux copies du MÊME Journal "
                         "officiel que celui de l'autorité de protection des données",
             "usage": "doublon écarté : le corpus ne référence qu'un exemplaire"},
            {"source": "artci.ci", "resultat": "HTTP 200",
             "usage": "autorité de régulation identifiée, textes d'application à collecter"},
        ],
        "lacunes": [
            "les 3 lois proviennent d'OCR et ne sont RECOUPÉES AVEC AUCUNE autre copie "
            "officielle : leur fidélité n'est pas mesurable, seulement contrôlée "
            "structurellement. Statut `PARTIELLEMENT_VERIFIE`",
            "aucun texte d'application (décrets, décisions de l'autorité de protection, "
            "règlements de l'ARTCI) n'est collecté : la loi seule ne dit pas comment "
            "elle est mise en œuvre",
            "la loi 2013-451 (cybercriminalité) est un texte PÉNAL : elle engage la "
            "liberté des personnes et impose une orientation vers un avocat",
            "cyberharcèlement, usurpation d'identité en ligne et diffusion non autorisée "
            "de contenus ne sont pas adossés à un article spécifique du corpus",
            "preuves numériques : aucune règle de conservation ou d'identification n'est "
            "documentée par un texte collecté",
        ],
        "risque": "MOYEN a ELEVE",
        "validation_humaine": "recommandee en cas d'atteinte grave a la vie privee",
    },
    "travail": {
        "perimetre": [
            "contrat de travail", "periode d'essai", "salaire et retenues",
            "heures supplementaires et conges", "licenciement et demission",
            "preavis et indemnites", "harcelement et discrimination", "accidents du travail",
            "conflits employeur/salarie", "stages et apprentissage",
            "secteur prive / fonction publique / regimes speciaux",
        ],
        "sources_tentees": [
            {"source": "travail.gouv.ci", "resultat": "injoignable (HTTP 000, DNS)",
             "usage": "aucun texte collecte"},
            {"source": "recherche web restreinte aux domaines officiels",
             "resultat": "aucun exemplaire libre du Code du travail (loi 2015-532)",
             "usage": "blocage constate, non contourne"},
        ],
        "lacunes": [
            "Code du travail (loi n° 2015-532) : AUCUN exemplaire officiel libre localise",
            "convention collective interprofessionnelle : non localisee",
            "statut de la fonction publique : non localise (page ministerielle = HTML, "
            "pas de PDF de texte)",
        ],
        "risque": "ELEVE — perte de revenus, licenciement",
        "validation_humaine": "recommandee des la rupture du contrat",
    },
    "contrats_dettes_commerce": {
        "perimetre": [
            "creation et fonctionnement d'entreprise", "societes et entreprise individuelle",
            "relations entre associes", "contrats commerciaux", "factures et impayes",
            "recouvrement de creances", "responsabilite contractuelle",
            "rupture de contrat", "difficultes d'entreprise", "procedures collectives",
            "droit OHADA et articulation avec le droit ivoirien",
        ],
        "sources_tentees": [
            {"source": "ohada.org — Journal officiel OHADA n° 22 (15/02/2011)",
             "resultat": "HTTP 200 — Acte uniforme portant organisation des sûretés, "
                         "131 911 caractères extraits, 228 articles indexés",
             "usage": "corpus effectivement collecté et vérifié"},
            {"source": "commerce.gouv.ci (publications)",
             "resultat": "HTTP 200 — agenda des foires 2026 et rapport d'activités 2021 : "
                         "aucun texte de loi",
             "usage": "classés non juridiques, non indexés"},
            {"source": "justice.gouv.ci, gouv.ci", "resultat": "302 puis 403 sur les pages "
             "de publications", "usage": "aucun texte collecté"},
        ],
        "lacunes": [
            "SEUL l'acte uniforme sur les sûretés est présent. Manquent : AUSCGIE (sociétés "
            "commerciales et GIE), AUDCG (droit commercial général), AUPSRVE (recouvrement "
            "des créances), AUPC (procédures collectives)",
            "le Journal officiel OHADA n° 22 publie plusieurs actes : les articles indexés "
            "doivent être rattachés à l'acte sur les sûretés, pas aux autres",
            "aucun texte ivoirien sur l'entreprise individuelle, le registre du commerce ou "
            "les difficultés d'entreprise n'est collecté",
            "la matière des sûretés touche aussi le cautionnement entre particuliers "
            "(domaine E) : le classement en droit des affaires est un choix documenté, pas "
            "une exclusion",
        ],
        "risque": "MOYEN",
        "validation_humaine": "recommandee au-dela de la premiere information",
    },
    "consommation": {
        "perimetre": [
            "dettes entre particuliers", "prets et reconnaissances de dette",
            "creances impayees", "litiges client/commercant", "defaut de livraison",
            "produits defectueux", "pratiques commerciales contestees", "remboursements",
            "garanties et engagements",
        ],
        "sources_tentees": [
            {"source": "recherche web (loi 2016-412 relative a la consommation)",
             "resultat": "exemplaires trouves uniquement sur des sites non officiels "
                         "et des depots internationaux (FAO)",
             "usage": "blocage constate : une source non officielle ne devient pas "
                      "un texte verifie"},
        ],
        "lacunes": [
            "loi n° 2016-412 (consommation) : aucun exemplaire officiel ivoirien libre",
            "dettes civiles / commerciales / fiscales / sociales : distinction non "
            "encore adossee a des textes collectes",
        ],
        "risque": "MOYEN",
        "validation_humaine": "recommandee si un montant important est en jeu",
    },
    "administratif_voies_de_recours": {
        "perimetre": [
            "actes d'etat civil", "erreurs sur les actes", "documents d'identite",
            "demandes et recours administratifs", "refus ou silence d'une administration",
            "autorisations et agrements", "fiscalite declarative",
            "recours gracieux / hierarchique / juridictionnel",
        ],
        "sources_tentees": [
            {"source": "onet.gouv.ci / interieur.gouv.ci (etat civil)",
             "resultat": "rapports statistiques publies, aucun texte de loi expose",
             "usage": "aucun texte collecte ; les textes d'etat civil viennent du "
                      "domaine famille (loi 2018-862, 2018-863)"},
            {"source": "fonctionpublique.gouv.ci", "resultat": "HTTP 200, pages HTML",
             "usage": "aucun PDF de texte expose dans le HTML servi"},
        ],
        "lacunes": [
            "code des procedures administratives : non identifie",
            "textes fiscaux : aucun exemplaire collecte (la DGI publie des loi_finances, "
            "non collectees)",
        ],
        "risque": "MOYEN — delais de recours pouvant expirer",
        "validation_humaine": "obligatoire si un delai de recours est proche",
    },
    "penal_procedure_penale": {
        "perimetre": [
            "vol", "escroquerie", "abus de confiance", "menaces", "violences",
            "diffamation", "degradations", "cyberinfractions", "depot de plainte",
            "convocation et audition", "garde a vue", "droits des victimes",
            "presomption d'innocence", "procedure et juridictions",
        ],
        "sources_tentees": [
            {"source": "justice.gouv.ci/publications", "resultat": "HTTP 200 mais aucun "
             "lien de PDF de texte expose", "usage": "aucun texte collecte"},
            {"source": "recherche web (loi 2019-574 code penal ; loi 2018-975 procedure penale)",
             "resultat": "exemplaires seulement sur des sites non officiels",
             "usage": "blocage constate, non contourne"},
        ],
        "lacunes": [
            "Code penal (loi n° 2019-574) : AUCUN exemplaire officiel",
            "Code de procedure penale (loi n° 2018-975) : AUCUN exemplaire officiel",
            "delais de prescription, de recours et d'appel : non documentes par un texte",
            "DOMAINE A RISQUE ELEVE : ne jamais conclure sans avocat",
        ],
        "risque": "CRITIQUE — liberte individuelle en jeu",
        "validation_humaine": "obligatoire : avocat recommande sans delai",
    },
    "associations_organisations_religieuses": {
        "perimetre": [
            "creation et fonctionnement d'association", "gouvernance et responsabilite "
            "des dirigeants", "conflits internes", "biens et fonds associatifs",
            "locaux et contrats", "responsabilite civile", "liberte de religion et "
            "ses limites", "obligations de declaration",
        ],
        "sources_tentees": [
            {"source": "interieur.gouv.ci (publications)",
             "resultat": "HTTP 200 — decrets de nomination et rapports statistiques, "
                         "aucun texte sur les associations",
             "usage": "aucun texte collecte"},
            {"source": "recherche web (loi 60-315 relative aux associations)",
             "resultat": "exemplaires seulement sur des sites non officiels",
             "usage": "blocage constate, non contourne"},
        ],
        "lacunes": [
            "loi n° 60-315 (associations) : aucun exemplaire officiel collecte",
            "regime des organisations religieuses : non documente par un texte collecte",
        ],
        "risque": "MOYEN — neutralite indispensable dans les conflits confessionnels",
        "validation_humaine": "recommandee en cas de conflit interne grave",
    },
    "transport_responsabilite_civile": {
        "perimetre": [
            "accidents de circulation", "dommages materiels et corporels",
            "responsabilite civile", "assurance", "litiges avec un transporteur",
            "contrats de transport", "indemnisation",
        ],
        "sources_tentees": [
            {"source": "sgg.gouv.ci/photo_doc/",
             "resultat": "HTTP 200 — décret n° 2013-711 (téléphone au volant), "
                         "4 517 caractères extraits, 6 articles indexés",
             "usage": "corpus effectivement collecté et vérifié"},
            {"source": "transports.gouv.ci", "resultat": "HTTP 200 — pages d'information "
             "sur la sécurité routière, aucun texte de loi exposé",
             "usage": "aucun texte collecté"},
        ],
        "lacunes": [
            "ATTENTION : le domaine n'a qu'UN texte, et il ne porte que sur l'usage du "
            "téléphone en conduisant. Il ne dit RIEN sur la responsabilité civile, "
            "l'indemnisation des dommages corporels, l'assurance ou les litiges avec un "
            "transporteur",
            "code de la route : non collecté",
            "régime des assurances (code CIMA) : non collecté",
            "accidents de circulation : aucune règle de responsabilité adossée à un texte "
            "du corpus — le statut technique du domaine ne doit PAS se lire comme une "
            "couverture du transport",
            "écart non tranché : le nom de fichier de la source annonce « décret n° 2013-791 "
            "du 20 novembre 2013 », le document porte « n° 2013-711 du 18 octobre 2013 ». "
            "C'est le document qui fait foi ; aucun autre exemplaire pour confirmer",
        ],
        "risque": "ELEVE — prejudice corporel",
        "validation_humaine": "obligatoire en cas de dommage corporel",
    },
    "sante_droits_usagers": {
        "perimetre": [
            "droits des patients", "consentement et information", "reclamations contre "
            "un etablissement", "confidentialite des donnees de sante",
            "responsabilite professionnelle", "voies de recours",
        ],
        "sources_tentees": [
            {"source": "sante.gouv.ci (publications)",
             "resultat": "HTTP 200 — 2 decrets d'organisation administrative, pas de "
                         "texte sur les droits des patients",
             "usage": "aucun texte utile collecte"},
        ],
        "lacunes": [
            "aucun texte sur les droits des patients collecte",
            "aucun texte sur la responsabilite medicale collecte",
            "DOMAINE HORS PORTEE : ne jamais repondre a une question medicale",
        ],
        "risque": "CRITIQUE — urgence vitale possible",
        "validation_humaine": "obligatoire ; orientation medicale immediate si urgence",
    },
    "indetermine": {
        "perimetre": [
            "situations transversales", "plusieurs domaines simultanes",
            "conflits entre regimes juridiques", "expertise non couverte",
        ],
        "sources_tentees": [],
        "lacunes": [
            "aucun corpus propre : ce domaine est un aiguillage, pas un corpus",
        ],
        "risque": "variable",
        "validation_humaine": "selon les domaines mobilises",
    },
}


def _libelle(cle):
    for entree in COUVERTURE_DOMAINES:
        if entree["cle"] == cle:
            return entree
    return {"code": "-", "cle": cle, "libelle": cle}


def mesurer(chemin=None):
    """Mesures lues dans la base, par domaine. Aucune valeur n'est estimee."""
    mesures = {}
    for cle in DOMAINES_JURIDIQUES:
        documents = corpus.lister_documents(domaine=cle, chemin=chemin)
        references = [r for r in _toutes_references(chemin) if r["domaine"] == cle]
        articles = 0
        par_origine = {}
        for document in documents:
            pour_document = corpus.articles_dun_document(document["doc_id"], chemin=chemin)
            articles += len(pour_document)
            for article in pour_document:
                origine = article.get("origine_texte") or "INCONNU"
                par_origine[origine] = par_origine.get(origine, 0) + 1
        mesures[cle] = {
            "code": _libelle(cle)["code"],
            "libelle": _libelle(cle)["libelle"],
            "documents": len(documents),
            "references": len(references),
            "references_verifiees": sum(1 for r in references
                                        if r["etat_verification"] == "VERIFIE"),
            "articles": articles,
            "par_origine": par_origine,
            "documents_illisibles": sum(1 for d in documents if not d["calque_texte"]),
        }
    return mesures


def _toutes_references(chemin=None):
    from core import base
    references = []
    for cle in DOMAINES_JURIDIQUES:
        references.extend(base.lister_references(domaine=cle, chemin=chemin))
    return references


def statut(cle, mesures=None):
    """Statut honnete d'un domaine : deux faits separes, jamais fusionnes.

      * `statut` — etat TECHNIQUE de la chaine : a-t-on des textes, sont-ils
        lisibles, en existe-t-il au moins un de verifie ?
      * `validation_juridique` — ce qu'il manque cote droit : une relecture
        humaine est-elle requise, et le corpus est-il complet ?

    Fusionner les deux ferait disparaitre une information : un domaine peut etre
    techniquement termine ET juridiquement incomplet, et un domaine bloque cote
    source n'est pas « en attente de validation ».
    """
    mesures = mesures or mesurer()
    m = mesures[cle]
    declaration = DECLARATIONS.get(cle, {})
    if m["documents"] == 0:
        if declaration.get("sources_tentees"):
            code = "BLOQUE_SOURCE"
            motif = ("aucun texte collecte : %d source(s) identifiee(s), aucune "
                     "exploitable" % len(declaration["sources_tentees"]))
        else:
            code = "NON_DEMARRE"
            motif = "aucun texte collecte, aucune source identifiee"
    elif m["references_verifiees"] == 0:
        code = "CORPUS_PARTIEL"
        motif = ("%d document(s) collecte(s) mais aucun texte integral verifie"
                 % m["documents"])
    else:
        code = "TERMINE_TECHNIQUEMENT"
        motif = ("%d document(s), %d article(s), %d reference(s) verifiee(s)"
                 % (m["documents"], m["articles"], m["references_verifiees"]))

    if m["documents"] and not _validation_humaine_tracee(chemin=None):
        completude = "INCOMPLET"
    elif m["documents"]:
        completude = "A_CONFIRMER"
    else:
        completude = "INCONNU"

    obligation = (declaration.get("validation_humaine") or "").lower()
    if "obligatoire" in obligation:
        validation = "REQUISE"
    elif "recommande" in obligation or "systematique" in obligation:
        validation = "RECOMMANDEE"
    else:
        validation = "NON_REQUISE"
    return {"domaine": cle, "code_domaine": m["code"], "libelle": m["libelle"],
            "statut": code, "motif": motif,
            "validation_juridique": validation,
            "completude_juridique": completude,
            "validation_humaine_obligatoire": validation == "REQUISE",
            "perimetre": declaration.get("perimetre", []),
            "lacunes": declaration.get("lacunes", []),
            "sources_tentees": declaration.get("sources_tentees", []),
            "risque": declaration.get("risque"),
            "mesures": m}


def _validation_humaine_tracee(chemin=None):
    """Y a-t-il une seule validation humaine tracee dans le corpus ?

    Tant qu'il n'y en a aucune, `TERMINE_ET_VERIFIE` est inatteignable — et le
    dire vaut mieux que d'afficher un statut flatteur.
    """
    try:
        compte = corpus.articles_par_origine(chemin=chemin)
        return compte.get("VERIFIE_MANUELLEMENT", {}).get("articles", 0) > 0
    except Exception:  # noqa: BLE001
        return False


def tableau(chemin=None):
    mesures = mesurer(chemin)
    lignes = []
    for cle in DOMAINES_JURIDIQUES:
        if cle == "indetermine":
            continue
        lignes.append(statut(cle, mesures))
    return lignes


def inventaire(chemin=None):
    """Vue d'ensemble, avec le total d'articles et la repartition par provenance."""
    lignes = tableau(chemin)
    total_articles = sum(l["mesures"]["articles"] for l in lignes)
    total_documents = sum(l["mesures"]["documents"] for l in lignes)
    provenance = {}
    for ligne in lignes:
        for origine, nombre in ligne["mesures"]["par_origine"].items():
            provenance[origine] = provenance.get(origine, 0) + nombre
    return {
        "horodatage": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "domaines": lignes,
        "total_documents": total_documents,
        "total_articles": total_articles,
        "articles_par_origine": provenance,
        "methode_de_comptage": (
            "documents = lignes de la table documents pour le domaine ; "
            "articles = lignes de articles_corpus rattachees a ces documents "
            "(comptees une par une, pas estimees) ; references = lignes de "
            "references_juridiques pour le domaine."
        ),
        "avertissement": (
            "La reussite des tests ne vaut PAS validation juridique. "
            "Un domaine TERMINE_TECHNIQUEMENT reste juridiquement incomplet."
        ),
    }


if __name__ == "__main__":
    import json
    inventaire_courant = inventaire()
    print(json.dumps(inventaire_courant, ensure_ascii=False, indent=1))
