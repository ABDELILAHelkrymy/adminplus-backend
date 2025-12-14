from django.apps import AppConfig


class BankStatementsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bank_statements'
    verbose_name = 'Bank Statements'

    def ready(self):
        import apps.bank_statements.signals
