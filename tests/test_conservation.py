# -*- coding: utf-8 -*-
"""Conservation temporaire : échéance inscrite à la création, dossier expiré jamais servi.

Données synthétiques uniquement : identifiants `TEST_CONSERVATION_*`, récits
fictifs, supprimés à la fin. Le vieillissement d'un dossier est simulé en
réécrivant son `CONSERVATION.json` (ou sa date d'ouverture) dans le passé.
"""

import datetime
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import config  # noqa: E402
from core import conservation, service  # noqa: E402

UTC = datetime.timezone.utc
DEMANDE = "Mon bailleur garde ma caution depuis deux mois."
PREFIXE = "TEST_CONSERVATION_"


def _vieillir(dossier_id, heures):
    """Place l'échéance `heures` dans le passé (négatif : dans le futur)."""
    chemin = config.dossier_utilisateur(dossier_id) / conservation.FICHIER
    meta = json.loads(chemin.read_text(encoding="utf-8"))
    meta["expire_le"] = (conservation.maintenant() - datetime.timedelta(hours=heures)).isoformat()
    chemin.write_text(json.dumps(meta), encoding="utf-8")


def _menes():
    return [n for n in os.listdir(str(config.DOSSIERS_DIR)) if n.startswith(PREFIXE)] \
        if os.path.isdir(str(config.DOSSIERS_DIR)) else []


class TestMarquage(unittest.TestCase):

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="test-conservation-"))

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_echeance_egale_creation_plus_24_heures(self):
        cree = datetime.datetime(2026, 10, 22, 8, 0, 0, tzinfo=UTC)
        meta = conservation.marquer(self.base / "d", instant=cree, heures=24)
        self.assertEqual(meta["cree_le"], "2026-10-22T08:00:00+00:00")
        self.assertEqual(meta["expire_le"], "2026-10-23T08:00:00+00:00")
        self.assertEqual(meta["duree_heures"], 24)

    def test_le_marquage_n_est_jamais_reecrit(self):
        premier = conservation.marquer(self.base / "d", instant=datetime.datetime(2026, 1, 1, tzinfo=UTC))
        second = conservation.marquer(self.base / "d", instant=datetime.datetime(2026, 6, 1, tzinfo=UTC))
        self.assertEqual(premier, second, "une nouvelle ouverture ne repousse pas l'échéance")

    def test_fichier_prive_et_sans_donnee_personnelle(self):
        conservation.marquer(self.base / "d")
        chemin = self.base / "d" / conservation.FICHIER
        self.assertEqual(os.stat(chemin).st_mode & 0o777, 0o600)
        self.assertEqual(sorted(json.loads(chemin.read_text())), ["cree_le", "duree_heures", "expire_le", "version"])

    def test_limite_a_la_seconde(self):
        cree = datetime.datetime(2026, 10, 22, 8, 0, 0, tzinfo=UTC)
        conservation.marquer(self.base / "d", instant=cree, heures=24)
        echeance = cree + datetime.timedelta(hours=24)
        self.assertFalse(conservation.est_expire(self.base / "d", instant=echeance - datetime.timedelta(seconds=1)))
        self.assertTrue(conservation.est_expire(self.base / "d", instant=echeance))

    def test_replis_ouvert_le_puis_mtime(self):
        dossier = self.base / "ancien"
        dossier.mkdir()
        (dossier / "DOSSIER_EN_COURS.json").write_text(json.dumps({"ouvert_le": "2026-10-20T10:00:00+00:00"}))
        echeance, source = conservation.expiration(dossier, heures=24)
        self.assertEqual((echeance.isoformat(), source), ("2026-10-21T10:00:00+00:00", "ouvert_le"))
        nu = self.base / "nu"
        nu.mkdir()
        _, source = conservation.expiration(nu, heures=24)
        self.assertEqual(source, "mtime")
        self.assertEqual(conservation.expiration(self.base / "absent"), (None, None))

    def test_fichier_corrompu_ne_raccourcit_pas_l_echeance(self):
        dossier = self.base / "corrompu"
        dossier.mkdir()
        (dossier / conservation.FICHIER).write_text("{pas du json")
        _, source = conservation.expiration(dossier, heures=24)
        self.assertEqual(source, "mtime")
        self.assertFalse(conservation.est_expire(dossier))

    def test_duree_configurable_et_validee(self):
        self.assertEqual(conservation.duree_heures({}), 24)
        self.assertEqual(conservation.duree_heures({conservation.VARIABLE_DUREE: "48"}), 48)
        for brut in ("0", "-1", "abc", "1.5"):
            with self.subTest(brut=brut), self.assertRaises(conservation.DureeInvalide):
                conservation.duree_heures({conservation.VARIABLE_DUREE: brut})


class TestServiceRefuseLesDossiersExpires(unittest.TestCase):

    def setUp(self):
        self.ids = []

    def tearDown(self):
        for identifiant in self.ids:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)

    def _ouvrir(self, suffixe):
        identifiant = PREFIXE + suffixe
        self.ids.append(identifiant)
        shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
        resultat = service.ouvrir(identifiant, DEMANDE)
        self.assertTrue(resultat["ok"], resultat)
        return identifiant

    def test_l_ouverture_inscrit_l_echeance(self):
        identifiant = self._ouvrir("OUVERTURE")
        meta = conservation.lire(config.dossier_utilisateur(identifiant))
        cree = datetime.datetime.fromisoformat(meta["cree_le"])
        expire = datetime.datetime.fromisoformat(meta["expire_le"])
        self.assertEqual(expire - cree, datetime.timedelta(hours=24))
        self.assertLess(abs((conservation.maintenant() - cree).total_seconds()), 120)

    def test_avant_l_echeance_le_dossier_est_servi(self):
        identifiant = self._ouvrir("AVANT")
        _vieillir(identifiant, -1)
        resultat = service.repondre(identifiant, {"logement": "oui"})
        self.assertTrue(resultat["ok"], resultat)

    def test_apres_l_echeance_repondre_et_courrier_sont_refuses(self):
        identifiant = self._ouvrir("APRES")
        _vieillir(identifiant, 1)
        for resultat in (service.repondre(identifiant, {"logement": "oui"}),
                         service.rediger_courrier(identifiant, {"expediteur": "Personne Fictive"})):
            self.assertFalse(resultat["ok"])
            self.assertEqual(resultat["erreur"]["code"], "DOSSIER_EXPIRE")
            self.assertNotIn("caution", json.dumps(resultat, ensure_ascii=False),
                             "aucun élément du récit ne doit être renvoyé")

    def test_un_dossier_expire_n_est_ni_modifie_ni_recree(self):
        identifiant = self._ouvrir("INTACT")
        _vieillir(identifiant, 1)
        dossier = config.dossier_utilisateur(identifiant)
        avant = sorted(p.name for p in dossier.rglob("*"))
        service.repondre(identifiant, {"logement": "oui"})
        service.rediger_courrier(identifiant, {"expediteur": "Personne Fictive"})
        service.ouvrir(identifiant, DEMANDE)
        self.assertEqual(sorted(p.name for p in dossier.rglob("*")), avant)

    def test_la_personne_peut_toujours_supprimer_un_dossier_expire(self):
        identifiant = self._ouvrir("SUPPRESSION")
        _vieillir(identifiant, 1)
        self.assertTrue(service.supprimer(identifiant)["data"]["supprime"])
        self.assertFalse(config.dossier_utilisateur(identifiant).exists())

    def test_une_consultation_supprimee_ne_renvoie_rien(self):
        identifiant = self._ouvrir("DISPARUE")
        service.supprimer(identifiant)
        resultat = service.repondre(identifiant, {"logement": "oui"})
        self.assertFalse(resultat["ok"])
        self.assertFalse(config.dossier_utilisateur(identifiant).exists(), "rien n'est recréé")


def tearDownModule():
    for nom in _menes():
        shutil.rmtree(str(config.DOSSIERS_DIR / nom), ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
