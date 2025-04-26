from django.apps import AppConfig


class InvoicesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.invoices'
    verbose_name = 'Invoice Management'
    
    def ready(self):
        # Import any signal handlers
        pass
