# Réponses réelles du moteur

Ces fichiers sont des réponses **enregistrées** de `bin/serveur_api.py`, obtenues le
2026-10-17 en appelant le serveur local avec `curl` (commit `2dca704` du moteur).
Elles n'ont pas été retouchées : certaines contiennent volontairement des chemins de
fichiers du serveur (`traceabilite`, `brouillon.genere.fichier_txt`) pour vérifier que
l'interface les retire.

| Fichier | Requête |
|---|---|
| `sante.json` | `GET /sante` |
| `ouvrir_caution.json` | `POST /ouvrir` « Mon bailleur garde ma caution de deux mois… » |
| `ouvrir_hors.json` | `POST /ouvrir` « Mon patron ne me paie plus mon salaire… » (hors catalogue) |
| `ouvrir_urgence.json` | `POST /ouvrir` « On veut m'expulser demain matin… » (urgence ÉLEVÉE, verrous) |
| `ouvrir_refus.json` | `POST /ouvrir` demande de fausse quittance (refus) |
| `repondre_caution.json` | `POST /repondre` `{"logement": "oui, …"}` |
| `repondre_urgence_vide.json` | `POST /repondre` sans réponse (fait manquant) |
| `repondre_deja.json` | second `POST /repondre` sur un dossier déjà clos |

Quand un test a besoin d'un cas que le moteur ne produit pas aujourd'hui (texte OCR
non recoupé, référence non vérifiée), il **dérive** une copie en mémoire et le dit
dans son nom. Ces variantes ne sont jamais servies par l'application.
