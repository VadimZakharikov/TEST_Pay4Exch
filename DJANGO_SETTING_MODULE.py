DEBUG = False

ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    '111.222.333.444',
]

INSTALLED_APPS = [
]

MIDDLEWARE = [
    # Другие промежуточные слои...
]

TEMPLATES = [
]

DATABASES = {
    # Ваши настройки базы данных...
}

WSGI_APPLICATION = 'wsgi.application'

FORCE_SCRIPT_NAME = None

ROOT_URLCONF = 'urls'  # Укажите корректный путь к вашему файлу urls.py

# Настройки для бота Telegram
DJANGO_TELEGRAMBOT = {
    'MODE': 'WEBHOOK',  # или 'POLLING'
    'WEBHOOK_PREFIX': None,
    'WEBHOOK_PORT': 443,  # Порт, на котором работает ваш бот
    'WEBHOOK_SSL_CERT': 'cert.pem',
    'WEBHOOK_SSL_PRIV': 'key.pem',
    'WEBHOOK_MAX_CONNECTIONS': 40,  # Максимальное количество одновременных соединений
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

LOGGING_CONFIG = None  # Это строка из вашего примера, оставьте ее так

DEBUG_PROPAGATE_EXCEPTIONS = True
TASTYPIE_FULL_DEBUG = True

CSRF_USE_SESSIONS = False
CSRF_COOKIE_NAME = "TEST"
DEFAULT_CHARSET="utf-8"

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.memcached.MemcachedCache',
        'LOCATION': '127.0.0.1:8000',
    }
}
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024