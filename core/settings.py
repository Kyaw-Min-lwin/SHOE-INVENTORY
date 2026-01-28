"""
Django settings for core project.
"""

from pathlib import Path
import os
from django.urls import reverse_lazy
import cloudinary
import cloudinary_storage

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# --- SECURITY: Load secrets from Environment or .env file ---
# (Make sure you created the .env file I mentioned in the last step!)
SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-fallback-key-for-dev-only")

DEBUG = True

ALLOWED_HOSTS = ["*"]


# Application definition

INSTALLED_APPS = [
    "unfold",  # <--- MUST be before admin
    "django.contrib.admin",  # <--- Standard admin
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "unfold.contrib.filters",
    "cloudinary_storage",
    "cloudinary",
    "store",  # <--- Your App
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # Point to root templates folder
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",  # Required by Unfold
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# --- CLOUDINARY CONFIGURATION ---
CLOUDINARY_STORAGE = {
    "CLOUD_NAME": os.environ.get("CLOUDINARY_CLOUD_NAME", "dxtwewfqm"),
    "API_KEY": os.environ.get("CLOUDINARY_API_KEY", "954413273429273"),
    "API_SECRET": os.environ.get(
        "CLOUDINARY_API_SECRET", "oJcinIyq2YDUyEi1SxMs4UtjHQc"
    ),
}

cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dxtwewfqm"),
    api_key=os.environ.get("CLOUDINARY_API_KEY", "954413273429273"),
    api_secret=os.environ.get(
        "CLOUDINARY_API_SECRET", "oJcinIyq2YDUyEi1SxMs4UtjHQc"
    ),
    secure=True,
)
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"


# --- STATIC FILES ---
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"


# --- UNFOLD ADMIN THEME SETTINGS ---
UNFOLD = {
    "SITE_TITLE": "Latli Boutique",
    "SITE_HEADER": "Inventory Admin",
    "SITE_URL": "/admin/",
    "DASHBOARD_CALLBACK": "store.dashboard.dashboard_callback",
    "COLORS": {
        "primary": {
            "50": "250 245 230",
            "100": "245 235 200",
            "200": "235 215 150",
            "300": "225 195 100",
            "400": "215 175 50",
            "500": "201 162 39",
            "600": "180 140 30",
            "700": "150 110 20",
            "800": "120 90 15",
            "900": "90 70 10",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": "Inventory Management",
                "separator": True,
                "items": [
                    {
                        "title": "All Products",
                        "icon": "inventory_2",
                        "link": reverse_lazy("admin:store_product_changelist"),
                    },
                    {
                        "title": "Restock Batches",
                        "icon": "local_shipping",
                        "link": reverse_lazy("admin:store_restockbatch_changelist"),
                    },
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": reverse_lazy("admin:store_category_changelist"),
                    },
                ],
            },
            {
                "title": "Sales & CRM",
                "separator": True,
                "items": [
                    {
                        "title": "New Sale (POS)",
                        "icon": "point_of_sale",
                        "link": reverse_lazy("admin:store_sale_add"),
                    },
                    {
                        "title": "Sales Receipts",
                        "icon": "receipt_long",
                        "link": reverse_lazy("admin:store_sale_changelist"),
                    },
                    {
                        "title": "Customers",
                        "icon": "groups",
                        "link": reverse_lazy("admin:store_customer_changelist"),
                    },
                    {
                        "title": "Staff Members",
                        "icon": "badge",
                        "link": reverse_lazy("admin:store_staff_changelist"),
                    },
                ],
            },
        ],
    },
}
