# accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    ROLE_CHOICES = [
        ('operator', 'Оператор'),
        ('head_technologist', 'Главный технолог'),
        ('technologist', 'Технолог'),
        ('okk_staff', 'Сотрудник ОКК'),
        ('okk_head', 'Начальник ОКК'),
        ('director', 'Директор'),
        ('admin', 'Системный администратор'),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)

    class Meta:
        verbous_name = 'Пользователь'
        verbous_name_plural = 'Пользователи'
        db_table = 'Пользователи'

    def __str__(self):
        return f"{self.username} ({self.role})"

