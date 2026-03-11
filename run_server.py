#!/usr/bin/env python
"""
MySchoolGN - Lanceur autonome offline
=======================================
Auteur  : GS Hadja Kanfing Dian
Version : 1.0.0

Ce script lance le serveur Django en mode autonome (offline).
Conçu pour être compilé en .exe avec PyInstaller.
"""
import os
import sys
import threading
import time
import webbrowser
import socket
import hashlib
import secrets
import traceback
import datetime

# ─── Répertoire de base ────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    # Mode exe PyInstaller
    BASE_DIR = os.path.dirname(sys.executable)
    # Ajouter le dossier _MEIPASS pour trouver les modules
    if hasattr(sys, '_MEIPASS'):
        sys.path.insert(0, sys._MEIPASS)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

# ─── DLLs GTK pour WeasyPrint (Windows) ───────────────────────────────────────
# Doit être fait AVANT tout import de Django / WeasyPrint
if os.name == 'nt':
    # Ajouter BASE_DIR au PATH pour que LoadLibrary trouve les DLLs GTK
    os.environ['PATH'] = BASE_DIR + os.pathsep + os.environ.get('PATH', '')
    # Python 3.8+ : répertoire explicite pour les DLLs (plus fiable que PATH)
    if hasattr(os, 'add_dll_directory'):
        try:
            os.add_dll_directory(BASE_DIR)
        except Exception:
            pass
        # Aussi _internal/ au cas où certaines DLLs s'y trouvent
        _internal = os.path.join(BASE_DIR, '_internal')
        if os.path.isdir(_internal):
            try:
                os.add_dll_directory(_internal)
            except Exception:
                pass

# ─── Générer une SECRET_KEY stable par installation ───────────────────────────
_secret_file = os.path.join(BASE_DIR, '.secret_key')
if os.path.exists(_secret_file):
    with open(_secret_file, 'r') as _f:
        _secret_key = _f.read().strip()
else:
    _secret_key = 'sk-' + secrets.token_hex(32)
    try:
        with open(_secret_file, 'w') as _f:
            _f.write(_secret_key)
    except Exception:
        _secret_key = 'offline-fallback-key-myschool-gn-v1-' + hashlib.md5(
            BASE_DIR.encode()
        ).hexdigest()

# ─── Variables d'environnement Django ─────────────────────────────────────────
os.environ['DJANGO_SETTINGS_MODULE'] = 'ecole_moderne.settings'
os.environ['DJANGO_DEBUG'] = 'true'
os.environ['DJANGO_SECRET_KEY'] = _secret_key
os.environ['OFFLINE_MODE'] = '1'
os.environ['TWILIO_DISABLED'] = '1'
os.environ['OPENAI_DISABLED'] = '1'

# Dossier de données Django (DB, media, logs)
os.environ['MYSCHOOL_BASE_DIR'] = BASE_DIR


# ─── Fenêtre d'activation de licence (tkinter) ────────────────────────────────
def show_activation_window(mid: str, trial_days_left: int = 0) -> bool:
    """
    Affiche une fenêtre graphique d'activation de licence.
    - Si trial_days_left > 0 : le bouton "Continuer l'essai" est affiché.
    - Si trial_days_left <= 0 : l'utilisateur DOIT activer pour continuer.
    Retourne True si l'application peut démarrer, False si l'utilisateur quitte.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox
    except ImportError:
        # tkinter non disponible (mode dev sans GUI) — accepter si essai actif
        return trial_days_left > 0

    result = [False]

    root = tk.Tk()
    root.title("MySchoolGN — Activation de la Licence")
    root.resizable(False, False)
    root.configure(bg='#ecf0f1')

    # ── Dimensions et centrage ──
    W, H = 540, 460
    root.geometry(f"{W}x{H}")
    root.update_idletasks()
    sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
    root.geometry(f"{W}x{H}+{(sw - W) // 2}+{(sh - H) // 2}")
    root.lift()
    root.attributes('-topmost', True)
    root.after(200, lambda: root.attributes('-topmost', False))

    # ── En-tête ──
    hdr = tk.Frame(root, bg='#1a3a5c', height=72)
    hdr.pack(fill='x')
    hdr.pack_propagate(False)
    tk.Label(hdr, text="MySchoolGN",
             font=('Arial', 22, 'bold'), bg='#1a3a5c', fg='white').place(
        relx=0.5, rely=0.35, anchor='center')
    tk.Label(hdr, text="Système de Gestion Scolaire — GS Hadja Kanfing Dian",
             font=('Arial', 8), bg='#1a3a5c', fg='#aed6f1').place(
        relx=0.5, rely=0.75, anchor='center')

    # ── Corps ──
    body = tk.Frame(root, bg='#ecf0f1', padx=24, pady=16)
    body.pack(fill='both', expand=True)

    # Message de statut
    if trial_days_left <= 0:
        status_txt = ("⚠  Votre période d'essai de 30 jours est expirée.\n"
                      "Veuillez activer votre licence pour continuer.")
        status_col = '#c0392b'
    else:
        status_txt = (f"Mode essai : {trial_days_left} jour(s) restant(s).\n"
                      "Activez votre licence pour un accès illimité.")
        status_col = '#d35400'

    tk.Label(body, text=status_txt, font=('Arial', 10), bg='#ecf0f1',
             fg=status_col, justify='left', wraplength=490).pack(
        anchor='w', pady=(0, 12))

    # ── ID Machine ──
    mid_frm = tk.LabelFrame(body, text="  Identifiant Machine  ",
                             bg='#ecf0f1', font=('Arial', 9, 'bold'),
                             fg='#1a3a5c', padx=10, pady=8, relief='groove')
    mid_frm.pack(fill='x', pady=(0, 10))
    tk.Label(mid_frm,
             text="Communiquez cet identifiant à GS Hadja Kanfing Dian pour obtenir votre licence :",
             font=('Arial', 8), bg='#ecf0f1', fg='#555').pack(anchor='w')
    mid_var = tk.StringVar(value=mid)
    tk.Entry(mid_frm, textvariable=mid_var, font=('Courier', 10, 'bold'),
             state='readonly', readonlybackground='#d5e8f7',
             relief='flat', bd=1, fg='#1a3a5c').pack(
        fill='x', pady=(4, 2), ipady=5)

    cb_btn = tk.Button(mid_frm, text="  Copier l'identifiant  ",
                       font=('Arial', 8), bg='#2980b9', fg='white',
                       relief='flat', padx=8, pady=3, cursor='hand2')
    cb_btn.pack(anchor='e', pady=(3, 0))

    def _copy_mid():
        root.clipboard_clear()
        root.clipboard_append(mid)
        cb_btn.config(text="  Copié !  ")
        root.after(2000, lambda: cb_btn.config(text="  Copier l'identifiant  "))
    cb_btn.config(command=_copy_mid)

    # ── Activation fichier .lic ──
    lic_frm = tk.LabelFrame(body,
                             text="  Activer avec un fichier de licence (.lic)  ",
                             bg='#ecf0f1', font=('Arial', 9, 'bold'),
                             fg='#1a3a5c', padx=10, pady=8, relief='groove')
    lic_frm.pack(fill='x', pady=(0, 8))

    lic_var = tk.StringVar(value="")
    lic_row = tk.Frame(lic_frm, bg='#ecf0f1')
    lic_row.pack(fill='x')
    tk.Entry(lic_row, textvariable=lic_var, font=('Arial', 9),
             state='readonly', readonlybackground='#f9f9f9',
             relief='flat', bd=1).pack(
        side='left', fill='x', expand=True, ipady=5)

    def _browse():
        p = filedialog.askopenfilename(
            title="Sélectionner votre fichier de licence",
            filetypes=[("Licence MySchoolGN", "*.lic"),
                       ("Tous les fichiers", "*.*")])
        if p:
            lic_var.set(p)
            status_lbl.config(text="", fg='#27ae60')

    tk.Button(lic_row, text="  Parcourir…  ", command=_browse,
              font=('Arial', 9), bg='#7f8c8d', fg='white',
              relief='flat', padx=6, pady=5, cursor='hand2').pack(
        side='left', padx=(6, 0))

    status_lbl = tk.Label(lic_frm, text="", font=('Arial', 9),
                          bg='#ecf0f1', fg='#27ae60')
    status_lbl.pack(anchor='w', pady=(4, 0))

    def _do_activate():
        p = lic_var.get().strip()
        if not p:
            messagebox.showwarning(
                "Fichier manquant",
                "Veuillez sélectionner un fichier .lic avant d'activer.")
            return
        try:
            import license_manager
            res = license_manager.activate_from_file(p)
        except Exception as ex:
            messagebox.showerror("Erreur", f"Erreur lors de l'activation :\n{ex}")
            return
        if res.get('valid'):
            school = res.get('school', '')
            days = res.get('days_left', 0)
            edition = res.get('edition', 'Standard')
            messagebox.showinfo(
                "Activation réussie",
                f"Licence activée avec succès !\n\n"
                f"École    : {school}\n"
                f"Édition  : {edition}\n"
                f"Validité : {days} jour(s)")
            result[0] = True
            root.destroy()
        else:
            reason = res.get('reason', 'Erreur inconnue.')
            status_lbl.config(text=f"Erreur : {reason}", fg='#c0392b')
            messagebox.showerror("Activation échouée", reason)

    # ── Boutons d'action ──
    btn_frm = tk.Frame(body, bg='#ecf0f1')
    btn_frm.pack(fill='x', pady=(4, 0))

    tk.Button(btn_frm, text="   Activer la Licence   ",
              command=_do_activate,
              font=('Arial', 11, 'bold'), bg='#27ae60', fg='white',
              relief='flat', padx=10, pady=8, cursor='hand2').pack(side='left')

    if trial_days_left > 0:
        def _continue_trial():
            result[0] = True
            root.destroy()
        tk.Button(btn_frm,
                  text=f"   Continuer l'essai ({trial_days_left}j)   ",
                  command=_continue_trial,
                  font=('Arial', 10), bg='#e67e22', fg='white',
                  relief='flat', padx=10, pady=8, cursor='hand2').pack(
            side='left', padx=(10, 0))

    def _on_close():
        if not result[0]:
            if messagebox.askyesno("Quitter", "Quitter MySchoolGN ?"):
                root.destroy()
                os._exit(0)   # Fermeture complète : tue tous les threads/processus
        else:
            root.destroy()

    tk.Button(btn_frm, text="  Quitter  ", command=_on_close,
              font=('Arial', 10), bg='#95a5a6', fg='white',
              relief='flat', padx=10, pady=8, cursor='hand2').pack(side='right')

    root.protocol("WM_DELETE_WINDOW", _on_close)
    root.mainloop()
    return result[0]


# ─── Vérification de la licence ────────────────────────────────────────────────
def check_license():
    """Vérifie la licence au démarrage. Affiche une fenêtre si activation requise."""
    try:
        import license_manager
        status = license_manager.check_license_or_trial()
    except Exception as e:
        print(f"[Licence] Avertissement vérification : {e}")
        return True  # Continuer si le module est absent (dev mode)

    mid = ''
    try:
        import license_manager as _lm
        mid = _lm.get_machine_id()
    except Exception:
        pass

    if status.get('valid'):
        # Licence valide OU essai encore actif
        if status.get('trial'):
            days_left = status.get('days_left', 0)
            if days_left <= 7:
                print(f"  [ESSAI] Il vous reste {days_left} jour(s) d'essai.")
                print(f"  [ESSAI] Contactez GS Hadja Kanfing Dian pour acheter une licence.")
                show_activation_window(mid, trial_days_left=days_left)
            else:
                from datetime import datetime, timedelta
                exp = (datetime.utcnow() + timedelta(days=days_left)).strftime('%d/%m/%Y')
                print(f"  [ESSAI GRATUIT] {days_left} jour(s) restant(s) — expire le {exp}")
                print(f"  [ESSAI GRATUIT] Contactez GS Hadja Kanfing Dian pour obtenir une licence.")
        else:
            school = status.get('school', '')
            edition = status.get('edition', 'Standard')
            days_left = status.get('days_left', 0)
            if days_left <= 30:
                print(f"  [Licence] Expire dans {days_left} jour(s). "
                      f"Renouvelez auprès de GS Hadja Kanfing Dian.")
            else:
                print(f"  [Licence] Valide — {school} ({edition}) — {days_left}j restant(s).")
    else:
        # Essai expiré ou aucune licence → fenêtre bloquante (pas de bouton "Continuer")
        days_left = status.get('days_left', 0)
        print("")
        print("  [Licence] Activation requise — ouverture de la fenêtre d'activation...")
        can_start = show_activation_window(mid, trial_days_left=days_left)
        if not can_start:
            os._exit(0)   # Fermeture totale sans laisser Django démarrer

    return True


# ─── Utilitaires ──────────────────────────────────────────────────────────────
def find_free_port(start_port=8000, max_port=8100):
    """Trouve un port libre disponible."""
    for port in range(start_port, max_port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('127.0.0.1', port))
                return port
        except OSError:
            continue
    return start_port


def setup_database():
    """Initialise / migre la base de données SQLite."""
    import django
    django.setup()
    from django.core.management import call_command

    db_path = os.path.join(BASE_DIR, 'db.sqlite3')
    is_new_db = not os.path.exists(db_path) or os.path.getsize(db_path) == 0

    print("[MySchoolGN] Migration de la base de données...")
    call_command('migrate', '--run-syncdb', verbosity=0)

    if is_new_db:
        print("[MySchoolGN] Nouvelle installation détectée.")
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if not User.objects.filter(username='admin').exists():
                User.objects.create_superuser(
                    username='admin',
                    password='admin1234',
                    email='admin@myschool.local'
                )
                print("[MySchoolGN] Compte admin créé : admin / admin1234")
        except Exception as e:
            print(f"[MySchoolGN] Avertissement création admin : {e}")

    print("[MySchoolGN] Préparation des fichiers statiques...")
    try:
        call_command('collectstatic', '--noinput', verbosity=0)
    except Exception:
        pass


def open_browser(port):
    """Ouvre le navigateur après un délai."""
    time.sleep(2.5)
    url = f'http://127.0.0.1:{port}'
    print(f"[MySchoolGN] Navigateur → {url}")
    webbrowser.open(url)


def show_banner(port, license_status=None):
    """Affiche la bannière de démarrage."""
    school = ''
    edition = 'Standard'
    mode_label = 'Mode Essai'
    if license_status:
        if not license_status.get('trial'):
            school = license_status.get('school', '')
            edition = license_status.get('edition', 'Standard')
            mode_label = f'Édition {edition}'
        else:
            days_left = license_status.get('days_left', 0)
            mode_label = f'Essai — {days_left}j restant(s)'

    print("")
    print("=" * 60)
    print("   MySchoolGN - Système de Gestion Scolaire")
    print(f"   {mode_label}")
    if school:
        print(f"   {school}")
    print("=" * 60)
    print("")
    print(f"   Adresse : http://127.0.0.1:{port}")
    print(f"   Admin   : http://127.0.0.1:{port}/admin/")
    print("")
    print("   Identifiants par défaut :")
    print("     Utilisateur : admin")
    print("     Mot de passe: admin1234")
    print("")
    print("   Appuyez sur Ctrl+C pour arrêter le serveur")
    print("=" * 60)
    print("")


# ─── Point d'entrée principal ──────────────────────────────────────────────────
def main():
    """Point d'entrée principal."""
    print("")
    print("*" * 60)
    print("   MySchoolGN — GS Hadja Kanfing Dian")
    print("   Démarrage en mode offline...")
    print("*" * 60)
    print(f"   Répertoire : {BASE_DIR}")

    # Vérification de la licence
    license_status = None
    try:
        import license_manager
        license_status = license_manager.check_license_or_trial()
    except Exception:
        pass
    check_license()

    # Créer les dossiers nécessaires
    for folder in ['logs', 'media', 'staticfiles',
                   'media/photos_eleves', 'media/logos_ecoles']:
        folder_path = os.path.join(BASE_DIR, folder)
        os.makedirs(folder_path, exist_ok=True)

    # Trouver un port libre
    port = find_free_port()

    # Initialiser la base de données
    try:
        setup_database()
    except Exception as e:
        print(f"[MySchoolGN] Erreur initialisation : {e}")
        print("[MySchoolGN] Tentative de démarrage sans migration...")

    # Afficher la bannière
    show_banner(port, license_status)

    # Ouvrir le navigateur en arrière-plan
    browser_thread = threading.Thread(
        target=open_browser, args=(port,), daemon=True
    )
    browser_thread.start()

    # Lancer le serveur Django
    try:
        import django
        django.setup()
        from django.core.management import call_command
        call_command('runserver', f'127.0.0.1:{port}', '--noreload')
    except KeyboardInterrupt:
        print("\n[MySchoolGN] Arrêt du serveur...")
        print("[MySchoolGN] Au revoir !")
    except Exception as e:
        print(f"\n[MySchoolGN] Erreur : {e}")
        input("Appuyez sur Entrée pour fermer...")


if __name__ == '__main__':
    _log_path = os.path.join(BASE_DIR, 'startup_error.log')
    try:
        main()
    except SystemExit:
        raise
    except Exception as _crash:
        _msg = (
            f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"CRASH AU DÉMARRAGE\n"
            f"{traceback.format_exc()}\n"
        )
        try:
            with open(_log_path, 'a', encoding='utf-8') as _f:
                _f.write(_msg)
        except Exception:
            pass
        print(_msg)
        input("ERREUR — Appuyez sur Entrée pour fermer...")
