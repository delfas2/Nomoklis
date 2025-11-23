from django.apps import AppConfig


class NomoklisAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "nomoklis_app"

    def ready(self):
        import nomoklis_app.signals
