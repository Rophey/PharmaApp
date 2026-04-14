import os, sys, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pharma_project.settings')
django.setup()

from mbr.models import MBR, MBRStatus, MBRParameter, DocumentType, Document, Product, Parameter
from users.models import User
import datetime

product = Product.objects.first()
print('Продукт:', product.product_code, product.product_name, flush=True)
params = list(Parameter.objects.all()[:3])
print('Параметры:', [p.parameter_name for p in params], flush=True)
user = User.objects.filter(role='главный технолог').first()
print('Главный технолог:', user.login if user else 'None', flush=True)

doc_type, _ = DocumentType.objects.get_or_create(type_name='MBR')
doc = Document.objects.create(type=doc_type)
approved = MBRStatus.objects.get(status_name='Утверждён')

mbr = MBR.objects.create(
    document=doc, product=product, version='v1',
    status=approved, operations='Прессование\nКонтроль',
    approval_date=datetime.date.today(), signed_by=user
)
for p in params:
    MBRParameter.objects.create(mbr=mbr, parameter=p, value=p.value, tolerance=p.tolerance, critical_deviation=p.critical_deviation)

print('MBR создан:', mbr.product.product_code, mbr.version, 'status=', mbr.status.status_name, flush=True)
print('Готово!', flush=True)
