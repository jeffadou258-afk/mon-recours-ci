# -*- coding: utf-8 -*-
"""Conservation des consultations — purge des consultations expirées.

Le script testé est celui qui sera installé (`web/scripts/purger-consultations.mjs`).
Tout est créé dans un répertoire temporaire, avec des dates imposées : aucun
dossier réel n'est lu ni touché. Les récits sont des chaînes fictives.

Deux familles de cas :
* politique de 24 heures, échéance lue dans `CONSERVATION.json` (dossiers créés
  par le moteur à partir de cette version) ou, à défaut, dans `ouvert_le` ;
* dossiers anciens sans aucune métadonnée : repli sur la date de modification
  (règle historique, exprimée ici en jours avec `--jours`).
"""

import datetime
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "web" / "scripts" / "purger-consultations.mjs"
JOUR = 86400
HEURE = 3600

IDENTIFIANTS = {
    "recent": "web-aaaaaaaa-1111-4111-8111-111111111111",
    "limite": "web-bbbbbbbb-2222-4222-8222-222222222222",
    "ancien": "web-cccccccc-3333-4333-8333-333333333333",
    "hors_motif": "CLI_DEMO",
}

CLES_JOURNAL = sorted(["horodatage", "mode", "heures", "eligibles", "conserves", "supprimes",
                       "restes_repris", "echecs", "sources", "duree_ms"])


def _iso(instant):
    return datetime.datetime.fromtimestamp(instant, datetime.timezone.utc).replace(microsecond=0).isoformat()


class _Base(unittest.TestCase):

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="test-purge-"))
        os.chmod(self.base, 0o700)
        self.racine = self.base / "DOSSIERS"
        self.racine.mkdir()
        self.journal = self.base / "purge.jsonl"

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _dossier(self, nom, mtime=None, cree=None, expire=None, ouvert_le=None, pdf=False):
        chemin = self.racine / nom
        chemin.mkdir()
        (chemin / "CONVERSATION.json").write_text('{"recit": "fictif"}', encoding="utf-8")
        if cree is not None:
            meta = {"version": 1, "cree_le": _iso(cree), "expire_le": _iso(expire), "duree_heures": 24}
            (chemin / "CONSERVATION.json").write_text(json.dumps(meta), encoding="utf-8")
        if ouvert_le is not None:
            (chemin / "DOSSIER_EN_COURS.json").write_text(
                json.dumps({"ouvert_le": ouvert_le, "demande": "récit fictif"}), encoding="utf-8")
        if pdf:
            (chemin / "BROUILLONS").mkdir()
            (chemin / "BROUILLONS" / "20261022-080000_reclamation.pdf").write_bytes(b"%PDF-1.4 fictif")
            (chemin / "BROUILLONS" / "20261022-080000_reclamation.txt").write_text("brouillon fictif", encoding="utf-8")
        if mtime is not None:
            os.utime(chemin, (mtime, mtime))
        return chemin

    def _lancer(self, *arguments):
        environnement = dict(os.environ,
                             MONRECOURS_DOSSIERS=str(self.racine),
                             MONRECOURS_JOURNAL_PURGE=str(self.journal))
        return subprocess.run(["node", str(SCRIPT), *arguments],
                              capture_output=True, text=True, env=environnement)

    def _restants(self):
        return sorted(p.name for p in self.racine.iterdir())

    def _journal(self):
        return [json.loads(l) for l in self.journal.read_text(encoding="utf-8").splitlines() if l.strip()]


@unittest.skipUnless(shutil.which("node"), "node requis")
class TestPurge24Heures(_Base):

    def setUp(self):
        super().setUp()
        t = time.time()
        # Créé il y a 23 h, échéance dans 1 h -> conservé.
        self._dossier(IDENTIFIANTS["recent"], cree=t - 23 * HEURE, expire=t + HEURE)
        # Créé il y a 24 h + 1 min -> expiré, avec son PDF.
        self._dossier(IDENTIFIANTS["limite"], cree=t - 24 * HEURE - 60, expire=t - 60, pdf=True)
        # Créé il y a 3 jours -> expiré.
        self._dossier(IDENTIFIANTS["ancien"], cree=t - 3 * JOUR, expire=t - 2 * JOUR)

    def test_moins_de_24_heures_conserve(self):
        self._lancer("--heures", "24", "--confirmer")
        self.assertIn(IDENTIFIANTS["recent"], self._restants())

    def test_plus_de_24_heures_supprime_pdf_compris(self):
        self._lancer("--heures", "24", "--confirmer")
        restants = self._restants()
        self.assertNotIn(IDENTIFIANTS["limite"], restants)
        self.assertNotIn(IDENTIFIANTS["ancien"], restants)
        self.assertEqual([p for p in self.racine.rglob("*.pdf")], [], "aucun PDF expiré ne doit subsister")
        self.assertFalse(any(n.startswith(".purge-") for n in restants), "aucun reste après succès")

    def test_l_echeance_inscrite_prime_sur_la_date_de_modification(self):
        # Modifié à l'instant, mais expiré selon CONSERVATION.json -> supprimé.
        t = time.time()
        nom = "web-eeeeeeee-5555-4555-8555-555555555555"
        self._dossier(nom, cree=t - 25 * HEURE, expire=t - HEURE, mtime=t)
        self._lancer("--heures", "24", "--confirmer")
        self.assertNotIn(nom, self._restants())

    def test_repli_sur_ouvert_le_pour_un_dossier_sans_conservation(self):
        t = time.time()
        vieux = "web-ffffffff-6666-4666-8666-666666666666"
        jeune = "web-abababab-7777-4777-8777-777777777777"
        self._dossier(vieux, ouvert_le=_iso(t - 30 * HEURE), mtime=t)
        self._dossier(jeune, ouvert_le=_iso(t - 2 * HEURE), mtime=t - 10 * JOUR)
        self._lancer("--heures", "24", "--confirmer")
        restants = self._restants()
        self.assertNotIn(vieux, restants)
        self.assertIn(jeune, restants, "ouvert_le récent l'emporte sur une date de modification ancienne")

    def test_execution_repetee_sans_effet_supplementaire(self):
        premiere = self._lancer("--heures", "24", "--confirmer")
        apres_premiere = self._restants()
        for _ in range(3):
            resultat = self._lancer("--heures", "24", "--confirmer")
            self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertEqual(premiere.returncode, 0, premiere.stderr)
        self.assertEqual(self._restants(), apres_premiere)
        self.assertEqual([e["supprimes"] for e in self._journal()], [2, 0, 0, 0])

    def test_une_consultation_expiree_ne_touche_pas_une_autre_non_expiree(self):
        self._lancer("--heures", "24", "--confirmer")
        recent = self.racine / IDENTIFIANTS["recent"]
        self.assertTrue((recent / "CONVERSATION.json").is_file())
        self.assertTrue((recent / "CONSERVATION.json").is_file())

    def test_donnees_permanentes_jamais_touchees(self):
        permanents = {
            "KNOWLEDGE/corpus_juridique.sqlite3": b"SQLite format 3\x00 fictif",
            "KNOWLEDGE/catalogue.json": b'{"fiches": []}',
            "etc/mon-recours-ci/comptes.json": b'[{"email": "fictif@exemple.invalid"}]',
            "etc/mon-recours-ci/env": b"MONRECOURS_MODE=fictif",
        }
        for relatif, contenu in permanents.items():
            chemin = self.base / relatif
            chemin.parent.mkdir(parents=True, exist_ok=True)
            chemin.write_bytes(contenu)
            vieux = time.time() - 400 * JOUR
            os.utime(chemin, (vieux, vieux))
        # Un fichier ordinaire au nom d'une consultation, dans la racine : ignoré.
        (self.racine / "web-cdcdcdcd-8888-4888-8888-888888888888").write_text("pas un dossier")
        self._lancer("--heures", "24", "--confirmer")
        for relatif, contenu in permanents.items():
            self.assertEqual((self.base / relatif).read_bytes(), contenu, relatif)
        self.assertIn("web-cdcdcdcd-8888-4888-8888-888888888888", self._restants())

    def test_reste_d_une_suppression_interrompue_est_repris(self):
        reste = self.racine / (".purge-" + IDENTIFIANTS["ancien"].replace("ccc", "ddd") + "-0a0b0c0d")
        (reste / "BROUILLONS").mkdir(parents=True)
        (reste / "BROUILLONS" / "x_reclamation.pdf").write_bytes(b"%PDF fictif")
        self._lancer("--heures", "24", "--confirmer")
        self.assertFalse(reste.exists())
        self.assertEqual(self._journal()[0]["restes_repris"], 1)

    def test_simulation_ne_supprime_rien(self):
        resultat = self._lancer("--heures", "24")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertEqual(len(self._restants()), 3)
        self.assertIn("simulation", resultat.stdout)

    def test_journal_sans_identifiant_ni_contenu(self):
        self._lancer("--heures", "24", "--confirmer")
        entree = self._journal()[0]
        self.assertEqual(sorted(entree), CLES_JOURNAL)
        texte = json.dumps(entree)
        for identifiant in IDENTIFIANTS.values():
            self.assertNotIn(identifiant, texte)
        self.assertNotIn("fictif", texte)
        self.assertEqual((entree["supprimes"], entree["conserves"], entree["heures"]), (2, 1, 24))
        self.assertEqual(entree["sources"]["conservation"], 2)


@unittest.skipUnless(shutil.which("node"), "node requis")
class TestPurgeDossiersSansMetadonnee(_Base):
    """Repli historique : date de modification, durée exprimée en jours."""

    def setUp(self):
        super().setUp()
        t = time.time()
        self._dossier(IDENTIFIANTS["recent"], mtime=t - 89 * JOUR)
        self._dossier(IDENTIFIANTS["limite"], mtime=t - 90 * JOUR - HEURE)
        self._dossier(IDENTIFIANTS["ancien"], mtime=t - 91 * JOUR)
        self._dossier(IDENTIFIANTS["hors_motif"], mtime=t - 400 * JOUR)

    def test_89_jours_conserve(self):
        self._lancer("--jours", "90", "--confirmer")
        self.assertIn(IDENTIFIANTS["recent"], self._restants())

    def test_90_jours_depasses_et_91_jours_supprimes(self):
        self._lancer("--jours", "90", "--confirmer")
        restants = self._restants()
        self.assertNotIn(IDENTIFIANTS["limite"], restants)
        self.assertNotIn(IDENTIFIANTS["ancien"], restants)

    def test_hors_motif_jamais_touche(self):
        self._lancer("--jours", "90", "--confirmer")
        self.assertIn(IDENTIFIANTS["hors_motif"], self._restants())

    def test_confirmation_necessaire(self):
        self._lancer("--jours", "90")
        self.assertTrue((self.racine / IDENTIFIANTS["ancien"]).exists())

    def test_lien_symbolique_ignore(self):
        dehors = self.base / "dehors"
        dehors.mkdir()
        (dehors / "precieux.txt").write_text("à ne pas supprimer", encoding="utf-8")
        lien = self.racine / "web-dddddddd-4444-4444-8444-444444444444"
        lien.symlink_to(dehors)
        vieux = time.time() - 200 * JOUR
        os.utime(dehors, (vieux, vieux))
        self._lancer("--jours", "90", "--confirmer")
        self.assertTrue((dehors / "precieux.txt").exists(), "la cible du lien doit survivre")
        self.assertTrue(lien.is_symlink())

    def test_racine_absente_ne_plante_pas(self):
        environnement = dict(os.environ,
                             MONRECOURS_DOSSIERS=str(self.base / "inexistant"),
                             MONRECOURS_JOURNAL_PURGE=str(self.journal))
        resultat = subprocess.run(["node", str(SCRIPT), "--heures", "24"],
                                  capture_output=True, text=True, env=environnement)
        self.assertEqual(resultat.returncode, 0)

    def test_duree_invalide_refusee(self):
        for arguments in (("--jours", "0"), ("--jours", "-5"), ("--jours", "abc"), ("--jours", ""),
                          ("--heures", "0"), ("--heures", "1.5"), ("--heures", "24", "--jours", "1"), ()):
            with self.subTest(arguments=arguments):
                self.assertEqual(self._lancer(*arguments).returncode, 2)

    def test_journal_ecrit_aussi_en_simulation(self):
        self._lancer("--jours", "90")
        entree = self._journal()[0]
        self.assertEqual(entree["mode"], "simulation")
        self.assertEqual(entree["supprimes"], 0)
        self.assertEqual(entree["heures"], 90 * 24)


if __name__ == "__main__":
    unittest.main(verbosity=2)
