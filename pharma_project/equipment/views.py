from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import PressMachine, EquipmentReading
from ebr.models import EBR, EBRNominalParameter, EBRActualParameter, EBRStatus
import datetime
import random
import json


def get_machines(request):
    """Получить список всех прессов"""
    machines = PressMachine.objects.filter(is_active=True)
    data = [{'id': m.id, 'code': m.machine_code, 'name': m.name} for m in machines]
    return JsonResponse({'machines': data})


@csrf_exempt
def simulate_reading(request, machine_id):
    """
    Симулировать показания с оборудования.
    Если указан batch_id — генерирует значения относительно номинальных параметров партии.
    Если batch_id не указан — генерирует в общих диапазонах.

    Реалистичная генерация:
    - ~88% показаний в пределах нормы (±50% от допуска)
    - ~10% показаний близко к границе допуска (50-90% от допуска) — предупреждение
    - ~2% показаний за допуском (>100%) — отклонение
    - ~0.5% показаний за критическим пределом — критическое отклонение
    """
    if request.method == 'POST':
        try:
            machine = PressMachine.objects.get(id=machine_id)

            batch_id = request.POST.get('batch_id')
            ebr = None
            ebr_params = {}  # {parameter_name: {nominal, tolerance, critical}}

            if batch_id:
                try:
                    ebr = EBR.objects.get(document_id=batch_id)
                    # Загружаем номинальные параметры партии
                    params = EBRNominalParameter.objects.filter(ebr=ebr).select_related('parameter')
                    for p in params:
                        ebr_params[p.parameter.parameter_name.lower()] = {
                            'nominal': float(p.nominal_value),
                            'tolerance': float(p.tolerance_value),
                            'critical': float(p.critical_value),
                            'unit': p.parameter.unit,
                            'param_obj': p,
                        }
                except EBR.DoesNotExist:
                    pass

            # Генерируем показания
            if ebr_params:
                # Реалистичная генерация на основе номинальных значений партии
                pressure = _realistic_value(ebr_params.get('усилие прессования', {}),
                                            default_nominal=50.0, default_tolerance=10.0)
                thickness = _realistic_value(ebr_params.get('толщина таблетки', {}),
                                             default_nominal=5.0, default_tolerance=5.0)
                weight = _realistic_value(ebr_params.get('масса таблетки', {}),
                                          default_nominal=500.0, default_tolerance=5.0)
            else:
                # Общие значения без привязки к партии
                pressure = round(random.uniform(40, 60), 2)
                thickness = round(random.uniform(4.5, 5.5), 2)
                weight = round(random.uniform(490, 510), 2)

            reading = EquipmentReading.objects.create(
                machine=machine,
                batch=ebr,
                pressure_force=pressure,
                tablet_thickness=thickness,
                tablet_weight=weight
            )

            return JsonResponse({
                'success': True,
                'reading': {
                    'id': reading.id,
                    'pressure_force': float(reading.pressure_force),
                    'tablet_thickness': float(reading.tablet_thickness),
                    'tablet_weight': float(reading.tablet_weight),
                    'timestamp': reading.timestamp.isoformat()
                }
            })
        except PressMachine.DoesNotExist:
            return JsonResponse({'error': 'Machine not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def _realistic_value(param_info, default_nominal, default_tolerance):
    """
    Генерирует реалистичное значение параметра с нормальным распределением.

    - 88%: в пределах 50% от допуска (норма)
    - 10%: 50-90% от допуска (предупреждение)
    - 2%: 90-110% от допуска (отклонение)
    - 0.5%: > критического отклонения
    """
    nominal = param_info.get('nominal', default_nominal)
    tolerance = param_info.get('tolerance', default_tolerance)
    critical = param_info.get('critical', tolerance * 2)

    # Определяем сценарий
    scenario = random.random()

    if scenario < 0.88:
        # Норма: ±50% от допуска (большинство показаний)
        max_deviation = nominal * (tolerance / 100) * 0.5
    elif scenario < 0.98:
        # Предупреждение: 50-90% от допуска
        max_deviation = nominal * (tolerance / 100) * 0.9
        min_deviation = nominal * (tolerance / 100) * 0.5
        max_deviation = random.uniform(min_deviation, max_deviation)
    elif scenario < 0.995:
        # Отклонение: 90-100% от допуска
        max_deviation = nominal * (tolerance / 100) * random.uniform(0.95, 1.0)
    else:
        # Критическое отклонение: > критического
        max_deviation = nominal * (critical / 100) * random.uniform(1.0, 1.5)

    # Случайное отклонение в выбранном диапазоне с нормальным распределением
    deviation = random.gauss(0, max_deviation / 2)
    value = nominal + deviation

    return round(value, 2)


@csrf_exempt
def send_reading(request, machine_id):
    """Получить показания от симулятора/оборудования и сохранить в БД"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            machine = PressMachine.objects.get(id=machine_id)

            batch = None
            batch_id = data.get('batch_id')
            if batch_id:
                try:
                    batch = EBR.objects.get(document_id=batch_id)
                except EBR.DoesNotExist:
                    pass

            reading = EquipmentReading.objects.create(
                machine=machine,
                batch=batch,
                pressure_force=data.get('pressure_force'),
                tablet_thickness=data.get('tablet_thickness'),
                tablet_weight=data.get('tablet_weight')
            )

            # Проверка на отклонения если привязано к партии
            if batch:
                _check_deviations(reading, batch)

            return JsonResponse({'success': True, 'reading_id': reading.id})
        except PressMachine.DoesNotExist:
            return JsonResponse({'error': 'Machine not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@csrf_exempt
def send_for_batch(request, machine_id):
    """
    Отправить показания с оборудования для конкретной партии.
    Автоматически обновляет EBRActualParameter.max_value
    и проверяет отклонения.

    POST /equipment/api/machine/<id>/send-for-batch/
    Body: {"batch_id": <int>, "pressure_force": <float>, "tablet_thickness": <float>, "tablet_weight": <float>}
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            machine = PressMachine.objects.get(id=machine_id)

            batch_id = data.get('batch_id')
            if not batch_id:
                return JsonResponse({'error': 'batch_id is required'}, status=400)

            batch = get_object_or_404(EBR, document_id=batch_id)

            pressure = float(data.get('pressure_force', 0))
            thickness = float(data.get('tablet_thickness', 0))
            weight = float(data.get('tablet_weight', 0))

            # Сохраняем показание
            reading = EquipmentReading.objects.create(
                machine=machine,
                batch=batch,
                pressure_force=pressure,
                tablet_thickness=thickness,
                tablet_weight=weight
            )

            # Обновляем EBRActualParameter.max_value и actual_value
            ebr_params = EBRActualParameter.objects.filter(ebr=batch).select_related('parameter')
            for ebr_param in ebr_params:
                pname = ebr_param.parameter.parameter_name.lower()
                new_value = None

                if 'усилие' in pname or 'force' in pname:
                    new_value = pressure
                elif 'толщин' in pname or 'thick' in pname:
                    new_value = thickness
                elif 'масс' in pname or 'weight' in pname:
                    new_value = weight

                if new_value is not None:
                    ebr_param.actual_value = new_value
                    ebr_param.source = 'equipment'

                    # Обновляем max_value (только если не было критического)
                    if ebr_param.max_value is None or new_value > float(ebr_param.max_value):
                        ebr_param.max_value = new_value

                    ebr_param.save(update_fields=['actual_value', 'max_value', 'source'])

                    # Проверка отклонений
                    _check_ebr_param_deviation(batch, ebr_param)

            # Пересчитываем общий статус EBR
            batch.recalculate_status()

            return JsonResponse({
                'success': True,
                'reading_id': reading.id,
                'pressure_force': pressure,
                'tablet_thickness': thickness,
                'tablet_weight': weight
            })
        except PressMachine.DoesNotExist:
            return JsonResponse({'error': 'Machine not found'}, status=404)
        except EBR.DoesNotExist:
            return JsonResponse({'error': 'Batch not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def _check_ebr_param_deviation(batch, ebr_param):
    """Проверить отклонение одного параметра и создать Deviation если нужно."""
    from quality.models import Deviation

    try:
        nominal = EBRNominalParameter.objects.get(ebr=batch, parameter=ebr_param.parameter)
    except EBRNominalParameter.DoesNotExist:
        return

    if ebr_param.actual_value is None or float(nominal.nominal_value) == 0:
        return

    diff = abs(float(ebr_param.actual_value) - float(nominal.nominal_value))
    tol = float(nominal.tolerance_value)
    crit = float(nominal.critical_value)

    if crit > 0 and diff > crit:
        Deviation.objects.create(
            ebr=batch,
            deviation_type='critical',
            parameter_name=nominal.parameter.parameter_name,
            expected_value=nominal.nominal_value,
            actual_value=ebr_param.actual_value,
            tolerance=nominal.tolerance_value,
            description=f"Автоматическое обнаружение: {diff:.1f} > {crit:.1f}"
        )
        # max_value = NULL при критическом
        ebr_param.max_value = None
        ebr_param.save(update_fields=['max_value'])
    elif tol > 0 and diff > tol:
        Deviation.objects.create(
            ebr=batch,
            deviation_type='deviation',
            parameter_name=nominal.parameter.parameter_name,
            expected_value=nominal.nominal_value,
            actual_value=ebr_param.actual_value,
            tolerance=nominal.tolerance_value,
            description=f"Автоматическое обнаружение: {diff:.1f} > {tol:.1f}"
        )


def _check_deviations(reading, batch):
    """Проверить показания на отклонения относительно номинальных значений EBRNominalParameter."""
    from quality.models import Deviation

    ebr_params = EBRActualParameter.objects.filter(ebr=batch).select_related('parameter')

    for ebr_param in ebr_params:
        pname = ebr_param.parameter.parameter_name.lower()
        actual_value = None

        if 'усилие' in pname or 'force' in pname:
            actual_value = reading.pressure_force
        elif 'толщин' in pname or 'thick' in pname:
            actual_value = reading.tablet_thickness
        elif 'масс' in pname or 'weight' in pname:
            actual_value = reading.tablet_weight

        if actual_value is not None:
            ebr_param.actual_value = actual_value
            ebr_param.source = 'equipment'
            if ebr_param.max_value is None or actual_value > float(ebr_param.max_value):
                ebr_param.max_value = actual_value
            ebr_param.save(update_fields=['actual_value', 'max_value', 'source'])

        if actual_value is not None:
            try:
                nominal = EBRNominalParameter.objects.get(ebr=batch, parameter=ebr_param.parameter)
            except EBRNominalParameter.DoesNotExist:
                continue

            if float(nominal.nominal_value) == 0:
                continue

            diff = abs(float(actual_value) - float(nominal.nominal_value))
            tol = float(nominal.tolerance_value)
            crit = float(nominal.critical_value)

            if crit > 0 and diff > crit:
                Deviation.objects.create(
                    ebr=batch,
                    deviation_type='critical',
                    parameter_name=nominal.parameter.parameter_name,
                    expected_value=nominal.nominal_value,
                    actual_value=actual_value,
                    tolerance=nominal.tolerance_value,
                    description=f"Автоматическое обнаружение: {diff:.1f} > {crit:.1f}"
                )
                ebr_param.max_value = None
                ebr_param.save(update_fields=['max_value'])
                try:
                    blocked_status = EBRStatus.objects.get(status_name='Заблокирована')
                    batch.status = blocked_status
                    batch.save(update_fields=['status'])
                except EBRStatus.DoesNotExist:
                    pass
            elif tol > 0 and diff > tol:
                Deviation.objects.create(
                    ebr=batch,
                    deviation_type='deviation',
                    parameter_name=nominal.parameter.parameter_name,
                    expected_value=nominal.nominal_value,
                    actual_value=actual_value,
                    tolerance=nominal.tolerance_value,
                    description=f"Автоматическое обнаружение: {diff:.1f} > {tol:.1f}"
                )


def latest_readings(request):
    """Последние показания со всех прессов"""
    readings = EquipmentReading.objects.select_related('machine').order_by('-timestamp')[:20]
    data = []
    for r in readings:
        data.append({
            'machine': r.machine.machine_code,
            'batch_id': r.batch_id,
            'pressure_force': float(r.pressure_force),
            'tablet_thickness': float(r.tablet_thickness),
            'tablet_weight': float(r.tablet_weight),
            'timestamp': r.timestamp.isoformat()
        })
    return JsonResponse({'readings': data})
