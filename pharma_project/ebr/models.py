from django.db import models
from users.models import User
from mbr.models import Document, Product, Parameter, MBR


class EBRStatus(models.Model):
    STATUS_CHOICES = [
        ('В ожидании', 'В ожидании'),
        ('В работе', 'В работе'),
        ('Завершена', 'Завершена'),
        ('Заблокирована', 'Заблокирована'),
    ]
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
    # Для отслеживания работы пресса
    pressing_start_time = models.DateTimeField(null=True, blank=True, verbose_name='Начало прессования')
    pressing_duration = models.IntegerField(null=True, blank=True, verbose_name='Длительность прессования (сек)')

    class Meta:
        db_table = 'EBR'
        verbose_name = 'EBR'
        verbose_name_plural = 'EBR'

    def __str__(self):
        return self.batch_number

    @property
    def current_operation_label(self):
        """Возвращает текстовое описание текущего этапа для отображения."""
        if self.status.status_name == 'В ожидании':
            return 'Ожидание оператора'
        if self.status.status_name == 'Завершена':
            return 'Партия завершена'
        if self.status.status_name == 'Заблокирована':
            return 'Партия заблокирована'

        # Проверяем, работает ли ещё пресс (по времени)
        if self.pressing_start_time and self.pressing_duration:
            from django.utils import timezone
            now = timezone.now()
            elapsed = (now - self.pressing_start_time).total_seconds()
            if elapsed < self.pressing_duration:
                return 'Пресс запущен'
            # Пресс отработал своё время → ОКК
            return 'Экспертиза в ОКК'

        # Проверяем операции
        ops = list(self.operations.order_by('id'))
        if ops:
            in_progress = [op for op in ops if op.status == 'in_progress']
            if in_progress:
                op_name = in_progress[0].operation_name
                # Если in_progress — «Работа пресса», но пресс ещё не запущен → «Подготовка пресса»
                if op_name == 'Работа пресса' and not self.pressing_start_time:
                    return 'Подготовка пресса'
                return op_name
            completed_count = sum(1 for op in ops if op.status == 'completed')
            if completed_count >= len(ops):
                return 'Экспертиза в ОКК'

        return 'Ожидание оператора'

    def recalculate_status(self):
        """Пересчитать статус EBR по всем 5 фактическим параметрам."""
        from quality.models import Deviation

        actual_params = EBRActualParameter.objects.filter(ebr=self).select_related('parameter')
        worst = 'ok'  # ok → warning → deviation → critical

        for ap in actual_params:
            if ap.actual_value is None:
                continue

            # Находим номинальный параметр
            try:
                nominal = EBRNominalParameter.objects.get(ebr=self, parameter=ap.parameter)
            except EBRNominalParameter.DoesNotExist:
                continue

            diff = abs(float(ap.actual_value) - float(nominal.nominal_value))
            tol_val = float(nominal.tolerance_value)
            crit_val = float(nominal.critical_value)

            if crit_val > 0 and diff > crit_val:
                worst = 'critical'
                break
            elif tol_val > 0 and diff > tol_val:
                worst = 'deviation'
            elif tol_val > 0 and diff > tol_val * 0.9 and worst not in ('critical', 'deviation'):
                worst = 'warning'

        # Применяем статус к EBR
        if worst == 'critical':
            new_status, _ = EBRStatus.objects.get_or_create(status_name='Заблокирована')
            self.status = new_status
            self.save(update_fields=['status'])
        # Для warning/deviation статус EBR не меняется визуально,
        # но отклонения уже записаны в Deviation


class EBRNominalParameter(models.Model):
    """Номинальные параметры EBR — «как должно быть» (копируются из MBR)."""
    id = models.AutoField(primary_key=True)
    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    # Номинальное значение из MBRParameter.value
    nominal_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Номинальное значение')
    # Абсолютный допуск = nominal × (tolerance% / 100)
    tolerance_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Допуск (абсолютный)')
    # Абсолютное критическое = nominal × (critical% / 100)
    critical_value = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Критическое отклонение (абсолютное)')

    class Meta:
        db_table = 'EBR_Nominal_Parameters'
        unique_together = ['ebr', 'parameter']
        verbose_name = 'Номинальный параметр EBR'
        verbose_name_plural = 'Номинальные параметры EBR'

    def __str__(self):
        return f"{self.parameter.parameter_name}: {self.nominal_value} {self.parameter.unit}"


class EBRActualParameter(models.Model):
    """Фактические параметры EBR — «как на самом деле» (оборудование или вручную)."""
    id = models.AutoField(primary_key=True)
    ebr = models.ForeignKey(EBR, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    # Последнее введённое значение
    actual_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                       verbose_name='Фактическое значение')
    # Максимальное значение за всё время (NULL если было критическое отклонение)
    max_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True,
                                    verbose_name='Максимальное значение')
    # Источник данных
    source = models.CharField(max_length=20, choices=[
        ('equipment', 'Оборудование'),
        ('manual', 'Вручную'),
    ], null=True, blank=True, verbose_name='Источник данных')

    class Meta:
        db_table = 'EBR_Actual_Parameters'
        unique_together = ['ebr', 'parameter']
        verbose_name = 'Фактический параметр EBR'
        verbose_name_plural = 'Фактические параметры EBR'

    def __str__(self):
        src = self.get_source_display() or '—'
        val = self.actual_value or '—'
        return f"{self.parameter.parameter_name}: {val} ({src})"


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