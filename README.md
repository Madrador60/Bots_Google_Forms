# Google Form Studio - Windows

Google Form Studio est un outil Python pour analyser un Google Form public, préparer des réponses, simuler un envoi et lancer des envois depuis une interface graphique Windows ou depuis le terminal.

Le projet est prêt pour Windows et peut s'utiliser avec une commande `googleform` dans le CMD ou PowerShell.

## Installation en une ligne

Ouvrir PowerShell, puis coller cette commande:

```powershell
irm https://raw.githubusercontent.com/Madrador60/Bots_Google_Forms/main/install.ps1 | iex
```

Cette commande:

- télécharge le projet depuis GitHub;
- l'installe dans le dossier utilisateur Windows;
- installe les dépendances Python;
- ajoute la commande `googleform` au `PATH` utilisateur.

Après l'installation, fermer puis rouvrir le terminal si la commande n'est pas reconnue.

## Lancement

Depuis le CMD ou PowerShell:

```bat
googleform
```

Commandes disponibles:

```bat
googleform          Lance l'interface graphique
googleform cli      Lance le mode terminal
googleform install  Installe les dépendances Python
googleform test     Lance les tests
googleform help     Affiche l'aide
```

## Installation manuelle

Si vous préférez télécharger le projet manuellement:

1. Télécharger ou cloner ce dépôt.
2. Ouvrir le dossier `Bots_Google_Forms`.
3. Double-cliquer sur `Installer_Dependances_Windows.bat`.
4. Double-cliquer sur `Lancer_GoogleForm_Studio.bat`.

Pour rendre la commande `googleform` disponible partout:

1. Double-cliquer sur `Installer_Commande_CMD_Windows.bat`.
2. Fermer puis rouvrir le CMD ou PowerShell.
3. Taper `googleform`.

## Prérequis

- Windows 10 ou Windows 11
- Python 3.10 ou plus récent
- Pendant l'installation de Python, cocher `Add Python to PATH`

Lien Python officiel:

```text
https://www.python.org/downloads/windows/
```

## Fonctionnalités

- Analyse d'un Google Form public à partir de son URL
- Affichage des questions dans une interface graphique
- Remplissage manuel
- Génération automatique de réponses avec profils intelligents
- Délais minimum et maximum configurables
- Simulation sans envoi
- Envoi unitaire
- Envoi en série avec progression
- Arrêt propre d'une série
- Journal récent des analyses, simulations et envois

## Types de questions pris en charge

- Réponse courte
- Paragraphe
- Choix multiple
- Liste déroulante
- Cases à cocher
- Échelle linéaire
- Grille à choix unique
- Grille à cases
- Date
- Heure

## Vérification et tests

Depuis le dossier du projet:

```bat
Verifier_Projet_Windows.bat
```

Ou avec la commande installée:

```bat
googleform test
```

Commande Python directe:

```bat
py -3 -m unittest discover -s tests -p "test_*.py"
```

## Structure du projet

```text
Bots_Google_Forms/
├─ Bot_GoogleForm_Intelligent.py        Moteur principal
├─ Interface_GoogleForm_Studio.py       Interface graphique Tkinter
├─ googleform.bat                       Commande principale CMD/PowerShell
├─ install.ps1                          Installateur PowerShell en une ligne
├─ Installer_Commande_CMD_Windows.bat   Ajoute googleform au PATH utilisateur
├─ Installer_Dependances_Windows.bat    Installe les dépendances Python
├─ Lancer_GoogleForm_Studio.bat         Lance l'interface graphique
├─ Verifier_Projet_Windows.bat          Compile et lance les tests
├─ requirements.txt                     Dépendances Python
├─ LISEZ_MOI.txt                        Instructions locales Windows
├─ logs/                                Journaux runtime
├─ runtime/                             Derniers snapshots et simulations
└─ tests/                               Tests automatiques
```

## Fichiers générés non envoyés sur GitHub

Le dépôt ignore volontairement:

- les fichiers `__pycache__/`;
- les fichiers `.pyc`;
- `logs/activity.jsonl`;
- `runtime/last_form.json`;
- `runtime/last_simulation.json`.

Ces fichiers sont générés automatiquement pendant l'utilisation.

## Notes importantes

- Le formulaire Google doit être public.
- Certains comportements Google Forms peuvent varier selon la structure du formulaire.
- Le journal runtime est stocké en local dans `logs/activity.jsonl`.
- Le journal du lanceur Windows est stocké dans `logs/google_form_studio.log`.
- L'outil dépend de la structure HTML/JavaScript de Google Forms, qui peut changer avec le temps.

## Dépôt

```text
https://github.com/Madrador60/Bots_Google_Forms
```
