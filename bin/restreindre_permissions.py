# -*- coding: utf-8 -*-
"""Ramène les dossiers de consultation au régime 700 / 600.

    python3 bin/restreindre_permissions.py              # simulation, n'écrit rien
    python3 bin/restreindre_permissions.py --appliquer  # applique

POURQUOI
--------
Les dossiers de `DOSSIERS/` contiennent le récit personnel d'une personne
(violences, famille, dettes, santé) et les courriers produits. Créés avant la
correction, ils étaient en 755/644 : **tout compte local de la machine pouvait
les lire**. Les nouveaux dossiers naissent en 700/600 (`config.creer_dossier_prive`,
`config.ecrire_fichier_prive`) ; ce script traite les anciens.

CE QU'IL FAIT
-------------
* dossiers → 700 (lecture, écriture, traversée : propriétaire seulement) ;
* fichiers → 600 ;
* rien d'autre : aucun fichier supprimé, aucun contenu modifié.

Il ne touche QUE `DOSSIERS/`, jamais `KNOWLEDGE/` ni le dépôt.
"""

import argparse
import os
import stat
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402


def parcourir(racine, appliquer):
    modifies, deja_ok, erreurs = 0, 0, []
    for chemin, dossiers, fichiers in os.walk(str(racine)):
        for dossier in dossiers:
            modifies, deja_ok = _regler(os.path.join(chemin, dossier), dossier=True,
                                        appliquer=appliquer, modifies=modifies,
                                        deja_ok=deja_ok, erreurs=erreurs)
        for fichier in fichiers:
            modifies, deja_ok = _regler(os.path.join(chemin, fichier), dossier=False,
                                        appliquer=appliquer, modifies=modifies,
                                        deja_ok=deja_ok, erreurs=erreurs)
    return modifies, deja_ok, erreurs


def _regler(chemin, dossier, appliquer, modifies, deja_ok, erreurs):
    attendu = config.PERMISSIONS_DOSSIER if dossier else config.PERMISSIONS_FICHIER
    try:
        actuel = stat.S_IMODE(os.stat(chemin, follow_symlinks=False).st_mode)
    except OSError as erreur:
        erreurs.append((chemin, str(erreur)))
        return modifies, deja_ok
    if actuel == attendu:
        return modifies, deja_ok + 1
    if appliquer:
        try:
            os.chmod(chemin, attendu)
        except OSError as erreur:
            erreurs.append((chemin, str(erreur)))
            return modifies, deja_ok
    print("  %-58s %s -> %s%s" % (chemin.replace(str(RACINE) + "/", "")[:58],
                                  oct(actuel), oct(attendu), "" if appliquer else "  (simulation)"))
    return modifies + 1, deja_ok


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--appliquer", action="store_true",
                           help="écrit les permissions (sans cette option : simulation)")
    analyseur.add_argument("--racine", default=str(config.DOSSIERS_DIR))
    arguments = analyseur.parse_args(argv)

    racine = arguments.racine
    if not os.path.isdir(racine):
        print("Aucun dossier de consultation : %s" % racine)
        return 0

    print("Racine : %s" % racine)
    # La racine elle-même : 755 laissait lister les identifiants de consultation.
    modifies_racine, _ = _regler(racine, dossier=True, appliquer=arguments.appliquer,
                                 modifies=0, deja_ok=0, erreurs=[])
    modifies, deja_ok, erreurs = parcourir(racine, arguments.appliquer)
    modifies += modifies_racine
    print("\n%d entrée(s) à corriger, %d déjà conformes, %d erreur(s)"
          % (modifies, deja_ok, len(erreurs)))
    for chemin, message in erreurs[:5]:
        print("  ERREUR %s : %s" % (chemin, message))
    if modifies and not arguments.appliquer:
        print("\nSimulation seulement. Relancer avec --appliquer pour écrire.")
    return 0 if not erreurs else 1


if __name__ == "__main__":
    sys.exit(main())
