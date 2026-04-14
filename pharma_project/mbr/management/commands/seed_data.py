import sys
import io
# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from django.core.management.base import BaseCommand
from mbr.models import MBRStatus, DocumentType, Product, Parameter, RawMaterial, MBR, MBRParameter, MBRRawMaterial, Document
from ebr.models import EBRStatus
from audit.models import Action
from users.models import User
from decimal import Decimal
import datetime


class Command(BaseCommand):
    help = 'Заполняет БД начальными данными (статусы, продукты, параметры, сырьё, действия)'

    def handle(self, *args, **options):
        self.stdout.write('Заполнение БД начальными данными...')

        # Статусы MBR
        MBRStatus.objects.get_or_create(status_name='Черновик')
        MBRStatus.objects.get_or_create(status_name='Утверждён')
        self.stdout.write('[OK] Статусы MBR созданы')

        # Статусы EBR
        EBRStatus.objects.get_or_create(status_name='В ожидании')
        EBRStatus.objects.get_or_create(status_name='В работе')
        EBRStatus.objects.get_or_create(status_name='Завершена')
        EBRStatus.objects.get_or_create(status_name='Заблокирована')
        self.stdout.write('[OK] Статусы EBR созданы')

        # Типы документов
        DocumentType.objects.get_or_create(type_name='MBR')
        DocumentType.objects.get_or_create(type_name='EBR')
        self.stdout.write('[OK] Типы документов созданы')

        # Действия для аудита
        actions = [
            'Вход в систему', 'Выход из системы',
            'Создание MBR', 'Утверждение MBR', 'Редактирование MBR',
            'Создание EBR', 'Запуск партии', 'Подписание EBR',
            'Ввод данных контроля', 'Обнаружение отклонения',
            'Решение по отклонению', 'Блокировка партии', 'Разблокировка партии',
            'Создание пользователя', 'Деактивация пользователя',
            'Изменение правил генерации номеров партий', 'Генерация отчёта',
        ]
        for action_name in actions:
            Action.objects.get_or_create(action_name=action_name)
        self.stdout.write(f'[OK] Создано {len(actions)} действий для аудита')

        # Продукты
        products = [
            ('Аспирин 500 мг', 'ASP-500'),
            ('Парацетамол 500 мг', 'PAR-500'),
            ('Ибупрофен 400 мг', 'IBU-400'),
        ]
        for name, code in products:
            Product.objects.get_or_create(
                product_code=code,
                defaults={'product_name': name}
            )
        self.stdout.write(f'[OK] Создано {len(products)} продукта')

        # Параметры
        params = [
            ('Усилие прессования', 'кН', 50.0, 10.0, 20.0),
            ('Толщина таблетки', 'мм', 5.0, 5.0, 10.0),
            ('Твердость таблетки', 'кПа', 100.0, 15.0, 25.0),
            ('Масса таблетки', 'мг', 500.0, 5.0, 10.0),
            ('Время распадаемости', 'мин', 15.0, 20.0, 30.0),
        ]
        for name, unit, value, tol, crit in params:
            Parameter.objects.get_or_create(
                parameter_name=name,
                unit=unit,
                defaults={'value': value, 'tolerance': tol, 'critical_deviation': crit}
            )
        self.stdout.write(f'[OK] Создано {len(params)} параметров')

        # Сырьё
        materials = [
            'Ацетилсалициловая кислота', 'Парацетамол', 'Ибупрофен',
            'Крахмал кукурузный', 'Стеарат магния', 'Микрокристаллическая целлюлоза',
        ]
        for mat_name in materials:
            RawMaterial.objects.get_or_create(material_name=mat_name)
        self.stdout.write(f'[OK] Создано {len(materials)} видов сырья')

        # Пользователи (по одному на каждую роль)
        # Пароль у всех: Test1234! (соответствует требованиям: 8-15 символов, латиница+цифры+спецсимволы)
        users_data = [
            ('admin_test1234', 'Test1234!', 'системный администратор', 'Админов', 'Системный', 'Админович'),
            ('chief_tech12', 'Test1234!', 'главный технолог', 'Главтехнов', 'Главный', 'Технологович'),
            ('tech_user123', 'Test1234!', 'технолог', 'Технологов', 'Технолог', 'Технологович'),
            ('operator1234', 'Test1234!', 'оператор', 'Операторов', 'Оператор', 'Операторович'),
            ('qc_spec12345', 'Test1234!', 'сотрудник ОКК', 'ОККшников', 'Сотрудник', 'ОККович'),
            ('qc_chief123', 'Test1234!', 'начальник ОКК', 'ОККначальников', 'Начальник', 'ОККович'),
            ('director1234', 'Test1234!', 'директор', 'Директоров', 'Директор', 'Директорович'),
        ]
        for login, password, role, last_name, first_name, middle_name in users_data:
            user, created = User.objects.get_or_create(
                login=login,
                defaults={
                    'role': role,
                    'last_name': last_name,
                    'first_name': first_name,
                    'middle_name': middle_name,
                    'is_active': True,
                }
            )
            if created:
                user.set_password(password)
                user.save()
        self.stdout.write(f'[OK] Создано {len(users_data)} тестовых пользователей (пароль: Test1234!)')

        # MBR (мастер-рецептуры)
        chief_tech = User.objects.get(login='chief_tech12')
        draft_status = MBRStatus.objects.get(status_name='Черновик')
        approved_status = MBRStatus.objects.get(status_name='Утверждён')
        doc_type = DocumentType.objects.get(type_name='MBR')

        aspirin_product = Product.objects.get(product_code='ASP-500')
        paracetamol_product = Product.objects.get(product_code='PAR-500')

        mbrs_data = [
            {
                'product': aspirin_product,
                'version': 'v1',
                'status': approved_status,
                'operations': '1. Подготовка сырья\n2. Смешивание\n3. Таблетирование\n4. Контроль качества',
                'approval_date': datetime.date(2026, 4, 1),
                'comments': 'Первичная рецептура Аспирина 500 мг',
                'parameters': {
                    'Усилие прессования': {'value': 50.0, 'tolerance': 10.0, 'critical': 20.0},
                    'Толщина таблетки': {'value': 5.0, 'tolerance': 5.0, 'critical': 10.0},
                    'Твердость таблетки': {'value': 100.0, 'tolerance': 15.0, 'critical': 25.0},
                    'Масса таблетки': {'value': 500.0, 'tolerance': 5.0, 'critical': 10.0},
                    'Время распадаемости': {'value': 15.0, 'tolerance': 20.0, 'critical': 30.0},
                },
                'raw_materials': ['Ацетилсалициловая кислота', 'Крахмал кукурузный', 'Стеарат магния'],
            },
            {
                'product': paracetamol_product,
                'version': 'v1',
                'status': draft_status,
                'operations': '1. Подготовка сырья\n2. Смешивание\n3. Таблетирование\n4. Контроль качества',
                'comments': 'Рецептура Парацетамола 500 мг (черновик)',
                'parameters': {
                    'Усилие прессования': {'value': 45.0, 'tolerance': 10.0, 'critical': 20.0},
                    'Толщина таблетки': {'value': 5.5, 'tolerance': 5.0, 'critical': 10.0},
                    'Твердость таблетки': {'value': 90.0, 'tolerance': 15.0, 'critical': 25.0},
                    'Масса таблетки': {'value': 500.0, 'tolerance': 5.0, 'critical': 10.0},
                    'Время распадаемости': {'value': 12.0, 'tolerance': 20.0, 'critical': 30.0},
                },
                'raw_materials': ['Парацетамол', 'Крахмал кукурузный', 'Микрокристаллическая целлюлоза'],
            },
        ]

        for mbr_data in mbrs_data:
            # Проверяем, есть ли уже такой MBR
            existing = MBR.objects.filter(product=mbr_data['product'], version=mbr_data['version']).first()
            if existing:
                status_label = 'Утверждён' if mbr_data['status'] == approved_status else 'Черновик'
                self.stdout.write(f'[SKIP] MBR {mbr_data["product"].product_code} {mbr_data["version"]} уже существует ({status_label})')
                continue

            doc = Document.objects.create(type=doc_type)
            mbr = MBR.objects.create(
                product=mbr_data['product'],
                version=mbr_data['version'],
                document=doc,
                status=mbr_data['status'],
                operations=mbr_data['operations'],
                comments=mbr_data.get('comments', ''),
                signed_by=chief_tech if mbr_data['status'] == approved_status else None,
                approval_date=mbr_data.get('approval_date', None),
            )

            # Параметры
            for param_name, vals in mbr_data['parameters'].items():
                param = Parameter.objects.get(parameter_name=param_name)
                MBRParameter.objects.create(
                    mbr=mbr,
                    parameter=param,
                    value=Decimal(str(vals['value'])),
                    tolerance=Decimal(str(vals['tolerance'])),
                    critical_deviation=Decimal(str(vals['critical'])),
                )

            # Сырьё
            for mat_name in mbr_data['raw_materials']:
                material = RawMaterial.objects.get(material_name=mat_name)
                MBRRawMaterial.objects.create(mbr=mbr, raw_material=material)

            status_label = 'Утверждён' if mbr_data['status'] == approved_status else 'Черновик'
            self.stdout.write(f'[OK] Создан MBR {mbr_data["product"].product_code} {mbr_data["version"]} ({status_label})')

        self.stdout.write('\n=== БД успешно заполнена начальными данными! ===')
