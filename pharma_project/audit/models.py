from django.db import models
from users.models import User
from mbr.models import Document


class Action(models.Model):
    action_name = models.CharField(max_length=100, verbose_name='Действие')

    class Meta:
        db_table = 'Action'
        verbose_name = 'Действие'
        verbose_name_plural = 'Действия'

    def __str__(self):
        return self.action_name


class AuditLog(models.Model):
    audit_id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    action = models.ForeignKey(Action, on_delete=models.CASCADE, verbose_name='Действие')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, null=True, blank=True,
                                 verbose_name='Документ')  # Должно быть null=True
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name='IP-адрес')

    class Meta:
        db_table = 'Audit_Log'
        verbose_name = 'Запись аудита'
        verbose_name_plural = 'Журнал аудита'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action}"


class ElectronicSignature(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    document = models.ForeignKey(Document, on_delete=models.CASCADE, verbose_name='Документ')
    signature_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата подписи')
    signature_hash = models.CharField(max_length=255, verbose_name='Хэш подписи')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')

    class Meta:
        db_table = 'Electronic_Signature'
        verbose_name = 'Электронная подпись'
        verbose_name_plural = 'Электронные подписи'