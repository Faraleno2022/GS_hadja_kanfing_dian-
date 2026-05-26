from django.apps import AppConfig


class SynchronisationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'synchronisation'
    verbose_name = 'Synchronisation offline/online'
