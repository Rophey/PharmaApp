from django.db import models
from users.models import User
from ebr.models import EBR


class QCTask(models.Model):
    TASK_TYPES = [
        ('sampling', 'Отбор проб'),
        ('testing', 'Лабораторные испытания'),
        ('review', 'Проверка')
    ]
    STATUS_CHOICES = [
        ('new', 'Новое'),
        ('in_progress', 'В работе'),
        ('completed', 'Выполнено'),
        ('rejected', 'Отклонено')
    ]

    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE, verbose_name='Партия')
    task_type = models.CharField(max_length=20, choices=TASK_TYPES, verbose_name='Тип задания')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', verbose_name='Статус')
    assigned_to = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Назначено', related_name='qc_tasks')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создал', related_name='created_tasks')
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateTimeField(verbose_name='Срок выполнения')
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'QC_Task'
        verbose_name = 'Задание ОКК'
        verbose_name_plural = 'Задания ОКК'


class QCResult(models.Model):
    task = models.OneToOneField(QCTask, on_delete=models.CASCADE, verbose_name='Задание')
    visual_control = models.TextField(verbose_name='Визуальный контроль')
    lab_results = models.TextField(verbose_name='Лабораторные результаты')
    files = models.FileField(upload_to='qc_files/', null=True, blank=True, verbose_name='Прикреплённые файлы')
    comments = models.TextField(blank=True, null=True, verbose_name='Комментарий')
    submitted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Предоставил')
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'QC_Result'
        verbose_name = 'Результат ОКК'
        verbose_name_plural = 'Результаты ОКК'


class Deviation(models.Model):
    DEVIATION_TYPES = [
        ('warning', 'Предупреждение'),
        ('deviation', 'Отклонение'),
        ('critical', 'Критическое отклонение')
    ]
    ACTIONS = [
        ('block', 'Заблокировать партию'),
        ('rework', 'Направить на доработку'),
        ('accept', 'Принять с замечаниями'),
        ('reject', 'Отклонить партию')
    ]

    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE, verbose_name='Партия')
    deviation_type = models.CharField(max_length=20, choices=DEVIATION_TYPES, verbose_name='Тип отклонения')
    parameter_name = models.CharField(max_length=100, verbose_name='Параметр')
    expected_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Ожидаемое значение')
    actual_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Фактическое значение')
    tolerance = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Допуск')
    description = models.TextField(verbose_name='Описание')
    detected_at = models.DateTimeField(auto_now_add=True)
    detected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Обнаружил')
    action_taken = models.CharField(max_length=50, choices=ACTIONS, null=True, blank=True,
                                    verbose_name='Принятое действие')
    action_comment = models.TextField(blank=True, null=True, verbose_name='Комментарий к действию')
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Решил',
                                    related_name='resolved_deviations')
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'Deviation'
        verbose_name = 'Отклонение'
        verbose_name_plural = 'Отклонения'