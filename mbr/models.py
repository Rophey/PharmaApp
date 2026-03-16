from django.db import models
from accounts.models import User


class Product(models.Model):
    product_name = models.CharField(max_length=255, verbose_name='Наименование продукта')
    product_code = models.CharField(max_length=50, unique=True, verbose_name='Код продукта')

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return f"{self.product_code} - {self.product_name}"


class MBRStatus(models.Model):
    status_name = models.CharField(max_length=20, choices=[
        ('draft', 'Черновик'),
        ('approved', 'Утверждён'),
    ], verbose_name='Статус')

    class Meta:
        verbose_name = 'Статус MBR'
        verbose_name_plural = 'Статусы MBR'

    def __str__(self):
        return self.status_name


class Parameter(models.Model):
    parameter_name = models.CharField(max_length=100, verbose_name='Название параметра')
    unit = models.CharField(max_length=20, verbose_name='Единица измерения')
    value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Значение')
    tolerance = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Допустимое отклонение (%)')
    critical_deviation = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Критическое отклонение (%)')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'

    def __str__(self):
        return f"{self.parameter_name} ({self.unit})"


class RawMaterial(models.Model):
    material_name = models.CharField(max_length=255, verbose_name='Наименование сырья')

    class Meta:
        verbose_name = 'Сырьё'
        verbose_name_plural = 'Сырьё'

    def __str__(self):
        return self.material_name


class MBR(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    version = models.CharField(max_length=10, verbose_name='Версия')
    status = models.ForeignKey(MBRStatus, on_delete=models.CASCADE, verbose_name='Статус')
    operations = models.TextField(verbose_name='Описание технологических операций')
    approval_date = models.DateField(blank=True, null=True, verbose_name='Дата утверждения')
    comments = models.TextField(blank=True, null=True, verbose_name='Комментарий к версии')
    parameters = models.ManyToManyField(Parameter, verbose_name='Параметры процесса')
    raw_materials = models.ManyToManyField(RawMaterial, verbose_name='Сырьё')
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True,
                                  verbose_name='Утвердил', related_name='approved_mbrs')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'MBR (Мастер-рецептура)'
        verbose_name_plural = 'MBR (Мастер-рецептуры)'
        unique_together = ['product', 'version']

    def __str__(self):
        return f"{self.product.product_code} - v{self.version}"

    def save(self, *args, **kwargs):
        if not self.version:
            last_mbr = MBR.objects.filter(product=self.product).order_by('-version').first()
            if last_mbr:
                last_version = int(last_mbr.version.replace('v', ''))
                self.version = f'v{last_version + 1}'
            else:
                self.version = 'v1'
        super().save(*args, **kwargs)