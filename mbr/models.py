# mbr/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class MBR(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Продукт")
    version = models.CharField(max_length=10, verbose_name="Версия MBR (vN)", editable=False)
    status = models.CharField(max_length=10, choices=MBRStatus.choices, default=MBRStatus.DRAFT, verbose_name="Статус")
    operations_description = models.TextField(verbose_name="Описание технологических операций")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_mbrs', verbose_name="Создано пользователем")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    approved_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_mbrs', verbose_name="Утверждено пользователем")
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата утверждения")
    comment = models.TextField(blank=True, verbose_name="Комментарий к версии")
    parent_mbr = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, verbose_name="Родительская версия MBR")

    class Meta:
        unique_together = ('product', 'version') # Уникальность версии в рамках продукта
        verbose_name = "Master Batch Record"
        verbose_name_plural = "Master Batch Records"

    def clean(self):
        # Проверка, что нельзя редактировать утверждённый MBR
        if self.pk and self.status == MBRStatus.APPROVED:
            original = MBR.objects.get(pk=self.pk)
            if original.status == MBRStatus.APPROVED:
                # Проверяем, какие поля изменились (можно сделать более подробно)
                if (self.product != original.product or
                    self.operations_description != original.operations_description or
                    # ... другие поля, которые нельзя менять в утверждённом MBR ...
                    ):
                     raise ValidationError(_('Нельзя изменять данные утверждённого MBR. Создайте новую версию.'))

        # Проверка, что утверждать можно только черновик
        if self.status == MBRStatus.APPROVED and not self.approved_by:
             raise ValidationError(_('Для утверждения MBR необходимо указать пользователя, который утверждает.'))

        super().clean()

    def save(self, *args, **kwargs):
        # Генерация версии при создании новой версии
        if not self.version and self.parent_mbr:
            # Найти максимальную версию для этого продукта
            last_version = MBR.objects.filter(product=self.product).exclude(version='').order_by('-version').first()
            if last_version:
                try:
                    # Извлекаем число из строки версии, предполагая формат vN
                    last_num_str = last_version.version[1:] # отрезаем 'v'
                    last_num = int(last_num_str)
                    new_num = last_num + 1
                except (ValueError, IndexError):
                    # Если формат не vN, начинаем с 1
                    new_num = 1
            else:
                new_num = 1
            self.version = f"v{new_num}"
        elif not self.version:
            # Если версия не задана и нет родителя, начинаем с v1
            self.version = "v1"

        # Установка даты утверждения
        if self.status == MBRStatus.APPROVED and not self.approved_at:
            # Предположим, что `approved_by` уже установлен в представлении до вызова save()
            # или можно здесь принудительно выставить timezone.now(), но лучше в view
            pass # Логика установки даты утверждения будет в view при смене статуса

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.product_code} - {self.version} ({self.get_status_display()})"


class Product(models.Model):
    product_name = models.CharField(
        max_length=255,
        help_text="Только латинские и русские буквы, цифры"
    )
    product_code = models.CharField(
        max_length=50,
        unique=True,
        help_text="Только латинские буквы, цифры, символ -"
    )

    def __str__(self):
        return f"{self.product_name} ({self.product_code})"

class MBRStatus(models.TextChoices):
    DRAFT = 'draft', 'Черновик'
    APPROVED = 'approved', 'Утверждён'

    def __str__(self):
        return self.name


class Parameter(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название параметра")
    unit = models.CharField(max_length=20, verbose_name="Единица измерения")

    def __str__(self):
        return f"{self.name} ({self.unit})"


class MBRParameter(models.Model):
    mbr = models.ForeignKey('MBR', on_delete=models.CASCADE, related_name='mbr_parameters')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE)
    planned_value = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Значение")
    planned_tolerance = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Допустимое отклонение (%)")
    planned_critical_deviation = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Критическое отклонение (%)")

    def __str__(self):
        return f"{self.mbr.product_code} - {self.parameter.name}"


class RawMaterial(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return f"{self.name} ({self.code})"


class MBRRawMaterial(models.Model):
    mbr = models.ForeignKey('MBR', on_delete=models.CASCADE, related_name='mbr_raw_materials')
    raw_material = models.ForeignKey(RawMaterial, on_delete=models.CASCADE)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0) # Добавим поле количества
    unit = models.CharField(max_length=20, default="кг") # Или отдельная FK на справочник единиц

    def __str__(self):
        return f"{self.mbr.product_code} - {self.raw_material.name}"
