# -*- coding: utf-8 -*-
"""Invariants des workflows GitHub Actions.

Ces tests ne lancent aucune CI. Ils lisent les fichiers de `.github/workflows/`
et vérifient les propriétés qui ont motivé leur correction :

1. le job `collecte` est en **lecture seule** et n'exécute aucun `git push` ;
2. seul le job `publication` dispose de `contents: write` ;
3. `publication` **dépend** du succès de `collecte` (`needs`) ;
4. `publier` est **faux par défaut** ;
5. une collecte ordinaire ne pousse rien (aucun commit, aucun push) ;
6. `publication` **refuse `main`** et toute branche hors `corpus/*` autorisée ;
7. les fichiers transitent par des **artefacts vérifiés** avant publication ;
8. aucun workflow ne **déploie** ;
9. `interface-web.yml` garde ses protections (verrou confiné, lecture seule) ;
10. ces contrôles **détectent réellement** la suppression d'une garde — éprouvé
    par mutation en mémoire dans `TestDetectionDeRegression`.

Un fichier de workflow n'est pas exécutable ici : ces assertions portent sur le
texte, ce qui suffit à empêcher le retour des défauts constatés.
"""

import os
import re
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOWS = os.path.join(RACINE, ".github", "workflows")
COLLECTE = os.path.join(WORKFLOWS, "collecte-corpus.yml")
INTERFACE = os.path.join(WORKFLOWS, "interface-web.yml")

MOTS_DEPLOIEMENT = ("vercel", "netlify", "firebase deploy", "gh-pages",
                    "docker push", "kubectl apply", "aws s3", "fly deploy")


def lire(chemin):
    with open(chemin, encoding="utf-8") as flux:
        return flux.read()


def bloc_job(contenu, nom):
    """Texte d'un job (indentation 2) jusqu'au job suivant, ou None."""
    depart = re.search(r"(?m)^  %s:\s*$" % re.escape(nom), contenu)
    if not depart:
        return None
    suivant = re.compile(r"(?m)^  [A-Za-z0-9_-]+:\s*$").search(contenu, depart.end())
    return contenu[depart.start():suivant.start() if suivant else len(contenu)]


def problemes_collecte(contenu):
    """Anomalies du workflow de collecte. Liste vide = conforme."""
    collecte = bloc_job(contenu, "collecte")
    publication = bloc_job(contenu, "publication")
    if collecte is None:
        return ["job `collecte` absent"]
    if publication is None:
        return ["job `publication` absent"]

    p = []

    # 1. Lecture seule côté collecte.
    if not re.search(r"(?m)^    permissions:\s*\n      contents: read\s*$", collecte):
        p.append("job `collecte` : permissions `contents: read` attendues")
    if "contents: write" in collecte:
        p.append("job `collecte` : `contents: write` interdit")

    # 5. Aucune écriture distante pendant la collecte.
    for numero, ligne in enumerate(collecte.splitlines(), 1):
        if re.search(r"\bgit\b.*\b(push|commit)\b", ligne):
            p.append("job `collecte` : écriture git ligne %d — %s" % (numero, ligne.strip()))

    # 2. Écriture réservée au job de publication.
    if not re.search(r"(?m)^    permissions:\s*\n      contents: write\s*$", publication):
        p.append("job `publication` : `contents: write` attendu")
    entete = re.search(r"(?m)^permissions:\s*\n((?:[ \t]+\S.*\n|\n)*)", contenu)
    if not entete or "contents: read" not in entete.group(1):
        p.append("workflow : `contents: read` attendu au niveau global")

    # 3. Dépendance explicite.
    if not re.search(r"(?m)^    needs:\s*collecte\s*$", publication):
        p.append("job `publication` : `needs: collecte` attendu")

    # 4. `publier` désactivé par défaut.
    bloc = re.search(r"(?m)^      publier:\n((?:[ \t]+.*\n|\n)*)", contenu)
    if not bloc:
        p.append("entrée `publier` absente")
    elif "default: false" not in bloc.group(1):
        p.append("entrée `publier` : `default: false` attendu")

    # 6. Publication : demande explicite + branche corpus autorisée.
    condition = re.search(r"(?m)^    if:\s*(.+?)(?=\n    [a-z_]+:)", publication, re.S)
    if not condition or "inputs.publier == true" not in condition.group(1):
        p.append("job `publication` : `if` doit exiger `inputs.publier == true`")
    if not condition or "corpus/collecte-autonome" not in condition.group(1):
        p.append("job `publication` : `if` doit nommer les branches autorisées")
    if 'case "$REF" in' not in publication:
        p.append("job `publication` : garde de branche (`case`) absente")
    if "publication refusée depuis la branche" not in publication:
        p.append("job `publication` : refus explicite des branches non autorisées absent")
    if "publication interdite depuis main" not in publication:
        p.append("job `publication` : refus explicite de `main` absent")

    # 7. Transfert par artefacts, vérifié avant écriture.
    for nom in ("pdf-collectes", "constats-collecte"):
        if nom not in collecte:
            p.append("job `collecte` : artefact `%s` non produit" % nom)
        if nom not in publication:
            p.append("job `publication` : artefact `%s` non récupéré" % nom)
    if "Vérifier les artefacts reçus" not in publication:
        p.append("job `publication` : étape de vérification des artefacts absente")
    if "artefact de constats absent" not in publication:
        p.append("job `publication` : refus d'un artefact manquant absent")

    return p


def problemes_interface(contenu):
    """Anomalies du workflow d'interface. Liste vide = conforme."""
    p = []
    if "refs/heads/feature/interface-web" not in contenu:
        p.append("verrou : garde sur `feature/interface-web` absente")
    verrou = bloc_job(contenu, "verrou-des-versions")
    if verrou is None:
        p.append("job `verrou-des-versions` absent")
    elif "contents: write" not in verrou:
        p.append("job `verrou-des-versions` : `contents: write` attendu")
    entete = re.search(r"(?m)^permissions:\s*\n((?:[ \t]+\S.*\n|\n)*)", contenu)
    if not entete or "contents: read" not in entete.group(1):
        p.append("workflow interface : `contents: read` attendu au niveau global")
    return p


def problemes_deploiement(contenu, nom="?"):
    p = []
    for mot in MOTS_DEPLOIEMENT:
        if mot in contenu.lower():
            p.append("%s contient « %s »" % (nom, mot))
    return p


class TestAucunDeploiement(unittest.TestCase):
    def test_aucun_workflow_ne_deploie(self):
        for nom in sorted(os.listdir(WORKFLOWS)):
            if nom.endswith((".yml", ".yaml")):
                self.assertEqual(problemes_deploiement(lire(os.path.join(WORKFLOWS, nom)), nom), [])


class TestAucunPushVersMain(unittest.TestCase):
    def test_aucune_commande_ne_pousse_vers_main(self):
        for nom in sorted(os.listdir(WORKFLOWS)):
            if not nom.endswith((".yml", ".yaml")):
                continue
            for numero, ligne in enumerate(lire(os.path.join(WORKFLOWS, nom)).splitlines(), 1):
                if "git" in ligne and "push" in ligne:
                    self.assertNotRegex(ligne, r"(^|[\s:])main\b",
                                        "%s:%d pousse vers main" % (nom, numero))


class TestWorkflowDeCollecte(unittest.TestCase):
    def setUp(self):
        self.contenu = lire(COLLECTE)

    def test_structure_conforme(self):
        """Les dix propriétés de sécurité, en un seul point de contrôle."""
        self.assertEqual(problemes_collecte(self.contenu), [])

    def test_pas_de_declenchement_au_push(self):
        self.assertNotRegex(self.contenu, r"(?m)^\s{2}push:\s*$")

    def test_execution_manuelle_avec_les_trois_options(self):
        self.assertRegex(self.contenu, r"(?m)^\s{2}workflow_dispatch:\s*$")
        for entree in ("forcer", "ocr", "publier"):
            self.assertRegex(self.contenu, r"(?m)^\s{6}%s:\s*$" % entree)

    def test_collecte_ne_configure_pas_d_identite_git(self):
        """`git config user.*` dans la collecte trahirait une intention d'écrire."""
        self.assertNotIn("git config user.", bloc_job(self.contenu, "collecte"))

    def test_checkout_de_collecte_sans_identifiants_persistes(self):
        self.assertIn("persist-credentials: false", bloc_job(self.contenu, "collecte"))


class TestWorkflowDInterface(unittest.TestCase):
    def test_protections_conservees(self):
        self.assertEqual(problemes_interface(lire(INTERFACE)), [])


class TestDetectionDeRegression(unittest.TestCase):
    """Une garde retirée doit être signalée. Mutations en mémoire, disque intact."""

    def setUp(self):
        self.contenu = lire(COLLECTE)

    def _muter(self, ancien, nouveau):
        self.assertIn(ancien, self.contenu, "mutation impossible : motif absent")
        return self.contenu.replace(ancien, nouveau, 1)

    def _doit_echouer(self, contenu):
        problemes = problemes_collecte(contenu)
        self.assertNotEqual(problemes, [], "la mutation n'a pas été détectée")
        return problemes

    def test_permission_ecriture_accordee_a_la_collecte(self):
        self._doit_echouer(self._muter(
            "    permissions:\n      contents: read\n    steps:\n      - uses: actions/checkout@v4",
            "    permissions:\n      contents: write\n    steps:\n      - uses: actions/checkout@v4"))

    def test_dependance_supprimee(self):
        self._doit_echouer(self._muter("    needs: collecte\n", ""))

    def test_garde_de_branche_supprimee(self):
        self._doit_echouer(self._muter('          case "$REF" in\n', "          true || {\n"))

    def test_refus_de_main_supprime(self):
        self._doit_echouer(self._muter(
            'if [ "$REF" = "main" ]; then echo "::error::publication interdite depuis main"; exit 1; fi',
            ""))

    def test_publier_actif_par_defaut(self):
        self._doit_echouer(self._muter("        default: false\n\npermissions:",
                                       "        default: true\n\npermissions:"))

    def test_push_ajoute_dans_la_collecte(self):
        self._doit_echouer(self._muter(
            "      - name: Conserver les PDF téléchargés (artefact)",
            "      - name: push interdit\n        run: git push origin HEAD\n\n"
            "      - name: Conserver les PDF téléchargés (artefact)"))

    def test_verification_des_artefacts_supprimee(self):
        self._doit_echouer(self._muter("artefact de constats absent", "artefact constats"))

    def test_deploiement_reintroduit(self):
        self.assertNotEqual(
            problemes_deploiement(self.contenu + "\n# vercel\n", "collecte-corpus.yml"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
