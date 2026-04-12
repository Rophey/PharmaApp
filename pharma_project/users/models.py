from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, login, password=None, **extra_fields):
        if not login:
            raise ValueError('Логин обязателен')
        user = self.model(login=login, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login, password=None, **extra_fields):
        extra_fields.setdefault('role', 'системный администратор')
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('last_name', 'Admin')
        extra_fields.setdefault('first_name', 'Admin')

        return self.create_user(login, password, **extra_fields)


class User(AbstractBaseUser):
    ROLE_CHOICES = [
        ('оператор', 'Оператор цеха'),
        ('технолог', 'Технолог'),
        ('главный технолог', 'Главный технолог'),
        ('сотрудник ОКК', 'Сотрудник ОКК'),
        ('начальник ОКК', 'Начальник ОКК'),
        ('директор', 'Директор'),
        ('системный администратор', 'Системный администратор'),
    ]

    user_id = models.AutoField(primary_key=True)
    login = models.CharField(max_length=15, unique=True, verbose_name='Логин')
    password = models.CharField(max_length=255, verbose_name='Пароль')
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, verbose_name='Роль')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    middle_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Отчество')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_active = models.BooleanField(default=True, verbose_name='Активен')

    # Поля, требуемые Django
    last_login = models.DateTimeField(blank=True, null=True, verbose_name='Последний вход')
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'login'
    REQUIRED_FIELDS = ['last_name', 'first_name', 'role']

    class Meta:
        db_table = 'users_user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def has_perm(self, perm, obj=None):
        return self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_superuser

    @property
    def is_anonymous(self):
        return False

    @property
    def is_authenticated(self):
        return True

    def get_full_name(self):
        return f"{self.last_name} {self.first_name} {self.middle_name or ''}".strip()

    def get_short_name(self):
        return self.first_name

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.login})"