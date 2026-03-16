from django.db import models
from django.contrib.auth.models import AbstractUser
import re


class User(AbstractUser):
    ROLE_CHOICES = [
        ('operator', 'Оператор цеха'),
        ('technologist', 'Технолог'),
        ('chief_technologist', 'Главный технолог'),
        ('qc_specialist', 'Сотрудник ОКК'),
        ('qc_head', 'Начальник ОКК'),
        ('director', 'Директор'),
        ('admin', 'Системный администратор'),
    ]

    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='operator')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Отчество')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.get_role_display()})"