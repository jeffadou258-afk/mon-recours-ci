# -*- coding: utf-8 -*-
"""Invariants des workflows GitHub Actions.

Ces tests ne lancent aucune CI. Ils lisent les fichiers de `.github/workflows/`
et vérifient les propriétés qui ont motivé leur correction :

1. la collecte **ne se déclenche plus au push** — elle écrivait des commits et
   des PDF dans le dépôt distant à chaque push touchant `manifeste.json` ;
2. **aucune commande ne pousse vers `main`** ;
3. les deux écritures distantes de la collecte sont **subordonnées à `publier`** ;
4. le verrou npm ne peut être poussé que depuis `feature/interface-web` ;
5. **aucun workflow ne déploie** l'application.

Un fichier de workflow n'est pas du code exécutable : ces assertions portent sur
le texte, ce qui suffit à empêcher le retour des défauts constatés.
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


class TestAucunDeploiement(unittest.TestCase):
    def test_aucun_workflow_ne_deploie(self):
        for nom in sorted(os.listdir(WORKFLOWS)):
            if not nom.endswith((".yml", ".yaml")):
                continue
            contenu = lire(os.path.join(WORKFLOWS, nom)).lower()
            for mot in MOTS_DEPLOIEMENT:
                self.assertNotIn(mot, contenu, "%s contient « %s »" % (nom, mot))


class TestAucunPushVersMain(unittest.TestCase):
    def test_aucune_commande_ne_pousse_vers_main(self):
        for nom in sorted(os.listdir(WORKFLOWS)):
            if not nom.endswith((".yml", ".yaml")):
                continue
            for numero, ligne in enumerate(lire(os.path.join(WORKFLOWS, nom)).splitlines(), 1):
                if "git" in ligne and "push" in ligne:
                    self.assertNotRegex(ligne, r"(^|[\s:])main\b",
                                        "%s:%d pousse vers main" % (nom, numero))


class TestCollecteManuelle(unittest.TestCase):
    def setUp(self):
        self.contenu = lire(COLLECTE)

    def test_pas_de_declenchement_au_push(self):
        """Le push ne doit plus lancer la collecte (écritures distantes)."""
        self.assertNotRegex(self.contenu, r"(?m)^\s{2}push:\s*$",
                            "collecte-corpus se déclenche encore au push")

    def test_execution_manuelle_conservee(self):
        self.assertRegex(self.contenu, r"(?m)^\s{2}workflow_dispatch:\s*$")
        for entree in ("forcer", "ocr", "publier"):
            self.assertRegex(self.contenu, r"(?m)^\s{6}%s:\s*$" % entree)

    def test_publier_est_desactive_par_defaut(self):
        bloc = re.search(r"publier:(.*?)\n\s{6}\w+:", self.contenu, re.S)
        self.assertIsNotNone(bloc, "entrée `publier` absente")
        self.assertIn("default: false", bloc.group(1))

    def test_les_deux_ecritures_sont_soumises_a_publier(self):
        """Chaque `git push` de la collecte doit être précédé de `if: inputs.publier`."""
        lignes = self.contenu.splitlines()
        pousses = [i for i, l in enumerate(lignes) if "git" in l and "push" in l]
        self.assertEqual(len(pousses), 2, "nombre d'écritures distantes inattendu")
        for indice in pousses:
            fenetre = "\n".join(lignes[max(0, indice - 30):indice])
            self.assertIn("if: inputs.publier", fenetre,
                          "une écriture distante n'est pas gardée : ligne %d" % (indice + 1))

    def test_les_artefacts_remplacent_la_publication(self):
        self.assertIn("actions/upload-artifact@v4", self.contenu)
        self.assertIn("pdf-collectes", self.contenu)
        self.assertIn("constats-collecte", self.contenu)

    def test_permissions_lecture_seule_par_defaut(self):
        bloc = re.search(r"(?m)^permissions:\n((?:[ \t]+.*\n|\n)*)", self.contenu)
        self.assertIsNotNone(bloc)
        self.assertIn("contents: read", bloc.group(1))


class TestVerrouInterface(unittest.TestCase):
    def test_le_verrou_ne_part_que_de_feature_interface_web(self):
        contenu = lire(INTERFACE)
        self.assertIn("refs/heads/feature/interface-web", contenu)
        # La permission d'écriture reste confinée au travail qui en a besoin.
        self.assertRegex(contenu, r"(?s)verrou-des-versions:.*?contents: write")

    def test_permissions_lecture_seule_par_defaut(self):
        contenu = lire(INTERFACE)
        bloc = re.search(r"(?m)^permissions:\n((?:[ \t]+.*\n|\n)*)", contenu)
        self.assertIsNotNone(bloc)
        self.assertIn("contents: read", bloc.group(1))


if __name__ == "__main__":
    unittest.main(verbosity=2)
