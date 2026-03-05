"""
Django settings for ecole_moderne project.
"""

from pathlib import Path
import os
try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

# =================== Base ===================
BASE_DIR = Path(__file__).resolve().parent.parent

# Charger .env si disponible
if load_dotenv:
    load_dotenv(BASE_DIR / ".env")

# =================== Clés et debug ===================
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'dev-unsafe-key')
DEBUG = os.environ.get('DJANGO_DEBUG', 'true').lower() == 'true'

# =================== Hôtes et CSRF ===================
if DEBUG:
    ALLOWED_HOSTS = ['*']  # Accepter tous les hôtes en développement
    CSRF_TRUSTED_ORIGINS = [
        'http://127.0.0.1:8000',
        'http://127.0.0.1:8001',
        'http://localhost:8000',
        'http://localhost:8001',
        'http://127.0.0.1:50148',
        'http://localhost:50148',
        'https://127.0.0.1:8000',
        'https://127.0.0.1:8001',
        'https://localhost:8000',
        'https://localhost:8001',
        'https://myschoolgn.space',
        'https://www.myschoolgn.space',
    ]
else:
    ALLOWED_HOSTS = [
        'gshadjakanfingdiane.pythonanywhere.com',
        'myschoolgn.space',
        'www.myschoolgn.space',
    ]
    CSRF_TRUSTED_ORIGINS = [
        'https://gshadjakanfingdiane.pythonanywhere.com',
        'https://myschoolgn.space',
        'https://www.myschoolgn.space',
    ]

# =================== Sécurité ===================
# Désactivé pour développement local
if DEBUG:
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_SECURE = False
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False
    SECURE_CONTENT_TYPE_NOSNIFF = False
    SECURE_BROWSER_XSS_FILTER = False
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    SECURE_REFERRER_POLICY = 'no-referrer-when-downgrade'
    
    CSRF_COOKIE_HTTPONLY = False
    SESSION_COOKIE_HTTPONLY = False
    SESSION_COOKIE_SAMESITE = 'Lax'
    CSRF_COOKIE_SAMESITE = 'Lax'
    SESSION_EXPIRE_AT_BROWSER_CLOSE = False
    
    SECURE_PROXY_SSL_HEADER = None
    USE_X_FORWARDED_HOST = False
else:
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'
    SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'
    
    CSRF_COOKIE_HTTPONLY = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Strict'
    CSRF_COOKIE_SAMESITE = 'Strict'
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True
    
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True

# =================== Applications ===================
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',

    # Applications de gestion scolaire
    'eleves',
    'paiements',
    'depenses',
    'salaires',
    'utilisateurs',
    'rapports',
    'administration',
    'bus',
    'notes',
    'abonnements',
    'chatbot',
]

# =================== Middleware ===================
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# Ajouter middlewares d’optimisation images
if DEBUG:
    MIDDLEWARE += [
        'ecole_moderne.image_cache_middleware.ImageCacheMiddleware',
        'ecole_moderne.image_optimization_middleware.ImageOptimizationMiddleware',
    ]
else:
    MIDDLEWARE.append('ecole_moderne.image_optimization_middleware.ImageOptimizationMiddleware')
    MIDDLEWARE.insert(1, 'ecole_moderne.security_middleware.SecurityMiddleware')
    MIDDLEWARE.insert(3, 'ecole_moderne.security_middleware.SessionSecurityMiddleware')
    MIDDLEWARE.insert(5, 'ecole_moderne.security_middleware.CSRFSecurityMiddleware')
    MIDDLEWARE.append('ecole_moderne.security_middleware.CSPMiddleware')

ROOT_URLCONF = 'ecole_moderne.urls'

# =================== Templates ===================
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'utilisateurs.context_processors.user_context',
            ],
        },
    },
]

WSGI_APPLICATION = 'ecole_moderne.wsgi.application'

# =================== Base de données ===================

if DEBUG:
    # Utiliser SQLite en développement local
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
else:
    # Utiliser MySQL sur PythonAnywhere en production
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": "myschoolgn$myschooldb",
            "USER": "myschoolgn",
            "PASSWORD": "Felixsuzaneleno1994@",
            "HOST": "myschoolgn.mysql.pythonanywhere-services.com",
            "PORT": "3306",
            "OPTIONS": {
                "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
                "charset": "utf8mb4",
            },
            "CONN_MAX_AGE": 60,
        }
    }

# =================== Auth & mots de passe ===================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 12}},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LOGIN_URL = '/utilisateurs/login/'
LOGIN_REDIRECT_URL = '/eleves/'
LOGOUT_REDIRECT_URL = '/utilisateurs/login/'

# =================== Internationalisation ===================
LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Conakry'
USE_I18N = True
USE_TZ = True

USE_THOUSAND_SEPARATOR = False
THOUSAND_SEPARATOR = ' '
NUMBER_GROUPING = 3
DEFAULT_CURRENCY = 'GNF'
DEFAULT_COUNTRY_CODE = '+224'

# =================== Static & Media ===================
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

if DEBUG:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
else:
    STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'

# =================== Logging ===================
LOGS_DIR = BASE_DIR / 'logs'
os.makedirs(LOGS_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'}},
    'handlers': {
        'file': {'level': 'INFO', 'class': 'logging.FileHandler', 'filename': LOGS_DIR / 'django.log', 'formatter': 'verbose'},
        'console': {'class': 'logging.StreamHandler', 'formatter': 'verbose'},
    },
    'root': {'handlers': ['console', 'file'], 'level': 'INFO'},
}

# =================== Uploads ===================
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880
DATA_UPLOAD_MAX_NUMBER_FIELDS = 5000

# =================== Intégrations externes ===================
TWILIO_ENABLED = os.getenv("TWILIO_ENABLED", "false").lower() in {"1", "true", "yes"}
PHONE_VERIFY_TTL_SECONDS = int(os.environ.get('PHONE_VERIFY_TTL_SECONDS', 4 * 3600))

# =================== Configuration IA Chatbot ===================
# Token HuggingFace pour l'API IA (obtenir sur https://huggingface.co/settings/tokens)
HF_TOKEN = os.environ.get('HF_TOKEN', '')
# Modèle à utiliser (DeepSeek via HuggingFace Router)
HF_MODEL = os.environ.get('HF_MODEL', 'deepseek-ai/DeepSeek-R1')

# =================== Paramètres de sécurité ===================
BLOCK_SUPERUSER_PUBLIC_LOGIN = os.environ.get('BLOCK_SUPERUSER_PUBLIC_LOGIN', 'true').lower() == 'true'
ADMIN_WHITELIST_IPS = [ip.strip() for ip in os.environ.get('ADMIN_WHITELIST_IPS', '').split(',') if ip.strip()]
MAX_CONNECTIONS_PER_IP = 10
IP_BLOCK_DURATION = 86400
MAX_LOGIN_ATTEMPTS = 5
LOGIN_BLOCK_DURATION = 300
