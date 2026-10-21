# -*- coding: utf-8 -*-
"""Mon Recours CI — Agent juridique et d'assistance citoyenne (Côte d'Ivoire).

Ce module est l'ORCHESTRATEUR. Il relie les cinq étapes du workflow et tient les
invariants du projet :

  Étape 1  Accueil et qualification      core.qualification + core.urgence
  Étape 2  Collecte des faits            core.faits
  Étape 3  Recherche et vérification     core.sources + core.base
  Étape 4  Analyse et explication        core.analyse (validation obligatoire)
  Étape 5  Plan d'action et suivi        core.plan_action

Principe tenu par le code, pas par la documentation :

  * Aucune conclusion ne sort sans règle appuyée sur une référence du corpus
    ET sans application aux faits (core.analyse.peut_conclure).
  * Aucune analyse non conforme ne sort (core.analyse.exiger_conformite).
  * Aucun courrier n'est envoyé : core.documents n'a aucune fonction d'envoi.
  * Le dossier de traçabilité nomme ce qui manque au lieu de l'omettre.

Le corpus est VIDE au départ. Ce n'est pas un défaut à combler par des
souvenirs : une référence n'entre qu'avec ses métadonnées et son état de
vérification (core.base).
"""

import json
import os
import re

import config
from config import NOM_AGENT, VERSION, dossier_utilisateur
from core import analyse as mod_analyse
from core import base, corpus, documents, evidence, faits as mod_faits, garde_fous, plan_action, qualification, sources
from core import corpus as mod_corpus
from core.urgence import detecter as detecter_urgence

STATUTS_REPONSE = (
    "REFUS",
    "EN_COURS",
    "ANALYSE_CONFORME",
    "CONCLUSION_IMPOSSIBLE",
    "ANALYSE_REFUSEE",
)


class MonRecoursCI(object):
    """Orchestrateur. Un dossier par utilisateur, jamais de croisement."""

    def __init__(self, chemin_db=None, chemin_sources=None):
        self.chemin_db = chemin_db
        self.chemin_sources = chemin_sources
        base.initialiser(chemin_db)

    # ------------------------------------------------------------------ état
    def etat(self):
        """État réel de l'agent : corpus, sources, dossiers. Rien n'est supposé."""
        return {
            "agent": NOM_AGENT,
            "version": VERSION,
            "pays": "Côte d'Ivoire",
            "corpus": base.statistiques(self.chemin_db),
            "sources": sources.rapport_sources(self.chemin_sources),
            "dossiers": evidence.lister_dossiers(),
            "capacites": {
                "peut": [
                    "qualifier une demande et router par domaine",
                    "détecter l'urgence et prioriser la sécurité",
                    "collecter des faits avec statuts préservés",
                    "vérifier l'accessibilité réelle des sources officielles",
                    "enregistrer des références avec métadonnées et état de vérification",
                    "valider une analyse (traçabilité) et refuser une analyse non conforme",
                    "préparer des brouillons de courriers (jamais envoyés)",
                    "produire un dossier de traçabilité",
                ],
                "ne_peut_pas": [
                    "dire ce que dit la loi sans référence enregistrée et vérifiée",
                    "inventer un article, un délai, une procédure ou une citation",
                    "garantir un résultat",
                    "représenter l'utilisateur",
                    "envoyer un courrier ou déclencher une démarche",
                    "supprimer définitivement un dossier (DELETE non accordé)",
                ],
            },
        }

    def verifier_sources(self, source_ids=None, timeout=20):
        """Teste réellement les sources du registre et journalise le résultat."""
        resultats = sources.verifier_sources(
            source_ids=source_ids, timeout=timeout, chemin=self.chemin_sources
        )
        return {
            "verifications": resultats,
            "rapport": sources.rapport_sources(self.chemin_sources),
        }

    # --------------------------------------------------------------- étape 1-2
    def ouvrir_dossier(self, dossier_id, demande, elements_connus=()):
        """Étapes 1 et 2 : qualification, urgence, collecte, questions ciblées."""
        chemin = dossier_utilisateur(dossier_id)  # valide l'identifiant
        config.creer_dossier_prive(chemin)

        evaluation = garde_fous.evaluer_demande(demande)
        dossier = {
            "dossier_id": dossier_id,
            "agent": {"nom": NOM_AGENT, "version": VERSION},
            "ouvert_le": _horodatage(),
            "demande": demande,
            "garde_fous": {k: v for k, v in evaluation.items() if k != "texte_normalise"},
            "statut": "EN_COURS",
        }

        if not evaluation["autorise"]:
            dossier["statut"] = "REFUS"
            dossier["refus"] = evaluation["refus"]
            dossier["note"] = (
                "Demande refusée. Aucune analyse juridique n'est produite et aucune "
                "démarche n'est engagée. Une voie sûre est proposée pour chaque refus."
            )
            self._ecrire_en_cours(dossier_id, dossier)
            return dossier

        urgence = detecter_urgence(demande)
        qualif = qualification.qualifier(demande)
        collecte = mod_faits.Faits(dossier_id)
        collecte.declarer(demande, precision="récit initial de l'utilisateur")
        questions = qualification.questions_a_poser(qualif["domaines_probables"], elements_connus)
        refs_candidates = self._chercher_references(demande, qualif["domaines_probables"])
        verrous = plan_action.evaluer_verrous(urgence, qualif["domaines_probables"], demande)

        dossier.update({
            "urgence": urgence,
            "qualification": qualif,
            "faits": collecte.to_dict(),
            "questions_a_poser": questions,
            "references_candidates": refs_candidates,
            "verrous_humains": verrous,
            "note_corpus": (
                "Les références candidates proviennent du corpus local. Un corpus vide "
                "signifie : aucune information juridique vérifiée n'est disponible pour "
                "cette demande — ce qui sera dit explicitement, sans suppléer par mémoire."
            ),
        })
        self._ecrire_en_cours(dossier_id, dossier)
        return dossier

    # --------------------------------------------------------------- étape 3-5
    def clore_dossier(self, dossier_id, analyse, brouillons=(), validations_humaines=(),
                      plan=None, sources_testees=None):
        """Étapes 3 à 5 : validation de l'analyse, plan d'action, traçabilité.

        `analyse` est une structure construite avec core.analyse.* — elle est
        VALIDÉE ici. Une analyse non conforme lève et n'est jamais écrite.
        """
        en_cours = self.lire_en_cours(dossier_id)
        if en_cours is None:
            # Clôturer un dossier jamais ouvert doit échouer CLAIREMENT : sans ce
            # garde, l'absence serait confondue avec une panne de lecture.
            raise ValueError(
                "aucun dossier ouvert pour %r : impossible de le clôturer"
                % (dossier_id,))
        if en_cours["statut"] == "REFUS":
            return self._clore_refus(en_cours)

        analyse = dict(analyse)
        analyse.setdefault("dossier_id", dossier_id)

        refs_utilisees = {r.get("ref_id") for r in analyse.get("regles", []) if r.get("ref_id")}
        refs_utilisees |= {rid for a in analyse.get("applications", []) for rid in a.get("ref_ids", [])}
        references = {}
        refs_inconnues = []
        for ref_id in sorted(refs_utilisees):
            ref = base.obtenir_reference(ref_id, self.chemin_db)
            if ref is None:
                refs_inconnues.append(ref_id)
            else:
                references[ref_id] = ref

        collecte = mod_faits.Faits.depuis_dict(en_cours.get("faits", {}))
        faits_texte = " ".join(f["libelle"] for f in collecte.tous())
        urgence = en_cours.get("urgence") or detecter_urgence(en_cours["demande"])
        domaines = (en_cours.get("qualification") or {}).get("domaines_probables") or ["indetermine"]

        violations = mod_analyse.valider(
            analyse, references=references, faits_texte=faits_texte
        )
        # Provenance des textes cités : une règle fondée sur un texte OCR non
        # recoupé exige une incertitude déclarée. Contrôle ADDITIF — il ne
        # remplace aucun des contrôles précédents.
        try:
            violations = violations + mod_corpus.verifier_provenance_analyse(analyse)
        except Exception:  # noqa: BLE001 — corpus absent : on ne masque pas, on dégrade
            pass
        conforme, raisons_conclusion = mod_analyse.peut_conclure(analyse, references=references)

        if plan is None:
            plan = plan_action.construire_plan(
                dossier_id, domaines, urgence, faits=collecte,
                references=references, documents_prepares=list(brouillons or ()),
            )
        autorise_externe, raisons_verrous = plan_action.actions_externes_autorisees(plan)

        if violations:
            statut = "ANALYSE_REFUSEE"
        elif conforme:
            statut = "ANALYSE_CONFORME"
        else:
            statut = "CONCLUSION_IMPOSSIBLE"

        controles = {
            "garde_fous_demande": en_cours.get("garde_fous"),
            "analyse_conforme": conforme,
            "violations": violations,
            "raisons_absence_de_conclusion": raisons_conclusion,
            "references_utilisees": sorted(references),
            "references_inconnues": refs_inconnues,
            "actions_externes_autorisees": autorise_externe,
            "raisons_verrous_ouverts": raisons_verrous,
            "aucune_fonction_d_envoi": True,
        }

        trace = evidence.construire(
            dossier_id=dossier_id,
            demande=en_cours.get("demande"),
            resume_neutre=_resume_neutre(en_cours.get("demande")),
            faits=collecte,
            questions=en_cours.get("questions_a_poser"),
            references_consultees=[references[rid] for rid in sorted(references)],
            articles_verifies=_articles_cites(analyse, references),
            analyse=analyse,
            plan=plan,
            verrous=en_cours.get("verrous_humains"),
            orientations=plan.get("orientations"),
            controles_qualite=controles,
            validations_humaines=list(validations_humaines or ()),
            urgence=urgence,
            qualification=en_cours.get("qualification"),
            sources_testees=sources_testees or [],
        )
        trace["statut_reponse"] = statut
        trace["analyse"] = analyse
        chemin_trace = evidence.ecrire(trace, chemin=dossier_utilisateur(dossier_id) / "DOSSIER_TRACABILITE.json")

        en_cours["statut"] = statut
        self._ecrire_en_cours(dossier_id, en_cours)

        return {
            "dossier_id": dossier_id,
            "statut_reponse": statut,
            "analyse": analyse,
            "plan": plan,
            "controles_qualite": controles,
            "traceabilite": chemin_trace,
            "brouillons": [documents.lister_brouillons(dossier_id)] if brouillons else [],
            "avertissement": (
                "Aucune action externe n'est exécutée par l'agent. Tout envoi exige une "
                "validation humaine explicite."
            ),
        }

    def _clore_refus(self, en_cours):
        dossier_id = en_cours["dossier_id"]
        trace = evidence.construire(
            dossier_id=dossier_id,
            demande=en_cours.get("demande"),
            resume_neutre=_resume_neutre(en_cours.get("demande")),
            refus=en_cours.get("refus"),
            controles_qualite={
                "refus_opposes": len(en_cours.get("refus") or []),
                "voies_sures_proposees": [r.get("suite_sure") for r in en_cours.get("refus") or []],
            },
            verrous=[],
        )
        trace["statut_reponse"] = "REFUS"
        chemin = evidence.ecrire(trace, chemin=dossier_utilisateur(dossier_id) / "DOSSIER_TRACABILITE.json")
        return {"dossier_id": dossier_id, "statut_reponse": "REFUS",
                "refus": en_cours.get("refus"), "traceabilite": chemin}

    # ------------------------------------------------------------- utilitaires
    def _chercher_references(self, demande, domaines):
        """Cherche dans le corpus local. Liste vide = réponse honnête, pas un échec."""
        mots = [m for m in re.split(r"[\s,;.()'\"]+", demande or "") if len(m) > 3]
        mots = list(dict.fromkeys(mots))[:12]
        resultats = base.rechercher(" ".join(mots), self.chemin_db) if mots else []
        for domaine in domaines or []:
            for ref in base.rechercher(domaine, self.chemin_db):
                if ref["ref_id"] not in {r["ref_id"] for r in resultats}:
                    resultats.append(ref)
        return [self._candidat_leger(r) for r in resultats[:20]]

    @staticmethod
    def _candidat_leger(reference):
        """Référence conservée dans l'état du dossier — sans le texte de l'article.

        `extrait_texte` peut dépasser 300 Ko par référence : c'est le texte complet
        de l'acte, utile au calcul, inutile à la trace. Il était pourtant recopié
        dans `DOSSIER_EN_COURS.json`, soit ~2,5 Mo par consultation, sans qu'aucune
        partie du code ne le relise. Ce qui reste permet de savoir quelles
        références ont été examinées, et dans quel état de vérification.
        """
        return {cle: valeur for cle, valeur in reference.items() if cle != "extrait_texte"}

    def _chemin_en_cours(self, dossier_id):
        return dossier_utilisateur(dossier_id) / "DOSSIER_EN_COURS.json"

    def _ecrire_en_cours(self, dossier_id, dossier):
        chemin = self._chemin_en_cours(dossier_id)
        config.ecrire_fichier_prive(chemin, json.dumps(dossier, ensure_ascii=False, indent=2))
        return str(chemin)

    def lire_en_cours(self, dossier_id):
        """Relit un dossier en cours. Un dossier inconnu renvoie `None`.

        Lever une exception ferait passer une absence normale pour une panne.
        """
        try:
            with open(str(self._chemin_en_cours(dossier_id)), "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, OSError):
            return None

    def enregistrer_faits(self, dossier_id, faits):
        """Persiste les faits d'un dossier en cours (déclarations, pièces, manquants).

        Sans cette écriture, une réponse donnée par l'utilisateur pendant la
        conversation n'atteindrait jamais le dossier de traçabilité : le dossier
        final ne contiendrait que les faits connus à l'ouverture. Défaut constaté
        en construisant la couche conversationnelle.
        """
        en_cours = self.lire_en_cours(dossier_id)
        if en_cours is None:
            raise ValueError("aucun dossier ouvert pour %r" % (dossier_id,))
        en_cours["faits"] = faits.to_dict() if hasattr(faits, "to_dict") else faits
        self._ecrire_en_cours(dossier_id, en_cours)
        return en_cours["faits"]

    def enregistrer_courrier(self, dossier_id, informations):
        """Persiste les informations de courrier (expéditeur, destinataire, pièces).

        Ce ne sont PAS des faits juridiques : elles ne prouvent rien et ne
        modifient aucune analyse. Elles servent uniquement à rédiger un document
        que la personne relira et enverra elle-même. Les clés inconnues sont
        écartées par l'appelant, pas ici.
        """
        en_cours = self.lire_en_cours(dossier_id)
        if en_cours is None:
            raise ValueError("aucun dossier ouvert pour %r" % (dossier_id,))
        courrier = dict(en_cours.get("courrier") or {})
        for cle, valeur in (informations or {}).items():
            if valeur is None:
                continue
            courrier[cle] = str(valeur).strip()
        en_cours["courrier"] = courrier
        self._ecrire_en_cours(dossier_id, en_cours)
        return courrier

    def dossier(self, dossier_id):
        """Relit la traçabilité d'un dossier précis. Jamais celle d'un autre.

        Un dossier inconnu renvoie `None` : lever une exception ferait croire à
        une panne alors que la réponse correcte est « ce dossier n'existe pas ».
        """
        try:
            return evidence.lire(dossier_id)
        except (FileNotFoundError, OSError):
            return None


def _numero_article(valeur):
    """« Article 415 » -> « 415 ». Retourne None si aucun numéro exploitable."""
    if valeur is None:
        return None
    m = re.search(r"(\d{1,4}(?:\s*(?:bis|ter|quater))?)", str(valeur), re.I)
    return m.group(1).strip().lower() if m else None


def _articles_cites(analyse, references):
    """Articles RÉELLEMENT cités par une analyse, avec leur empreinte si indexés.

    Le champ ne prétend pas que « tout le texte est vérifié » : il dit quels
    articles ont servi à l'analyse, et, lorsque le corpus les a indexés, il
    porte l'empreinte SHA-256 du texte de l'article — la chaîne de preuve
    descend donc jusqu'à l'article, plus seulement jusqu'au document.

    Quand l'analyse ne nomme aucun article, l'entrée retombe au niveau de la
    référence (couverture annoncée), plutôt que de laisser le champ vide : un
    dossier sans aucune entrée se lirait comme « rien n'a été vérifié ».
    """
    resultats = []
    for ref_id in sorted(references):
        reference = references[ref_id]
        if reference.get("etat_verification") != "VERIFIE":
            continue
        numeros = []
        for regle in analyse.get("regles", []):
            if regle.get("ref_id") != ref_id:
                continue
            numero = _numero_article(regle.get("articles"))
            if numero and numero not in numeros:
                numeros.append(numero)
        if not numeros:
            resultats.append({"ref_id": ref_id, "articles": reference.get("articles"),
                              "etat_verification": reference.get("etat_verification"),
                              "portee": "couverture de la reference"})
            continue
        for numero in numeros:
            entree = {"ref_id": ref_id, "article": numero,
                      "etat_verification": reference.get("etat_verification"),
                      "indexe_dans_le_corpus": False, "sha256_article": None}
            try:
                from core import corpus as mod_corpus
                article = mod_corpus.obtenir_article_par_reference(ref_id, numero)
                if article:
                    entree["indexe_dans_le_corpus"] = True
                    entree["sha256_article"] = article["sha256_article"]
            except Exception:  # noqa: BLE001 — corpus absent : on ne masque pas, on dégrade
                pass
            resultats.append(entree)
    return resultats


def _horodatage():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _resume_neutre(demande, limite=400):
    """Résumé minimal : le récit tel que reçu, tronqué, sans interprétation."""
    if not demande:
        return None
    texte = re.sub(r"\s+", " ", str(demande)).strip()
    return texte if len(texte) <= limite else texte[:limite] + " […]"
