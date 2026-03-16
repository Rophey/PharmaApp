from django.db import models
from datetime import datetime, timedelta


class ProductionReport(models.Model):
    product_name = models.CharField(max_length=255, verbose_name='Продукт')
    report_date = models.DateField(verbose_name='Дата отчёта')
    batches_count = models.IntegerField(verbose_name='Количество партий')
    units_produced = models.IntegerField(verbose_name='Выпущено единиц')
    defect_percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Процент брака')
    raw_material_consumed = models.DecimalField(max_digits=10, decimal_places=2,
                                                verbose_name='Расход сырья (кг)')

    class Meta:
        verbose_name = 'Отчёт по выпуску'
        verbose_name_plural = 'Отчёты по выпуску'
        unique_together = ['product_name', 'report_date']

    def __str__(self):
        return f"{self.product_name} - {self.report_date}"


class DeviationReport(models.Model):
    deviation_type = models.CharField(max_length=100, verbose_name='Тип отклонения')
    report_date = models.DateField(verbose_name='Дата отчёта')
    count = models.IntegerField(verbose_name='Количество')
    percentage = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='% от общего числа')
    main_cause = models.TextField(verbose_name='Основные причины')

    class Meta:
        verbose_name = 'Отчёт по отклонениям'
        verbose_name_plural = 'Отчёты по отклонениям'
        unique_together = ['deviation_type', 'report_date']

    def __str__(self):
        return f"{self.deviation_type} - {self.report_date}"