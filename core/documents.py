# -*- coding: utf-8 -*-
"""Générateur de documents — BROUILLONS uniquement, jamais d'envoi.

Invariants stricts :

* Ce module ne contient **aucune** fonction d'envoi. Pas de SMTP, pas de requête
  réseau sortante, pas de dépôt en ligne. L'absence est vérifiée par un test qui
  lit ce fichier source (spec §8 : aucun courrier n'est envoyé sans autorisation).
* Tout document produit porte l'en-tête « BROUILLON — NON ENVOYÉ » et une
  mention indiquant que l'agent n'est pas un professionnel habilité.
* Le texte produit est contrôlé par core/garde_fous.evaluer_sortie AVANT écriture :
  une formulation qui promet un résultat fait échouer la génération.
* L'écriture est confinée à DOSSIERS/<dossier_id>/BROUILLONS/. Toute tentative
  d'écriture hors de cette zone lève une erreur.

Les modèles ne contiennent aucune affirmation juridique : ce sont des demandes
administratives neutres, à compléter par l'utilisateur.
"""

import datetime
import os
import re

from config import DOSSIERS_DIR, dossier_utilisateur
from core.garde_fous import evaluer_sortie

MENTION_BROUILLON = "BROUILLON — NON ENVOYÉ — À RELIRE ET À VALIDER PAR L'UTILISATEUR"

MENTION_FIN = (
    "Document préparé avec une assistance automatisée. L'agent n'est ni avocat, ni "
    "huissier, ni autorité administrative : il ne représente personne et ne garantit "
    "aucun résultat. Ce document doit être relu avant tout usage."
)

# Modèles neutres. Les champs {{...}} sont à compléter par l'utilisateur.
MODELES = {
    "demande_amiable": {
        "objet": "{{objet}}",
        "corps": (
            "Madame, Monsieur,\n\n"
            "Je vous adresse la présente au sujet de : {{objet}}.\n\n"
            "Les faits, tels que je peux les établir, sont les suivants :\n{{faits}}\n\n"
            "Les pièces en ma possession sont :\n{{pieces}}\n\n"
            "Ma demande est la suivante : {{demande}}.\n\n"
            "Je vous remercie de bien vouloir me faire connaître votre position, par "
            "écrit, à l'adresse suivante : {{adresse_retour}}.\n\n"
            "Je reste à votre disposition pour tout échange permettant de régler la "
            "situation à l'amiable."
        ),
    },
    "reclamation": {
        "objet": "Réclamation — {{objet}}",
        "corps": (
            "Madame, Monsieur,\n\n"
            "Je porte à votre attention une réclamation concernant : {{objet}}.\n\n"
            "Faits constatés :\n{{faits}}\n\n"
            "Pièces jointes :\n{{pieces}}\n\n"
            "Demande : {{demande}}.\n\n"
            "Je sollicite une réponse écrite dans vos meilleurs délais, à l'adresse "
            "suivante : {{adresse_retour}}."
        ),
    },
    "demande_de_pieces": {
        "objet": "Demande de communication de pièces — {{objet}}",
        "corps": (
            "Madame, Monsieur,\n\n"
            "Dans le cadre de la situation suivante : {{objet}}, je sollicite la "
            "communication des documents suivants :\n{{demande}}\n\n"
            "Éléments de contexte :\n{{faits}}\n\n"
            "Je vous remercie de me les adresser à : {{adresse_retour}}."
        ),
    },
    "reponse_a_courrier": {
        "objet": "Réponse à votre courrier du {{date_courrier}} — {{objet}}",
        "corps": (
            "Madame, Monsieur,\n\n"
            "J'accuse réception de votre courrier du {{date_courrier}} relatif à "
            "{{objet}}.\n\n"
            "Je souhaite apporter les précisions suivantes :\n{{faits}}\n\n"
            "Les pièces que je joins sont :\n{{pieces}}\n\n"
            "Ma position est la suivante : {{demande}}.\n\n"
            "Je reste à votre disposition, par écrit, à l'adresse suivante : "
            "{{adresse_retour}}."
        ),
    },
}

CHAMPS_OBLIGATOIRES = ("objet", "faits", "demande", "adresse_retour")


def horodatage():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def dossier_brouillons(dossier_id):
    chemin = dossier_utilisateur(dossier_id) / "BROUILLONS"
    return chemin


def nettoyer_pour_pdf(texte):
    """Remplace les caractères hors latin-1 (’ — … ) avant rendu PDF."""
    remplacements = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"',
                     "\u2014": "-", "\u2013": "-", "\u2026": "..."}
    for source, cible in remplacements.items():
        texte = texte.replace(source, cible)
    return texte.encode("latin-1", "replace").decode("latin-1")


def _remplir(gabarit, champs):
    """Remplit les {{champs}} fournis ; les autres deviennent VISIBLES.

    Aucun trou silencieux : un champ non fourni apparaît en clair dans le
    brouillon, pour que l'utilisateur le complète au lieu de l'oublier.
    """
    texte = gabarit
    for cle, valeur in (champs or {}).items():
        if valeur not in (None, ""):
            texte = texte.replace("{{%s}}" % cle, str(valeur))
    for cle in sorted(set(re.findall(r"\{\{(\w+)\}\}", texte))):
        texte = texte.replace("{{%s}}" % cle, "[À COMPLÉTER : %s]" % cle)
    return texte


def rendre_texte(dossier_id, type_document, champs, date_document=None):
    """Construit le texte complet du brouillon. Aucune écriture ici."""
    if type_document not in MODELES:
        raise KeyError("modèle inconnu : %r. Modèles disponibles : %s"
                       % (type_document, ", ".join(sorted(MODELES))))
    manquants = [c for c in CHAMPS_OBLIGATOIRES if not str(champs.get(c) or "").strip()]
    if manquants:
        raise ValueError("champs obligatoires du brouillon manquants : %s"
                         % ", ".join(manquants))

    modele = MODELES[type_document]
    corps = _remplir(modele["corps"], champs)
    objet = _remplir(modele["objet"], champs)

    date_document = date_document or datetime.date.today().isoformat()
    entete = "%s\nGénéré le %s\n%s\n" % (MENTION_BROUILLON, date_document, "=" * 68)
    pied = "\n%s\n%s\n" % ("-" * 68, MENTION_FIN)
    return entete + "\nObjet : %s\n\n" % objet + corps + pied


def generer_brouillon(dossier_id, type_document, champs, export_pdf=True):
    """Écrit le brouillon (.txt, et .pdf si la bibliothèque est disponible).

    Lève si le texte produit promet un résultat (garde-fou de sortie).
    Retourne un dict de traçabilité — avec les échecs DÉCLARÉS, pas masqués.
    """
    texte = rendre_texte(dossier_id, type_document, champs)
    violations = evaluer_sortie(texte)
    if violations:
        raise ValueError(
            "brouillon refusé : formulation interdite détectée (%s)"
            % "; ".join("%s : %s" % (v["code"], v["motif_detecte"]) for v in violations)
        )

    destination = dossier_brouillons(dossier_id)
    os.makedirs(str(destination), exist_ok=True)
    horo = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base = "%s_%s" % (horo, type_document)
    chemin_txt = destination / (base + ".txt")
    with open(str(chemin_txt), "w", encoding="utf-8") as f:
        f.write(texte)

    resultat = {
        "dossier_id": dossier_id,
        "type_document": type_document,
        "fichier_txt": str(chemin_txt),
        "octets_txt": os.path.getsize(str(chemin_txt)),
        "fichier_pdf": None,
        "pdf": {"tente": False, "ok": False, "erreur": None},
        "envoi": "AUCUN — l'agent ne dispose d'aucune fonction d'envoi",
        "horodatage": horodatage(),
        "mention": MENTION_BROUILLON,
    }

    if export_pdf:
        resultat["pdf"]["tente"] = True
        try:
            from fpdf import FPDF  # import local : le module reste utilisable sans fpdf
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            pdf.add_page()
            pdf.set_font("Helvetica", size=10)
            for ligne in nettoyer_pour_pdf(texte).split("\n"):
                pdf.multi_cell(0, 5, ligne if ligne.strip() else " ")
            chemin_pdf = destination / (base + ".pdf")
            pdf.output(str(chemin_pdf))
            resultat["fichier_pdf"] = str(chemin_pdf)
            resultat["pdf"].update(ok=True, octets=os.path.getsize(str(chemin_pdf)))
        except Exception as erreur:  # noqa: BLE001 — l'échec PDF est déclaré, pas masqué
            resultat["pdf"].update(ok=False, erreur="%s : %s" % (type(erreur).__name__, erreur))

    return resultat


def lister_brouillons(dossier_id):
    """Liste les brouillons produits pour un dossier."""
    dossier = dossier_brouillons(dossier_id)
    if not os.path.isdir(str(dossier)):
        return []
    fichiers = sorted(os.listdir(str(dossier)))
    return [{"fichier": f, "octets": os.path.getsize(str(dossier / f))} for f in fichiers]


def types_de_documents():
    return sorted(MODELES)
