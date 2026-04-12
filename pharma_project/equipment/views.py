from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from .models import PressMachine, EquipmentReading
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
    """Симулировать показания с оборудования (для тестирования)"""
    if request.method == 'POST':
        try:
            machine = PressMachine.objects.get(id=machine_id)
            
            # Генерируем случайные показания в пределах нормы
            pressure = round(random.uniform(40, 60), 2)  # кН
            thickness = round(random.uniform(4.5, 5.5), 2)  # мм
            weight = round(random.uniform(490, 510), 2)  # мг
            
            reading = EquipmentReading.objects.create(
                machine=machine,
                pressure_force=pressure,
                tablet_thickness=thickness,
                tablet_weight=weight
            )

            return JsonResponse({
                'success': True,
                'reading': {
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


@csrf_exempt
def send_reading(request, machine_id):
    """Получить показания от симулятора и сохранить в БД"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            machine = PressMachine.objects.get(id=machine_id)
            
            reading = EquipmentReading.objects.create(
                machine=machine,
                pressure_force=data.get('pressure_force'),
                tablet_thickness=data.get('tablet_thickness'),
                tablet_weight=data.get('tablet_weight')
            )

            # Проверка на отклонения если привязано к партии
            if reading.batch:
                from quality.models import Deviation
                from ebr.models import EBRParameter
                from mbr.models import Parameter
                
                # Получаем целевые параметры из MBR
                ebr_params = EBRParameter.objects.filter(ebr=reading.batch)
                for ebr_param in ebr_params:
                    param = ebr_param.parameter
                    actual_value = None
                    
                    # Определяем какой параметр проверять
                    if 'усилие' in param.parameter_name.lower() or 'force' in param.parameter_name.lower():
                        actual_value = reading.pressure_force
                    elif 'толщин' in param.parameter_name.lower() or 'thick' in param.parameter_name.lower():
                        actual_value = reading.tablet_thickness
                    elif 'масс' in param.parameter_name.lower() or 'weight' in param.parameter_name.lower():
                        actual_value = reading.tablet_weight
                    
                    if actual_value and param.value > 0:
                        diff_percent = abs((float(actual_value) - float(param.value)) / float(param.value) * 100)
                        
                        if diff_percent > float(param.critical_deviation):
                            Deviation.objects.create(
                                ebr=reading.batch,
                                deviation_type='critical',
                                parameter_name=param.parameter_name,
                                expected_value=param.value,
                                actual_value=actual_value,
                                tolerance=param.tolerance,
                                description=f"Автоматическое обнаружение: {diff_percent:.1f}%"
                            )
                        elif diff_percent > float(param.tolerance):
                            Deviation.objects.create(
                                ebr=reading.batch,
                                deviation_type='deviation',
                                parameter_name=param.parameter_name,
                                expected_value=param.value,
                                actual_value=actual_value,
                                tolerance=param.tolerance,
                                description=f"Автоматическое обнаружение: {diff_percent:.1f}%"
                            )

            return JsonResponse({'success': True, 'reading_id': reading.id})
        except PressMachine.DoesNotExist:
            return JsonResponse({'error': 'Machine not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def latest_readings(request):
    """Последние показания со всех прессов"""
    readings = EquipmentReading.objects.select_related('machine').order_by('-timestamp')[:20]
    data = []
    for r in readings:
        data.append({
            'machine': r.machine.machine_code,
            'pressure_force': float(r.pressure_force),
            'tablet_thickness': float(r.tablet_thickness),
            'tablet_weight': float(r.tablet_weight),
            'timestamp': r.timestamp.isoformat()
        })
    return JsonResponse({'readings': data})
