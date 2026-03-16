from django.db import models
from users.models import User
from mbr.models import Document, Product, Parameter, MBR


class EBRStatus(models.Model):
    STATUS_CHOICES = [('В работе', 'В работе'), ('Завершена', 'Завершена'), ('Заблокирована', 'Заблокирована')]
    status_name = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Статус')

    class Meta:
        db_table = 'EBR_Status'
        verbose_name = 'Статус EBR'
        verbose_name_plural = 'Статусы EBR'

    def __str__(self):
        return self.status_name


class EBR(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, primary_key=True)
    batch_number = models.CharField(max_length=50, unique=True, verbose_name='Номер партии')
    status = models.ForeignKey(EBRStatus, on_delete=models.CASCADE, verbose_name='Статус')
    mbr = models.ForeignKey(MBR, on_delete=models.CASCADE, verbose_name='Исходный MBR')
    start_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата начала')
    completion_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата завершения')
    inspection_notes = models.TextField(blank=True, null=True, verbose_name='Результаты контроля')
    comments = models.TextField(blank=True, null=True, verbose_name='Комментарии')
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Подписал',
                                  related_name='signed_ebr')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Оператор',
                                 related_name='operator_ebr')

    class Meta:
        db_table = 'EBR'
        verbose_name = 'EBR'
        verbose_name_plural = 'EBR'

    def __str__(self):
        return self.batch_number


class EBRParameter(models.Model):
    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    actual_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       verbose_name='Фактическое значение')

    class Meta:
        db_table = 'EBR_Parameters'
        unique_together = ['ebr', 'parameter']
        verbose_name = 'Параметр EBR'
        verbose_name_plural = 'Параметры EBR'


class BatchOperation(models.Model):
    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE, related_name='operations')
    operation_name = models.CharField(max_length=100, verbose_name='Операция')
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Ожидает'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершена'),
        ('blocked', 'Заблокирована')
    ], verbose_name='Статус')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    operator_comment = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'Batch_Operation'
        verbose_name = 'Операция партии'
        verbose_name_plural = 'Операции партии'