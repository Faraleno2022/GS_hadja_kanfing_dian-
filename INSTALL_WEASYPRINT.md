# Installation de WeasyPrint sur le Serveur

## Problème
```
ModuleNotFoundError: No module named 'weasyprint'
```

## Solution

### 1. Se connecter au serveur
```bash
ssh myschoolgn@www.myschoolgn.space
```

### 2. Activer l'environnement virtuel
```bash
cd /home/myschoolgn/GS_hadja_kanfing_dian-
source /home/myschoolgn/venv/bin/activate
```

### 3. Installer les dépendances système (si nécessaire)
WeasyPrint nécessite certaines bibliothèques système. Sur Ubuntu/Debian :

```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    python3-cffi \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

### 4. Installer WeasyPrint via pip
```bash
pip install weasyprint==63.1
```

OU installer toutes les dépendances depuis requirements.txt :
```bash
pip install -r requirements.txt
```

### 5. Vérifier l'installation
```bash
python -c "import weasyprint; print(weasyprint.__version__)"
```

Devrait afficher : `63.1`

### 6. Redémarrer le serveur web
```bash
sudo systemctl restart uwsgi
# OU
sudo systemctl restart nginx
```

## Vérification

Accéder à l'URL qui causait l'erreur :
```
https://www.myschoolgn.space/notes/bulletins/pdf/?classe_id=2&eleve_id=173&periode=OCTOBRE&system_type=mensuel
```

Le PDF devrait maintenant se générer correctement.

## Notes

- **WeasyPrint** est utilisé pour générer des bulletins PDF avec un meilleur rendu HTML/CSS que ReportLab
- Version utilisée : **63.1** (dernière version stable compatible avec Python 3.13)
- Nécessite des bibliothèques système pour le rendu des polices et des images

## Dépendances de WeasyPrint

WeasyPrint installe automatiquement :
- `cairocffi` - Bindings Python pour Cairo
- `cffi` - Foreign Function Interface
- `cssselect2` - Sélecteurs CSS
- `html5lib` - Parser HTML5
- `Pillow` - Traitement d'images (déjà installé)
- `pydyf` - Génération PDF
- `pyphen` - Césure des mots
- `tinycss2` - Parser CSS

## Troubleshooting

### Erreur : "cairo >= 1.15.4 not found"
```bash
sudo apt-get install libcairo2-dev
pip install --upgrade cairocffi
```

### Erreur : "Pango not found"
```bash
sudo apt-get install libpango1.0-dev
```

### Erreur : "GdkPixbuf not found"
```bash
sudo apt-get install libgdk-pixbuf2.0-dev
```

## Alternative (si problèmes persistent)

Si l'installation de WeasyPrint pose problème, vous pouvez temporairement désactiver la génération PDF avec WeasyPrint et utiliser uniquement ReportLab :

1. Commenter l'import dans `notes/views.py` ligne 4886
2. Utiliser une autre méthode de génération PDF

Mais **WeasyPrint est recommandé** pour un meilleur rendu des bulletins.
