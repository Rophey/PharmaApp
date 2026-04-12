"""Скрипт для полного пересоздания БД"""
import psycopg2
import os
import subprocess

DB_NAME = 'pharma_db'
DB_USER = 'postgres'
DB_PASS = 'pharma'
DB_HOST = 'localhost'
DB_PORT = '5432'

print('=== Полное пересоздание БД ===')

# 1. Подключаемся к postgres (default DB)
print('1. Подключение к PostgreSQL...')
try:
    conn = psycopg2.connect(
        dbname='postgres',
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    # 2. Удаляем все активные подключения к нашей БД
    print('2. Отключение всех активных сессий...')
    cur.execute(f"""
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE pg_stat_activity.datname = '{DB_NAME}'
        AND pid <> pg_backend_pid();
    """)
    
    # 3. Удаляем БД
    print(f'3. Удаление БД "{DB_NAME}"...')
    cur.execute(f'DROP DATABASE IF EXISTS {DB_NAME};')
    print('   БД удалена')
    
    # 4. Создаём БД заново
    print(f'4. Создание БД "{DB_NAME}"...')
    cur.execute(f'CREATE DATABASE {DB_NAME};')
    print('   БД создана')
    
    cur.close()
    conn.close()
    
except Exception as e:
    print(f'Ошибка при работе с PostgreSQL: {e}')
    print('Убедитесь что PostgreSQL запущен и доступен')
    input('Нажмите Enter для выхода...')
    exit(1)

# 5. Применяем миграции Django
print('\n5. Применение миграций Django...')
os.chdir(os.path.dirname(os.path.abspath(__file__)))
result = subprocess.run(
    ['python', 'manage.py', 'migrate'],
    capture_output=True, text=True
)
if result.returncode == 0:
    print('   Миграции применены успешно')
else:
    print(f'   Ошибка миграций: {result.stderr}')
    input('Нажмите Enter для выхода...')
    exit(1)

# 6. Заполняем начальными данными
print('\n6. Заполнение БД начальными данными...')
result = subprocess.run(
    ['python', 'manage.py', 'seed_data'],
    capture_output=True, text=True
)
print(result.stdout)
if result.returncode != 0:
    print(f'   Ошибка: {result.stderr}')

print('\n✅ БД успешно пересоздана и заполнена!')
print('\nТеперь можно запустить сервер:')
print('  python manage.py runserver')
input('\nНажмите Enter для выхода...')
