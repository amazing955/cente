from django.db import models
import uuid
from django.conf import settings


class ReportLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    generated_at = models.DateTimeField(auto_now_add=True)
    filters = models.JSONField(default=dict, blank=True)

    class Meta:
        verbose_name = 'Report Log'
        verbose_name_plural = 'Report Logs'

    def __str__(self):
        return f"{self.name} @ {self.generated_at:%Y-%m-%d %H:%M}"
