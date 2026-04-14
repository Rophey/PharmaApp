import os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharma_project.settings')
import django
django.setup()

from ebr.models import EBR, EBRStatus

print('=== EBRStatus ===', flush=True)
for s in EBRStatus.objects.all():
    print(f'  id={s.pk} name={repr(s.status_name)}', flush=True)

print(f'\n=== EBR count: {EBR.objects.count()} ===', flush=True)
for ebr in EBR.objects.all()[:10]:
    print(f'  batch={ebr.batch_number} status={repr(ebr.status.status_name)} op={ebr.operator_id}', flush=True)

print('\n=== Query test ===', flush=True)
q = EBR.objects.filter(status__status_name='В ожидании', operator__isnull=True)
print(f'  waiting_ebrs count: {q.count()}', flush=True)
for e in q:
    print(f'  -> {e.batch_number}', flush=True)
