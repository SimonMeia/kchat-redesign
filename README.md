# kChat Redesign

Thème CSS personnalisé pour **kChat Desktop sur Linux**, avec un injecteur Python
et un installateur local. L'AppImage peut rester gérée par Gear Lever.

- Palette indigo, couleur principale `#3c41f5`.
- Modes clair et sombre conservés.
- Sidebar en îlot, coins arrondis, fond `#F2F2F2` en mode clair.
- Messages sur fond blanc en mode clair et notifications non lues plus visibles.
- Rechargement automatique du CSS sous environ une seconde.

## Installation

Pré-requis : Linux, Git, Python avec le module `venv`, et une AppImage kChat
exécutable. L'installation des dépendances nécessite un accès réseau.
Sur Ubuntu/Debian, installer `python3-venv` si la création du virtualenv échoue.

```bash
mkdir -p ~/Documents/projets-persos
cd ~/Documents/projets-persos
git clone https://github.com/SimonMeia/kchat-redesign.git
cd kchat-redesign
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python install.py --appimage "$HOME/AppImages/kchat.appimage"
```

Adapter le chemin de l'AppImage sur chaque machine. Fermer complètement kChat,
y compris son icône dans la zone de notification, puis ouvrir **kChat (CSS custom)**
depuis le menu des applications. Utiliser ce raccourci aux prochains démarrages.
L'installateur ne ferme ni ne relance l'application.

L'installation crée :

| Emplacement | Contenu |
| --- | --- |
| `~/.config/kchat-custom/custom.css` | Lien vers le CSS du dépôt |
| `~/.local/share/kchat-custom-css/launch.py` | Lien vers l'injecteur du dépôt |
| `~/.local/share/applications/kchat-custom-css.desktop` | Raccourci adapté à la machine |
| `~/.cache/kchat-custom-css/` | Verrou de l'injecteur et journal de démarrage |

Les variables `XDG_CONFIG_HOME`, `XDG_DATA_HOME` et `XDG_CACHE_HOME` sont prises
en compte. Les fichiers remplacés sont conservés avec un suffixe `.backup-…`.
Relancer l'installateur ne duplique pas les liens.

**Conserver le dépôt à son emplacement** : les liens et le Python du virtualenv
en dépendent. En cas de déplacement, recréer le virtualenv et relancer l'installateur.

## Modifier et synchroniser le thème

Modifier `custom.css` dans le dépôt. Lorsque l'injecteur fonctionne, le changement
apparaît automatiquement dans kChat. Publier ensuite la modification :

```bash
git add custom.css
git commit -m "Ajuste le thème kChat"
git push
```

Sur les autres machines, dans leur copie du dépôt :

```bash
git pull --ff-only
```

Le CSS est rechargé automatiquement. Après une modification de `launch.py`,
fermer complètement kChat et le rouvrir avec le raccourci personnalisé.
Après une modification de `requirements.txt`, relancer :

```bash
.venv/bin/python -m pip install -r requirements.txt
```

Pour changer le chemin de l'AppImage, relancer `install.py` avec le nouveau chemin.
Si Gear Lever ou l'auto-update conserve ce chemin, rien à modifier.

## Fichiers

- `custom.css` : thème complet et variables de couleurs.
- `launch.py` : lancement et injection dans les vues kChat et Electron.
- `install.py` : liens, sauvegardes et raccourci local.
- `requirements.txt` : dépendance Python figée.
- `palette-indigo.svg` : nuancier de référence.

Le dépôt ne contient ni AppImage, ni compte, ni profil, ni messages kChat.

## Fonctionnement et dépannage

Le lanceur ouvre kChat avec le débogage Electron sur `127.0.0.1:9223`, puis applique
le CSS aux vues concernées. Le port permet d'accéder à la session Electron :
ne pas l'exposer au réseau. Un seul injecteur fonctionne à la fois pour le même
répertoire de cache.

Vérifié sur kChat Desktop **3.5.2**, avec Python **3.12** et websockets **10.4**.
Une mise à jour kChat peut modifier les classes HTML et nécessiter un ajustement
du CSS. Le journal de démarrage est dans `~/.cache/kchat-custom-css/app.log`.

Si le thème ne s'affiche pas, vérifier le chemin de l'AppImage, fermer toutes les
instances de kChat puis utiliser le raccourci personnalisé. Lancer kChat par son
raccourci habituel, sans injecteur actif, permet de retrouver l'apparence native.

Pour surveiller une instance déjà lancée avec le port de débogage actif :

```bash
.venv/bin/python launch.py --attach --css ./custom.css
```

## Désinstallation

Fermer complètement kChat, vérifier que les chemins suivants correspondent aux
liens créés par l'installateur, puis les supprimer :

```bash
rm ~/.config/kchat-custom/custom.css
rm ~/.local/share/kchat-custom-css/launch.py
rm ~/.local/share/applications/kchat-custom-css.desktop
```

Adapter les chemins si XDG est personnalisé. Les sauvegardes `.backup-…` peuvent
être restaurées si nécessaire. Le dépôt, l'AppImage et les données kChat sont conservés.
