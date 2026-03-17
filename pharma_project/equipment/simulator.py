import random
import time
import threading
from datetime import datetime
from ebr.models import EBR, EBRParameter, BatchOperation
from quality.models import Deviation
from audit.models import Action, AuditLog


class TabletPressSimulator:
    """Имитатор таблеточного пресса"""

    def __init__(self):
        self.running = False
        self.thread = None
        self.current_ebr = None

    def start_production(self, ebr_id):
        """Запуск производства партии"""
        from ebr.models import EBR, BatchOperation
        from quality.models import Deviation

        self.current_ebr = EBR.objects.get(document_id=ebr_id)
        self.running = True

        # Создаём операции
        operations = [
            'Подготовка сырья',
            'Настройка пресса',
            'Прессование',
            'Контроль качества'
        ]

        for op_name in operations:
            BatchOperation.objects.create(
                ebr=self.current_ebr,
                operation_name=op_name,
                status='pending'
            )

        # Запускаем поток симуляции
        self.thread = threading.Thread(target=self._simulate)
        self.thread.start()

        return True

    def stop_production(self):
        """Остановка производства"""
        self.running = False
        if self.thread:
            self.thread.join()

    def _simulate(self):
        """Основной цикл симуляции"""
        operations = BatchOperation.objects.filter(
            ebr=self.current_ebr
        ).order_by('id')

        for operation in operations:
            if not self.running:
                break

            # Начинаем операцию
            operation.status = 'in_progress'
            operation.started_at = datetime.now()
            operation.save()

            # Симулируем выполнение операции
            if operation.operation_name == 'Прессование':
                self._simulate_pressing(operation)
            else:
                # Для других операций просто ждём
                time.sleep(2)
                operation.status = 'completed'
                operation.completed_at = datetime.now()
                operation.save()

    def _simulate_pressing(self, operation):
        """Симуляция процесса прессования с генерацией параметров"""
        import random
        from quality.models import Deviation

        # Получаем параметры из MBR
        parameters = EBRParameter.objects.filter(
            ebr=self.current_ebr
        ).select_related('parameter')

        for ebr_param in parameters:
            if not self.running:
                break

            param = ebr_param.parameter

            # Генерируем случайное значение с возможными отклонениями
            # 70% - норма, 20% - предупреждение, 8% - отклонение, 2% - критическое
            rand = random.random()

            if rand < 0.7:  # Норма
                variation = random.uniform(-param.tolerance / 2, param.tolerance / 2)
                actual = param.value * (1 + variation / 100)
                status = 'normal'

            elif rand < 0.9:  # Предупреждение (в пределах допуска)
                variation = random.uniform(param.tolerance / 2, param.tolerance)
                if random.choice([True, False]):
                    actual = param.value * (1 + variation / 100)
                else:
                    actual = param.value * (1 - variation / 100)
                status = 'warning'

            elif rand < 0.98:  # Отклонение (превышает допуск, но не критично)
                variation = random.uniform(param.tolerance, param.critical_deviation)
                if random.choice([True, False]):
                    actual = param.value * (1 + variation / 100)
                else:
                    actual = param.value * (1 - variation / 100)
                status = 'deviation'

            else:  # Критическое отклонение
                variation = random.uniform(param.critical_deviation, param.critical_deviation * 1.5)
                if random.choice([True, False]):
                    actual = param.value * (1 + variation / 100)
                else:
                    actual = param.value * (1 - variation / 100)
                status = 'critical'

            # Сохраняем значение
            ebr_param.actual_value = round(actual, 2)
            ebr_param.save()

            # Если отклонение - создаём запись
            if status in ['deviation', 'critical']:
                Deviation.objects.create(
                    ebr=self.current_ebr,
                    deviation_type='critical' if status == 'critical' else 'deviation',
                    parameter_name=param.parameter_name,
                    expected_value=param.value,
                    actual_value=round(actual, 2),
                    tolerance=param.tolerance,
                    description=f"{'Критическое' if status == 'critical' else ''} отклонение: {round(abs((actual - param.value) / param.value * 100), 1)}%",
                    detected_at=datetime.now()
                )

                # Если критическое - блокируем операцию
                if status == 'critical':
                    from ebr.models import EBRStatus
                    self.current_ebr.status = EBRStatus.objects.get(status_name='Заблокирована')
                    self.current_ebr.save()
                    operation.status = 'blocked'
                    operation.save()
                    self.running = False
                    break

            time.sleep(1)  # Пауза между измерениями

        if self.running:
            operation.status = 'completed'
            operation.completed_at = datetime.now()
            operation.save()


# Создаём глобальный экземпляр симулятора
simulator = TabletPressSimulator()