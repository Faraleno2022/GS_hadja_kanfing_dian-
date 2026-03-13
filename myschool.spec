# -*- mode: python ; coding: utf-8 -*-
"""
MySchoolGN - PyInstaller Spec File
====================================
Auteur  : GS Hadja Kanfing Dian
Version : 1.0.0

Pour compiler :
    venv\Scripts\python.exe -m PyInstaller --clean --noconfirm myschool.spec
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

PROJECT_DIR = SPECPATH

# ─── Hidden imports ────────────────────────────────────────────────────────────
hiddenimports = []

# Django core (sans GIS qui exige GDAL)
hiddenimports += collect_submodules('django', filter=lambda name: 'gis' not in name)
hiddenimports += collect_submodules('django.contrib.admin')
hiddenimports += collect_submodules('django.contrib.auth')
hiddenimports += collect_submodules('django.contrib.contenttypes')
hiddenimports += collect_submodules('django.contrib.sessions')
hiddenimports += collect_submodules('django.contrib.messages')
hiddenimports += collect_submodules('django.contrib.staticfiles')
hiddenimports += collect_submodules('django.contrib.humanize')
hiddenimports += collect_submodules('django.template')
hiddenimports += collect_submodules('django.db.backends.sqlite3')

# Applications du projet
for _app in ['eleves', 'paiements', 'depenses', 'salaires', 'utilisateurs',
             'rapports', 'administration', 'bus', 'notes', 'abonnements',
             'chatbot', 'ecole_moderne']:
    try:
        hiddenimports += collect_submodules(_app)
    except Exception:
        pass

# Librairies tierces
hiddenimports += collect_submodules('reportlab')
hiddenimports += collect_submodules('openpyxl')
hiddenimports += collect_submodules('PIL')

# Pandas (import/export eleves)
try:
    hiddenimports += collect_submodules('pandas')
    hiddenimports += collect_submodules('numpy')
except Exception:
    pass

# WeasyPrint et ses dependances
for _wp_pkg in ['weasyprint', 'pydyf', 'fonttools', 'cssselect2',
                'tinycss2', 'html5lib', 'brotli', 'zopfli']:
    try:
        hiddenimports += collect_submodules(_wp_pkg)
    except Exception:
        pass

# Modules explicites
hiddenimports += [
    # Django management
    'django.core.management.commands.migrate',
    'django.core.management.commands.collectstatic',
    'django.core.management.commands.runserver',
    'django.db.backends.sqlite3.base',
    'django.db.backends.sqlite3.introspection',
    'django.contrib.admin.apps',
    # Projet
    'ecole_moderne.settings',
    'ecole_moderne.urls',
    'ecole_moderne.wsgi',
    'ecole_moderne.static_views',
    'ecole_moderne.middleware',
    'ecole_moderne.security_middleware',
    'ecole_moderne.image_cache_middleware',
    'ecole_moderne.image_optimization_middleware',
    # Utils
    'load_env',
    'dotenv',
    'sqlite3',
    '_sqlite3',
    'sqlparse',
    'asgiref',
    'asgiref.sync',
    'asgiref.local',
    'six',
    'dateutil',
    'dateutil.parser',
    'dateutil.relativedelta',
    # Tkinter (fenêtre d'activation de licence)
    'tkinter',
    'tkinter.ttk',
    'tkinter.filedialog',
    'tkinter.messagebox',
    '_tkinter',
    # Encodages Windows
    'encodings',
    'encodings.utf_8',
    'encodings.ascii',
    'encodings.latin_1',
    'encodings.cp1252',
    'encodings.cp850',
    # Reseau / stdlib
    'socket',
    'webbrowser',
    'threading',
    'winreg',
    'hmac',
    'hashlib',
    'base64',
    'json',
    # JWT / auth
    'jwt',
    'jwt.algorithms',
]

# ─── Données à inclure ─────────────────────────────────────────────────────────
datas = []

def _add_if_exists(src_rel, dst):
    src = os.path.join(PROJECT_DIR, src_rel)
    if os.path.exists(src):
        datas.append((src, dst))

# Dossiers principaux
_add_if_exists('templates', 'templates')
_add_if_exists('static', 'static')
_add_if_exists('staticfiles', 'staticfiles')
_add_if_exists('media', 'media')

# Base de données (copiée, migrée automatiquement au premier lancement)
_add_if_exists('db.sqlite3', '.')

# Fichier .env
_add_if_exists('.env', '.')

# Chargeur d'env (license_manager est un .pyd Nuitka — voir binaries)
_add_if_exists('load_env.py', '.')

# Templates et templatetags + migrations de chaque app
for _app in ['eleves', 'paiements', 'depenses', 'salaires', 'utilisateurs',
             'rapports', 'administration', 'bus', 'notes', 'abonnements', 'chatbot']:
    _add_if_exists(os.path.join(_app, 'templates'), os.path.join(_app, 'templates'))
    _add_if_exists(os.path.join(_app, 'templatetags'), os.path.join(_app, 'templatetags'))
    _add_if_exists(os.path.join(_app, 'fixtures'), os.path.join(_app, 'fixtures'))
    _add_if_exists(os.path.join(_app, 'migrations'), os.path.join(_app, 'migrations'))

# Migrations ecole_moderne
_add_if_exists('ecole_moderne/migrations', 'ecole_moderne/migrations')

# Données Django (templates admin, etc.)
datas += collect_data_files('django.contrib.admin')
datas += collect_data_files('django.contrib.auth')
datas += collect_data_files('django')

# ReportLab (polices)
try:
    datas += collect_data_files('reportlab')
except Exception:
    pass

# WeasyPrint (feuilles CSS par défaut)
try:
    datas += collect_data_files('weasyprint')
except Exception:
    pass

try:
    datas += collect_data_files('tinycss2')
except Exception:
    pass

# Pillow
try:
    datas += collect_data_files('PIL')
except Exception:
    pass

# ─── Icône ────────────────────────────────────────────────────────────────────
_icon_candidates = [
    os.path.join(PROJECT_DIR, 'myschool.ico'),
    os.path.join(PROJECT_DIR, 'static', 'logos', 'logo.ico'),
]
_icon = next((c for c in _icon_candidates if os.path.exists(c)), None)

# ─── DLLs GTK/Pango/Cairo pour WeasyPrint (depuis MSYS2) ──────────────────────
_gtk_dll_dir = r'C:\msys64\mingw64\bin'
_gtk_dlls = [
    'libpango-1.0-0.dll',
    'libpangocairo-1.0-0.dll',
    'libpangoft2-1.0-0.dll',
    'libpangowin32-1.0-0.dll',
    'libcairo-2.dll',
    'libcairo-gobject-2.dll',
    'libgobject-2.0-0.dll',
    'libglib-2.0-0.dll',
    'libgio-2.0-0.dll',
    'libgmodule-2.0-0.dll',
    'libgdk_pixbuf-2.0-0.dll',
    'libfontconfig-1.dll',
    'libfreetype-6.dll',
    'libfribidi-0.dll',
    'libharfbuzz-0.dll',
    'libintl-8.dll',
    'libiconv-2.dll',
    'libpixman-1-0.dll',
    'libpng16-16.dll',
    'libexpat-1.dll',
    'libpcre2-8-0.dll',
    'zlib1.dll',
    'libffi-8.dll',
    'libgraphite2.dll',
    'libbrotlidec.dll',
    'libbrotlicommon.dll',
    'libbz2-1.dll',
    'libstdc++-6.dll',
    'libgcc_s_seh-1.dll',
    'libwinpthread-1.dll',
]
_gtk_binaries = []
for _dll in _gtk_dlls:
    _dll_path = os.path.join(_gtk_dll_dir, _dll)
    if os.path.exists(_dll_path):
        _gtk_binaries.append((_dll_path, '.'))
    else:
        print(f'[ATTENTION] DLL manquante: {_dll}')

# GdkPixbuf loaders (nécessaires pour le rendu d'images dans les PDFs)
_pixbuf_loaders_dir = r'C:\msys64\mingw64\lib\gdk-pixbuf-2.0\2.10.0\loaders'
if os.path.isdir(_pixbuf_loaders_dir):
    import glob as _glob
    for _loader in _glob.glob(os.path.join(_pixbuf_loaders_dir, '*.dll')):
        _gtk_binaries.append((_loader, 'lib/gdk-pixbuf-2.0/2.10.0/loaders'))
    _loaders_cache = os.path.join(os.path.dirname(_pixbuf_loaders_dir), 'loaders.cache')
    if os.path.exists(_loaders_cache):
        datas.append((_loaders_cache, 'lib/gdk-pixbuf-2.0/2.10.0'))

# ─── Analyse ──────────────────────────────────────────────────────────────────
a = Analysis(
    [os.path.join(PROJECT_DIR, 'run_server.py')],
    pathex=[PROJECT_DIR],
    binaries=[
        # Nuitka-compiled license module (native binary — non-decompilable)
        (os.path.join(PROJECT_DIR, 'dist_nuitka', 'license_manager.cp313-win_amd64.pyd'), '.'),
    ] + _gtk_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'scipy',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'mypy',
        'black',
        'flake8',
        'django.contrib.gis',
        'mysqlclient',
        'PyMySQL',
        'license_manager',   # excluded: native .pyd is in binaries instead
    ],
    noarchive=False,
    optimize=2,   # strip docstrings + assert statements
)

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MySchoolGN',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=_icon,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MySchoolGN',
)

# ─── Post-build: remove license_manager.py source, keep only the .pyd ─────────
import shutil as _shutil
_internal = os.path.join(DISTPATH, 'MySchoolGN', '_internal')
_py_src = os.path.join(_internal, 'license_manager.py')
_pyc_dir = os.path.join(_internal, '__pycache__')
_pyd_src = os.path.join(PROJECT_DIR, 'dist_nuitka', 'license_manager.cp313-win_amd64.pyd')
_pyd_dst = os.path.join(_internal, 'license_manager.cp313-win_amd64.pyd')

if os.path.exists(_py_src):
    os.remove(_py_src)
    print('[Protection] Removed license_manager.py from dist')
if os.path.exists(_pyc_dir):
    for _f in os.listdir(_pyc_dir):
        if 'license_manager' in _f:
            os.remove(os.path.join(_pyc_dir, _f))
if os.path.exists(_pyd_src) and not os.path.exists(_pyd_dst):
    _shutil.copy2(_pyd_src, _pyd_dst)
    print('[Protection] Installed license_manager.pyd in dist')
print('[Protection] license_manager protection applied.')
