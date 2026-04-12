from django.db import models


class PressMachine(models.Model):
    """Таблеточный пресс"""
    name = models.CharField(max_length=100, verbose_name='Название пресса')
    machine_code = models.CharField(max_length=50, unique=True, verbose_name='Код оборудования')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    last_maintenance = models.DateField(null=True, blank=True, verbose_name='Последнее ТО')

    class Meta:
        db_table = 'Press_Machine'
        verbose_name = 'Таблеточный пресс'
        verbose_name_plural = 'Таблеточные прессы'

    def __str__(self):
        return f"{self.machine_code} - {self.name}"


class EquipmentReading(models.Model):
    """Показания с оборудования"""
    machine = models.ForeignKey(PressMachine, on_delete=models.CASCADE, verbose_name='Пресс')
    batch = models.ForeignKey('ebr.EBR', on_delete=models.CASCADE, verbose_name='Партия', null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Время считывания')
    
    # Параметры с датчиков
    pressure_force = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Усилие прессования (кН)')
    tablet_thickness = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Толщина таблетки (мм)')
    tablet_weight = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Масса таблетки (мг)')

    class Meta:
        db_table = 'Equipment_Readings'
        verbose_name = 'Показания оборудования'
        verbose_name_plural = 'Показания оборудования'
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.machine.machine_code} @ {self.timestamp}"
