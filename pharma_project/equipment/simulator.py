import random
import time
import threading
from datetime import datetime, timedelta
from django.utils import timezone
from ebr.models import EBR, EBRNominalParameter, EBRActualParameter, EBRStatus
from quality.models import Deviation


class TabletPressSimulator:
    """Имитатор таблеточного пресса — поддерживает несколько партий одновременно."""

    def __init__(self):
        # {ebr_id: {'running': bool, 'thread': Thread, 'pressing_time': int}}
        self.active_productions = {}
        self._lock = threading.Lock()

    def start_production(self, ebr_id, pressing_time=10):
        """Запуск производства конкретной партии."""
        try:
            EBR.objects.get(document_id=ebr_id)
        except EBR.DoesNotExist:
            return False

        with self._lock:
            if ebr_id in self.active_productions:
                return False
            self.active_productions[ebr_id] = {
                'running': True,
                'thread': None,
                'pressing_time': pressing_time,
            }

        thread = threading.Thread(
            target=self._simulate, args=(ebr_id, pressing_time), daemon=True
        )
        with self._lock:
            self.active_productions[ebr_id]['thread'] = thread
        thread.start()
        return True

    def stop_production(self, ebr_id):
        """Остановка производства конкретной партии."""
        with self._lock:
            prod = self.active_productions.get(ebr_id)
            if prod:
                prod['running'] = False

    def _simulate(self, ebr_id, pressing_time):
        """Основной цикл симуляции для конкретной партии."""
        try:
            ebr = EBR.objects.get(document_id=ebr_id)
        except EBR.DoesNotExist:
            return

        nominal_params = list(
            EBRNominalParameter.objects.filter(ebr=ebr).select_related('parameter')
        )
        if not nominal_params:
            return

        # Исключаем «Время распадаемости» — вручную
        manual_kw = ['время распадаем', 'disintegration']
        equipment_params = [
            np for np in nominal_params
            if not any(skip in np.parameter.parameter_name.lower() for skip in manual_kw)
        ]

        readings_count = max(1, pressing_time // 3)
        interval = 3  # фиксированный интервал 3 секунды

        for i in range(readings_count):
            with self._lock:
                prod = self.active_productions.get(ebr_id)
                if not prod or not prod['running']:
                    break

            for np_param in equipment_params:
                with self._lock:
                    prod = self.active_productions.get(ebr_id)
                    if not prod or not prod['running']:
                        break

                nominal = float(np_param.nominal_value)
                tol = float(np_param.tolerance_value)
                crit = float(np_param.critical_value)
                actual = self._generate_value(nominal, tol, crit)

                try:
                    ap = EBRActualParameter.objects.get(
                        ebr=ebr, parameter=np_param.parameter
                    )
                except EBRActualParameter.DoesNotExist:
                    continue

                ap.actual_value = round(actual, 2)
                ap.source = 'equipment'
                if ap.max_value is None or actual > float(ap.max_value):
                    ap.max_value = round(actual, 2)
                ap.save(update_fields=['actual_value', 'max_value', 'source'])

                diff = abs(actual - nominal)
                if crit > 0 and diff > crit:
                    Deviation.objects.create(
                        ebr=ebr, deviation_type='critical',
                        parameter_name=np_param.parameter.parameter_name,
                        expected_value=np_param.nominal_value,
                        actual_value=round(actual, 2),
                        tolerance=np_param.tolerance_value,
                        description=f"Критическое отклонение: {diff:.1f} > {crit:.1f}",
                    )
                    ap.max_value = None
                    ap.save(update_fields=['max_value'])
                    try:
                        blocked = EBRStatus.objects.get(status_name='Заблокирована')
                        ebr.status = blocked
                        ebr.save(update_fields=['status'])
                    except EBRStatus.DoesNotExist:
                        pass
                    with self._lock:
                        prod = self.active_productions.get(ebr_id)
                        if prod:
                            prod['running'] = False
                    break
                elif tol > 0 and diff > tol:
                    Deviation.objects.create(
                        ebr=ebr, deviation_type='deviation',
                        parameter_name=np_param.parameter.parameter_name,
                        expected_value=np_param.nominal_value,
                        actual_value=round(actual, 2),
                        tolerance=np_param.tolerance_value,
                        description=f"Отклонение: {diff:.1f} > {tol:.1f}",
                    )

            time.sleep(interval)

        with self._lock:
            prod = self.active_productions.get(ebr_id)
            if prod:
                prod['running'] = False

        try:
            ebr = EBR.objects.get(document_id=ebr_id)
            ebr.recalculate_status()
            self._create_qc_task(ebr)
        except Exception:
            pass

    def _create_qc_task(self, ebr):
        from quality.models import QCTask
        from users.models import User
        import datetime as dt

        qc_user = User.objects.filter(
            role='сотрудник ОКК', is_active=True
        ).first()
        if not qc_user:
            return
        if QCTask.objects.filter(ebr=ebr).exists():
            return

        QCTask.objects.create(
            ebr=ebr, task_type='testing', status='new',
            assigned_to=qc_user, created_by=qc_user,
            due_date=timezone.now() + timedelta(hours=4),
        )

    @staticmethod
    def _generate_value(nominal, tolerance, critical):
        scenario = random.random()
        if tolerance == 0:
            return nominal

        if scenario < 0.88:
            max_dev = tolerance * 0.5
        elif scenario < 0.98:
            max_dev = random.uniform(tolerance * 0.5, tolerance * 0.9)
        elif scenario < 0.995:
            max_dev = random.uniform(tolerance * 0.9, tolerance)
        else:
            max_dev = random.uniform(
                tolerance, critical if critical > 0 else tolerance * 1.5
            )

        deviation = random.gauss(0, max_dev / 2)
        return round(nominal + deviation, 2)


simulator = TabletPressSimulator()
