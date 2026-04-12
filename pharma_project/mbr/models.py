from django.db import models
from users.models import User


class Product(models.Model):
    product_name = models.CharField(max_length=255, verbose_name='Наименование продукта')
    product_code = models.CharField(max_length=50, unique=True, verbose_name='Код продукта')

    class Meta:
        db_table = 'Product'
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return f"{self.product_code} - {self.product_name}"


class RawMaterial(models.Model):
    material_name = models.CharField(max_length=255, verbose_name='Наименование сырья')

    class Meta:
        db_table = 'Raw_Material'
        verbose_name = 'Сырьё'
        verbose_name_plural = 'Сырьё'

    def __str__(self):
        return self.material_name


class Parameter(models.Model):
    parameter_name = models.CharField(max_length=100, verbose_name='Название параметра')
    unit = models.CharField(max_length=20, verbose_name='Единица измерения')
    value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Значение')
    tolerance = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Допустимое отклонение (%)')
    critical_deviation = models.DecimalField(max_digits=5, decimal_places=2, verbose_name='Критическое отклонение (%)')

    class Meta:
        db_table = 'Parameter'
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'

    def __str__(self):
        return f"{self.parameter_name} ({self.unit})"


class DocumentType(models.Model):
    TYPE_CHOICES = [('MBR', 'MBR'), ('EBR', 'EBR')]
    type_name = models.CharField(max_length=50, choices=TYPE_CHOICES, verbose_name='Тип документа')

    class Meta:
        db_table = 'Document_Type'
        verbose_name = 'Тип документа'
        verbose_name_plural = 'Типы документов'

    def __str__(self):
        return self.type_name


class Document(models.Model):
    type = models.ForeignKey(DocumentType, on_delete=models.CASCADE, verbose_name='Тип документа')

    class Meta:
        db_table = 'Document'
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'


class MBRStatus(models.Model):
    STATUS_CHOICES = [('Черновик', 'Черновик'), ('Утверждён', 'Утверждён')]
    status_name = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name='Статус')

    class Meta:
        db_table = 'MBR_Status'
        verbose_name = 'Статус MBR'
        verbose_name_plural = 'Статусы MBR'

    def __str__(self):
        return self.status_name


class MBR(models.Model):
    document = models.OneToOneField(Document, on_delete=models.CASCADE, primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Продукт')
    version = models.CharField(max_length=10, verbose_name='Версия')
    status = models.ForeignKey(MBRStatus, on_delete=models.CASCADE, verbose_name='Статус')
    operations = models.TextField(verbose_name='Технологические операции')
    approval_date = models.DateField(null=True, blank=True, verbose_name='Дата утверждения')
    comments = models.TextField(blank=True, null=True, verbose_name='Комментарий к версии')
    signed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Утвердил')
    raw_materials = models.ManyToManyField(RawMaterial, through='MBRRawMaterial')
    parameters = models.ManyToManyField(Parameter, through='MBRParameter')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'MBR'
        unique_together = ['product', 'version']
        verbose_name = 'MBR'
        verbose_name_plural = 'MBR'

    def __str__(self):
        return f"{self.product.product_code} v{self.version}"


class MBRRawMaterial(models.Model):
    id = models.AutoField(primary_key=True)
    mbr = models.ForeignKey(MBR, on_delete=models.CASCADE)
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)

    class Meta:
        db_table = 'MBR_Raw_Materials'
        unique_together = ['mbr', 'raw_material']


class MBRParameter(models.Model):
    """Параметры конкретного MBR (хранят свои значения для каждого MBR)"""
    id = models.AutoField(primary_key=True)
    mbr = models.ForeignKey(MBR, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    # Своя копия значений для ЭТОГО MBR
    value = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Значение')
    tolerance = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Допустимое отклонение (%)')
    critical_deviation = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name='Критическое отклонение (%)')

    class Meta:
        db_table = 'MBR_Parameters'
        unique_together = ['mbr', 'parameter']

    def __str__(self):
        return f"{self.parameter.parameter_name}: {self.value} {self.parameter.unit}"