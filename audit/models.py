from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from accounts.models import User


class Action(models.Model):
    action_name = models.CharField(max_length=100, unique=True, verbose_name='Название действия')

    class Meta:
        verbose_name = 'Действие'
        verbose_name_plural = 'Действия'

    def __str__(self):
        return self.action_name


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    action = models.ForeignKey(Action, on_delete=models.CASCADE, verbose_name='Действие')
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Дата и время')
    comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    ip_address = models.GenericIPAddressField(blank=True, null=True, verbose_name='IP адрес')

    class Meta:
        verbose_name = 'Аудит'
        verbose_name_plural = 'Аудит'
        ordering = ['-timestamp']
        # ТЗ 4.2.6.1.2 - запрет на модификацию и удаление
        permissions = [
            ('view_auditlog', 'Может просматривать журнал аудита'),
        ]

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"

    def save(self, *args, **kwargs):
        # Запрет на редактирование существующих записей
        if self.pk:
            raise ValueError('Записи аудита нельзя изменять')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Запрет на удаление записей аудита
        raise ValueError('Записи аудита нельзя удалять')