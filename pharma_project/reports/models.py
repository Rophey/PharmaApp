from django.db import models
from users.models import User
from ebr.models import EBR


class ReportTemplate(models.Model):
    REPORT_TYPES = [
        ('production', 'Отчет по выпуску продукции'),
        ('deviation', 'Отчет по отклонениям'),
        ('efficiency', 'Отчет по эффективности оборудования'),
    ]

    name = models.CharField(max_length=100, verbose_name='Название отчета')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='Тип отчета')
    description = models.TextField(blank=True, null=True, verbose_name='Описание')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Создал')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    class Meta:
        db_table = 'Report_Template'
        verbose_name = 'Шаблон отчета'
        verbose_name_plural = 'Шаблоны отчетов'


class GeneratedReport(models.Model):
    FORMAT_CHOICES = [
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
        ('csv', 'CSV'),
    ]

    template = models.ForeignKey(ReportTemplate, on_delete=models.CASCADE, verbose_name='Шаблон')
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Сгенерировал')
    generated_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата генерации')
    start_date = models.DateField(verbose_name='Начало периода')
    end_date = models.DateField(verbose_name='Конец периода')
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES, default='excel', verbose_name='Формат')
    file = models.FileField(upload_to='reports/', null=True, blank=True, verbose_name='Файл отчета')
    data = models.JSONField(null=True, blank=True, verbose_name='Данные отчета')

    class Meta:
        db_table = 'Generated_Report'
        verbose_name = 'Сгенерированный отчет'
        verbose_name_plural = 'Сгенерированные отчеты'
        ordering = ['-generated_at']


class ProductionStats(models.Model):
    """Статистика производства для быстрого доступа"""
    ebr = models.OneToOneField(EBR, on_delete=models.CASCADE, verbose_name='Партия')
    total_units = models.IntegerField(default=0, verbose_name='Выпущено единиц')
    defect_units = models.IntegerField(default=0, verbose_name='Брак (единиц)')
    defect_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Процент брака')
    raw_material_used = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                            verbose_name='Расход сырья (кг)')
    equipment_efficiency = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True,
                                               verbose_name='Эффективность оборудования (%)')

    class Meta:
        db_table = 'Production_Stats'
        verbose_name = 'Статистика производства'
        verbose_name_plural = 'Статистика производства'