import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-your-secret-key-here'
DEBUG = True
ALLOWED_HOSTS = ['*']

# Подключаем наши приложения
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'users',
    'mbr',
    'ebr',
    'quality',
    'audit',
    'reports',
    'equipment',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'users.middleware.AuthMiddleware',
]

ROOT_URLCONF = 'pharma_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# Подключение к PostgreSQL
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'pharma_db',
        'USER': 'postgres',
        'PASSWORD': 'pharma',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'pharma_db',
#         'USER': 'pharma_user',
#         'PASSWORD': 'pharma_pass',
#         'HOST': 'localhost',
#         'PORT': '5432',
#     }
# }


# Настройки статики
STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Настройки медиа
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Для шаблонов
import mimetypes
mimetypes.add_type("text/css", ".css", True)

# Кастомная модель пользователя
AUTH_USER_MODEL = 'users.User'

# Отключаем стандартную аутентификацию Django
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # оставляем для админки
]

# Для админки
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'

LANGUAGE_CODE = 'ru-ru'

USE_I18N = True

USE_TZ = True
