from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
# SECRET_KEY turi būti nustatytas kaip environment variable
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-n@(+@z8l%3hj7_^p2lf%r3q^!i&$afmrj2(u-yeq-8#+jwp^kk')
CHAT_ENCRYPTION_KEY = os.environ.get('CHAT_ENCRYPTION_KEY', 'L9mLt5bbNxNS_yaaQv2eiIGdyNInG9vAfI9_sDBfwFA=')

# SECURITY WARNING: don't run with debug turned on in production!
# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False') == 'True' 

# SECURITY: ribojame tik leidžiamus host'us (pašalintas '*')
ALLOWED_HOSTS = ['nomoklis.lt', 'www.nomoklis.lt', 'localhost', '127.0.0.1']

CSRF_TRUSTED_ORIGINS = ['http://127.0.0.1', 'http://localhost', 'https://nomoklis.lt', 'https://www.nomoklis.lt']


# Application definition
INSTALLED_APPS = [
    'daphne',  # Turi būti pirmoje vietoje
    'channels',
    "django.contrib.admin",  # Admin po daphne ir channels
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "nomoklis_app",
    "widget_tweaks",
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    # Security apps
    'axes',  # Rate limiting / brute force protection
    # 'csp',   # Content Security Policy (Laikinai išjungta)
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    # Security middleware
    'axes.middleware.AxesMiddleware',  # Rate limiting (turi būti po AuthenticationMiddleware)
    # 'csp.middleware.CSPMiddleware',    # Content Security Policy (Laikinai išjungta)
]

STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}

ROOT_URLCONF = "Nomoklis.urls"
WSGI_APPLICATION = "Nomoklis.wsgi.application"
ASGI_APPLICATION = 'Nomoklis.asgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True, # ŠI EILUTĖ TURI BŪTI True
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Pridedame savo context procesorių
                'nomoklis_app.context_processors.unread_messages_count',
            ],
        },
    },
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.environ.get('DATABASE_NAME'),
        'USER': os.environ.get('DATABASE_USER'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD'),
        'HOST': os.environ.get('DATABASE_SERVER'),
        'PORT': '3306',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "lt"
TIME_ZONE = "UTC"
USE_I18N = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]

USE_TZ = True

# Static and Media files
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50 MB

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            # Pakeičiame '127.0.0.1' į 'redis'
            "hosts": [("redis", 6379)],
        },
    },
}

# Stripe Keys
STRIPE_PUBLISHABLE_KEY= os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_SECRET_KEY= os.environ.get('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET= os.environ.get('STRIPE_WEBHOOK_SECRET')

# --- Allauth and Authentication Settings ---
SITE_ID = 1

LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/'

# Allauth specific settings
ACCOUNT_ADAPTER = 'nomoklis_app.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'nomoklis_app.adapters.MySocialAccountAdapter'
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ["username", "email", "first_name", "last_name", "password1"]
# SECURITY: Email verification įjungta production'e
ACCOUNT_EMAIL_VERIFICATION = os.environ.get('EMAIL_VERIFICATION', 'optional')  # 'mandatory' production'e
SOCIALACCOUNT_AUTO_SIGNUP = True
ACCOUNT_LOGOUT_ON_GET = True
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_QUERY_EMAIL = True
SOCIALACCOUNT_EMAIL_VERIFICATION = os.environ.get('EMAIL_VERIFICATION', 'optional') 

# Google provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

ACCOUNT_FORMS = {
    'signup': 'nomoklis_app.forms.CustomSignupForm',
}

# --- Slaptažodžio atstatymo ir el. pašto nustatymai ---
# Plėtros metu laiškai spausdinami konsolėje.
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.hostinger.com'  # Pvz., 'smtp.serveriai.lt'
EMAIL_PORT = 587  # Dažniausiai naudojamas prievadas su TLS
EMAIL_USE_TLS = True  # Naudoti TLS šifravimą

EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')

DEFAULT_FROM_EMAIL = 'info@nomoklis.lt'
SERVER_EMAIL = 'info@nomoklis.lt'

# Nurodome allauth, kokius šablonus naudoti laiškams
ACCOUNT_EMAIL_SUBJECT_PREFIX = '' # Išjungiame standartinį "[example.com]" priedėlį

# --- HTTPS ir Session Security Nustatymai ---
# Šie nustatymai aktyvuojami tik production aplinkoje (kai DEBUG=False)
if not DEBUG:
    # HTTPS nustatymai
    SECURE_SSL_REDIRECT = True  # Automatiškai nukreipia HTTP -> HTTPS
    SESSION_COOKIE_SECURE = True  # Session cookies tik per HTTPS
    CSRF_COOKIE_SECURE = True  # CSRF cookies tik per HTTPS
    
    # HTTP Strict Transport Security (HSTS)
    SECURE_HSTS_SECONDS = 31536000  # 1 metai
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    
    # Security headers
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    X_FRAME_OPTIONS = 'DENY'

# Session security (visada aktyvus)
SESSION_COOKIE_HTTPONLY = True  # Apsaugo nuo XSS atakų
SESSION_COOKIE_SAMESITE = 'Lax'  # Apsaugo nuo CSRF
SESSION_COOKIE_AGE = 1209600  # 2 savaitės
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Lax'

# --- Django Axes (Rate Limiting) Nustatymai ---
AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesStandaloneBackend',  # Axes turi būti pirmas
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

# Axes konfigūracija
AXES_FAILURE_LIMIT = 5  # Maksimalus bandymų skaičius
AXES_COOLOFF_TIME = 1  # Blokavimo trukmė valandomis
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True  # Blokuoti pagal IP + username
AXES_RESET_ON_SUCCESS = True  # Atstatyti bandymus po sėkmingo prisijungimo
AXES_LOCKOUT_TEMPLATE = None  # Naudoti default error message
AXES_VERBOSE = True  # Detalūs logai

# --- Content Security Policy (CSP) Nustatymai ---
# LAIKINAI IŠJUNGTA - sukelia rendering problemas
# Leidžiame tik saugius šaltinius
# CSP_DEFAULT_SRC = ("'self'",)
# CSP_SCRIPT_SRC = ("'self'", "https://cdn.tailwindcss.com", "https://unpkg.com", "https://cdn.jsdelivr.net", "'unsafe-inline'")
# CSP_STYLE_SRC = ("'self'", "https://fonts.googleapis.com", "https://cdn.tailwindcss.com", "'unsafe-inline'")
# CSP_FONT_SRC = ("'self'", "https://fonts.gstatic.com")
# CSP_IMG_SRC = ("'self'", "data:", "https:", "http:")  # Leidžiame images iš bet kur (CDN ir t.t.)
# CSP_CONNECT_SRC = ("'self'", "wss:", "ws:")  # WebSocket palaikymui
# CSP_FRAME_ANCESTORS = ("'none'",)  # Neleidžiame iframe