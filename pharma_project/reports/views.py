from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import HttpResponse
from .models import ReportTemplate, GeneratedReport, ProductionStats
from ebr.models import EBR
from quality.models import Deviation
import csv
import json
import datetime
import openpyxl
from openpyxl.styles import Font, Alignment


def report_list(request):
    if 'user_id' not in request.session or request.session.get('user_role') != 'директор':
        messages.error(request, 'Доступ только для директора')
        return redirect('dashboard')

    templates = ReportTemplate.objects.filter(is_active=True)
    recent_reports = GeneratedReport.objects.filter(
        generated_by=request.current_user
    ).order_by('-generated_at')[:20]

    context = {
        'user': request.current_user,
        'templates': templates,
        'recent_reports': recent_reports,
    }
    return render(request, 'reports/report_list.html', context)


def generate_report(request, report_type):
    if 'user_id' not in request.session or request.session.get('user_role') != 'директор':
        return redirect('login')

    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        format = request.POST.get('format', 'excel')

        # Преобразуем строки в даты
        start = datetime.datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.datetime.strptime(end_date, '%Y-%m-%d').date()

        template = ReportTemplate.objects.get(report_type=report_type)

        # Генерируем данные в зависимости от типа отчёта
        data = {}

        if report_type == 'production':
            # Отчёт по выпуску продукции
            ebrs = EBR.objects.filter(
                start_date__date__gte=start,
                start_date__date__lte=end,
                status__status_name='Завершена'
            ).select_related('mbr__product')

            products_data = {}
            total_units = 0
            total_defects = 0

            for ebr in ebrs:
                product_code = ebr.mbr.product.product_code
                if product_code not in products_data:
                    products_data[product_code] = {
                        'product_name': ebr.mbr.product.product_name,
                        'batches': 0,
                        'units': 0,
                        'defects': 0,
                        'raw_material': 0
                    }

                products_data[product_code]['batches'] += 1
                # Здесь должны быть реальные данные, пока заглушка
                products_data[product_code]['units'] += 100000
                products_data[product_code]['defects'] += 2000
                products_data[product_code]['raw_material'] += 50

                total_units += 100000
                total_defects += 2000

            data = {
                'start_date': start_date,
                'end_date': end_date,
                'products': products_data,
                'total_units': total_units,
                'total_defects': total_defects,
                'defect_percentage': (total_defects / total_units * 100) if total_units > 0 else 0
            }

        elif report_type == 'deviation':
            # Отчёт по отклонениям
            deviations = Deviation.objects.filter(
                detected_at__date__gte=start,
                detected_at__date__lte=end
            )

            types_count = {}
            for dev in deviations:
                if dev.deviation_type not in types_count:
                    types_count[dev.deviation_type] = 0
                types_count[dev.deviation_type] += 1

            data = {
                'start_date': start_date,
                'end_date': end_date,
                'total_deviations': deviations.count(),
                'by_type': types_count,
                'deviations': deviations[:50]  # последние 50
            }

        # Сохраняем отчёт
        report = GeneratedReport.objects.create(
            template=template,
            generated_by=request.current_user,
            start_date=start,
            end_date=end,
            format=format,
            data=data
        )

        # Генерируем файл
        if format == 'excel':
            return generate_excel_report(report, data, report_type)
        elif format == 'csv':
            return generate_csv_report(report, data, report_type)

        messages.success(request, 'Отчёт сгенерирован')
        return redirect('reports:report_list')

    return redirect('reports:report_list')


def generate_excel_report(report, data, report_type):
    """Генерирует Excel-файл отчёта"""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Отчёт"

    # Заголовок
    ws['A1'] = f"Отчёт по {report_type} за период {data['start_date']} - {data['end_date']}"
    ws['A1'].font = Font(bold=True, size=14)
    ws.merge_cells('A1:E1')

    if report_type == 'production':
        # Заголовки таблицы
        headers = ['Продукт', 'Количество партий', 'Выпущено единиц', 'Процент брака', 'Расход сырья (кг)']
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)

        # Данные
        row = 4
        for code, prod_data in data['products'].items():
            ws.cell(row=row, column=1, value=f"{code} - {prod_data['product_name']}")
            ws.cell(row=row, column=2, value=prod_data['batches'])
            ws.cell(row=row, column=3, value=prod_data['units'])
            defect_pct = prod_data['defects'] / prod_data['units'] * 100 if prod_data['units'] > 0 else 0
            ws.cell(row=row, column=4, value=f"{defect_pct:.1f}%")
            ws.cell(row=row, column=5, value=prod_data['raw_material'])
            row += 1

        # Итого
        ws.cell(row=row, column=1, value="ИТОГО").font = Font(bold=True)
        ws.cell(row=row, column=3, value=data['total_units']).font = Font(bold=True)
        ws.cell(row=row, column=4, value=f"{data['defect_percentage']:.1f}%").font = Font(bold=True)

    # Сохраняем
    filename = f"report_{report_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    filepath = f"media/reports/{filename}"
    wb.save(filepath)

    report.file = f"reports/{filename}"
    report.save()

    return redirect('reports:report_list')


def generate_csv_report(report, data, report_type):
    """Генерирует CSV-файл отчёта"""
    response = HttpResponse(content_type='text/csv')
    filename = f"report_{report_type}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([f"Отчёт по {report_type}", data['start_date'], data['end_date']])
    writer.writerow([])

    if report_type == 'production':
        writer.writerow(['Продукт', 'Количество партий', 'Выпущено единиц', 'Процент брака', 'Расход сырья (кг)'])
        for code, prod_data in data['products'].items():
            defect_pct = prod_data['defects'] / prod_data['units'] * 100 if prod_data['units'] > 0 else 0
            writer.writerow([
                f"{code} - {prod_data['product_name']}",
                prod_data['batches'],
                prod_data['units'],
                f"{defect_pct:.1f}%",
                prod_data['raw_material']
            ])

    return response


def download_report(request, report_id):
    if 'user_id' not in request.session:
        return redirect('login')

    report = get_object_or_404(GeneratedReport, id=report_id)

    if report.generated_by != request.current_user and request.session.get('user_role') != 'директор':
        messages.error(request, 'У вас нет доступа к этому отчёту')
        return redirect('reports:report_list')

    from django.http import FileResponse
    import os
    from django.conf import settings

    file_path = os.path.join(settings.MEDIA_ROOT, str(report.file))
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True, filename=os.path.basename(file_path))

    messages.error(request, 'Файл не найден')
    return redirect('reports:report_list')