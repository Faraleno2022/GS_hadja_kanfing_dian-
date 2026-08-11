from django.apps import AppConfig


class AdministrationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'administration'
    verbose_name = 'Administration'
    
    def ready(self):
        import administration.signals
        import administration.audit_signals  # corbeille mémoire des modifications
