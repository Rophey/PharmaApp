from django.db import models
from ebr.models import EBR
from accounts.models import User


class QualityTask(models.Model):
    TASK_TYPES = [
        ('sampling', 'Отбор проб'),
        ('lab_test', 'Лабораторные испытания'),
        ('visual_check', 'Визуальный контроль'),
    ]

    STATUS_CHOICES = [
        ('new', 'Новое'),
        ('in_progress', 'В выполнении'),
        ('completed', 'Выполнено'),
    ]

    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE, verbose_name='Партия', related_name='quality_tasks')
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, verbose_name='Тип задания')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Исполнитель',
                                    limit_choices_to={'role': 'qc_specialist'})
    deadline = models.DateTimeField(verbose_name='Срок выполнения')
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата выполнения')
    result_data = models.TextField(blank=True, null=True, verbose_name='Результаты')
    attached_files = models.FileField(upload_to='quality_files/', blank=True, null=True,
                                      verbose_name='Прикреплённые файлы')

    class Meta:
        verbose_name = 'Задание ОКК'
        verbose_name_plural = 'Задания ОКК'

    def __str__(self):
        return f"{self.get_task_type_display()} - {self.ebr.batch_number}"


class Alert(models.Model):
    ALERT_LEVELS = [
        ('warning', 'Предупреждение'),
        ('deviation', 'Отклонение'),
        ('critical', 'Критическое отклонение'),
    ]

    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE, verbose_name='Партия', related_name='alerts')
    level = models.CharField(max_length=20, choices=ALERT_LEVELS, verbose_name='Уровень')
    parameter_name = models.CharField(max_length=100, verbose_name='Параметр')
    actual_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Фактическое значение')
    expected_range = models.CharField(max_length=100, verbose_name='Допустимый диапазон')
    detected_at = models.DateTimeField(auto_now_add=True, verbose_name='Время обнаружения')
    resolved = models.BooleanField(default=False, verbose_name='Устранено')
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                    verbose_name='Устранил', related_name='resolved_alerts')
    resolution_comment = models.TextField(blank=True, null=True, verbose_name='Комментарий')

    class Meta:
        verbose_name = 'Оповещение'
        verbose_name_plural = 'Оповещения'
        ordering = ['-detected_at']

    def __str__(self):
        return f"{self.get_level_display()} - {self.parameter_name}"