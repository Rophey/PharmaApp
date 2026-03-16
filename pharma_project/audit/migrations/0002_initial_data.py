from django.db import migrations

def create_actions(apps, schema_editor):
    Action = apps.get_model('audit', 'Action')
    actions = [
        'Вход в систему',
        'Выход из системы',
        'Создание MBR',
        'Редактирование MBR',
        'Утверждение MBR',
        'Создание новой версии MBR',
        'Запуск партии',
        'Завершение операции',
        'Подтверждение операции',
        'Ввод данных контроля',
        'Создание отклонения',
        'Блокировка партии',
        'Разблокировка партии',
        'Подписание EBR',
        'Экспорт отчета',
        'Создание пользователя',
        'Деактивация пользователя',
        'Изменение системных настроек'
    ]
    for action_name in actions:
        Action.objects.create(action_name=action_name)

class Migration(migrations.Migration):
    dependencies = [
        ('audit', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_actions),
    ]