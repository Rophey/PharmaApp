from django.db import models
from accounts.models import User
from mbr.models import MBR, Parameter


class EBRStatus(models.Model):
    status_name = models.CharField(max_length=20, choices=[
        ('in_progress', 'В работе'),
        ('completed', 'Завершена'),
        ('blocked', 'Заблокирована'),
    ], verbose_name='Статус')

    class Meta:
        verbose_name = 'Статус EBR'
        verbose_name_plural = 'Статусы EBR'

    def __str__(self):
        return self.status_name


class EBR(models.Model):
    mbr = models.ForeignKey(MBR, on_delete=models.CASCADE, verbose_name='MBR')
    batch_number = models.CharField(max_length=50, unique=True, verbose_name='Номер партии')
    status = models.ForeignKey(EBRStatus, on_delete=models.CASCADE, verbose_name='Статус')
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата начала')
    completion_date = models.DateTimeField(blank=True, null=True, verbose_name='Дата завершения')
    inspection_notes = models.TextField(blank=True, null=True,
                                        verbose_name='Визуальный контроль и лабораторные испытания')
    comments = models.TextField(blank=True, null=True, verbose_name='Комментарии')
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                  verbose_name='Подписал', related_name='signed_ebrs')
    actual_parameters = models.ManyToManyField(Parameter, related_name='ebr_parameters',
                                               verbose_name='Фактические параметры')

    class Meta:
        verbose_name = 'EBR (Паспорт партии)'
        verbose_name_plural = 'EBR (Паспорта партий)'

    def __str__(self):
        return f"Партия {self.batch_number}"

    def generate_batch_number(self):
        from datetime import datetime
        last_ebr = EBR.objects.all().order_by('-id').first()
        if last_ebr:
            last_number = int(last_ebr.batch_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        year = datetime.now().year
        self.batch_number = f"B-{year}-{new_number:03d}"