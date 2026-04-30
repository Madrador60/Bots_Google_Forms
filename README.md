# Google Form Studio

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-0078D6?logo=windows&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Status](https://img.shields.io/badge/Status-Ready-success)

Google Form Studio est un outil Windows pour analyser un Google Form public, préparer des réponses, simuler un envoi et piloter le tout depuis une interface graphique simple.

Le projet peut aussi s'utiliser depuis le terminal avec la commande `googleform`.

## Installation rapide

Ouvrir PowerShell, coller cette commande, puis appuyer sur Entrée :

```powershell
irm https://raw.githubusercontent.com/Madrador60/Bots_Google_Forms/main/install.ps1 | iex
```

L'installateur :

- télécharge la dernière version depuis GitHub;
- installe le projet dans le dossier utilisateur Windows;
- installe les dépendances Python;
- ajoute la commande `googleform` au PATH utilisateur;
- lance l'application à la fin de l'installation.

Si `googleform` n'est pas reconnu après l'installation, fermer puis rouvrir le CMD ou PowerShell.

## Utilisation

Lancer l'interface graphique :

```bat
googleform
```

Autres commandes :

```bat
googleform cli      Lance le mode terminal
googleform install  Installe ou réinstalle les dépendances
googleform uninstall Désinstalle Google Form Studio
googleform test     Lance les tests du projet
googleform help     Affiche l'aide
```

## Fonctionnalités

- Analyse d'un Google Form public depuis son URL
- Interface graphique Windows
- Remplissage manuel
- Génération automatique de réponses
- Profils automatiques : prudent, équilibré, varié
- Simulation sans envoi
- Envoi unitaire
- Envoi en série avec progression
- Pause, reprise et arrêt propre d'une série
- Journal récent local
- Suppression de l'historique local depuis l'interface

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

## Confidentialité

Chaque machine garde son propre historique local.

Les journaux, les derniers formulaires analysés et les dernières simulations ne sont pas envoyés sur GitHub. Ils restent uniquement sur le PC de l'utilisateur.

Le dépôt ignore volontairement :

- `logs/*`
- `runtime/*`
- `__pycache__/`
- `*.pyc`
- les environnements virtuels Python
- les dossiers de build

Seuls `logs/.gitkeep` et `runtime/.gitkeep` sont conservés pour garder les dossiers dans le dépôt.

Dans l'application, le bouton `Effacer l'historique local` supprime :

- le journal récent;
- le journal du lanceur Windows;
- le dernier formulaire analysé;
- la dernière simulation sauvegardée.

## Prérequis

- Windows 10 ou Windows 11
- Python 3.10 ou plus récent
- Option `Add Python to PATH` cochée pendant l'installation de Python

Téléchargement Python :

[https://www.python.org/downloads/windows/](https://www.python.org/downloads/windows/)

## Installation manuelle

1. Télécharger ou cloner ce dépôt.
2. Ouvrir le dossier `Bots_Google_Forms`.
3. Double-cliquer sur `Installer_Dependances_Windows.bat`.
4. Double-cliquer sur `Lancer_GoogleForm_Studio.bat`.

Pour rendre `googleform` disponible dans tous les terminaux :

1. Double-cliquer sur `Installer_Commande_CMD_Windows.bat`.
2. Fermer puis rouvrir le CMD ou PowerShell.
3. Taper `googleform`.

## Désinstallation

Depuis le CMD ou PowerShell :

```bat
googleform uninstall
```

Cette commande retire `googleform` du PATH utilisateur et supprime le dossier installé dans `%LOCALAPPDATA%\Bots_Google_Forms`.

Si vous utilisez le dossier téléchargé manuellement, vous pouvez aussi lancer :

```bat
Desinstaller_GoogleForm_Studio.bat
```

## Tests

Depuis le dossier du projet :

```bat
Verifier_Projet_Windows.bat
```

Ou avec la commande installée :

```bat
googleform test
```

Commande Python directe :

```bat
py -3 -m unittest discover -s tests -p "test_*.py"
```

## Structure du projet

```text
Bots_Google_Forms/
├─ Bot_GoogleForm_Intelligent.py        Moteur principal
├─ Interface_GoogleForm_Studio.py       Interface graphique Tkinter
├─ googleform.bat                       Commande principale Windows
├─ install.ps1                          Installation PowerShell en une ligne
├─ uninstall.ps1                        Désinstallation PowerShell
├─ Installer_Commande_CMD_Windows.bat   Ajoute googleform au PATH utilisateur
├─ Installer_Dependances_Windows.bat    Installe les dépendances Python
├─ Desinstaller_GoogleForm_Studio.bat   Désinstalle l'application
├─ Lancer_GoogleForm_Studio.bat         Lance l'application
├─ Verifier_Projet_Windows.bat          Lance les vérifications
├─ requirements.txt                     Dépendances Python
├─ logs/                                Journaux locaux non partagés
├─ runtime/                             Données locales temporaires
└─ tests/                               Tests automatiques
```

## Dépannage

Python n'est pas reconnu :

- installer Python depuis le site officiel;
- cocher `Add Python to PATH`;
- fermer puis rouvrir le terminal.

`googleform` n'est pas reconnu :

- fermer puis rouvrir le CMD ou PowerShell;
- relancer `Installer_Commande_CMD_Windows.bat`.

L'interface ne s'ouvre pas :

- lancer `googleform test`;
- vérifier `logs/google_form_studio.log`.

## Notes

- Le formulaire Google doit être public.
- Certains formulaires peuvent avoir une structure atypique.
- Google Forms peut modifier son fonctionnement avec le temps.
- Utiliser l'outil uniquement sur des formulaires que vous êtes autorisé à tester ou administrer.
