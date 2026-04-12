from django.test import TestCase
from django.urls import reverse
from users.models import User
from mbr.models import Product, RawMaterial, Parameter, Document, DocumentType, MBR, MBRStatus
from ebr.models import EBR, EBRStatus, BatchOperation
from quality.models import QCTask, QCResult, Deviation
from audit.models import Action, AuditLog
import datetime


class UserAuthTestCase(TestCase):
    """Тесты аутентификации пользователей"""
    
    def setUp(self):
        self.admin_user = User.objects.create_user(
            login='admin_test',
            password='Admin123!',
            role='системный администратор',
            last_name='Admin',
            first_name='Test'
        )
        self.operator = User.objects.create_user(
            login='operator1',
            password='Oper1234!',
            role='оператор',
            last_name='Operator',
            first_name='Test'
        )
    
    def test_login_valid(self):
        """Тест успешного входа"""
        response = self.client.post(reverse('users:login'), {
            'login': 'admin_test',
            'password': 'Admin123!'
        })
        self.assertEqual(response.status_code, 302)  # Редирект после успеха
        self.assertIn('user_id', self.client.session)
    
    def test_login_invalid_credentials(self):
        """Тест входа с неверными данными"""
        response = self.client.post(reverse('users:login'), {
            'login': 'admin_test',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, 200)  # Остаёмся на странице входа
    
    def test_login_validation_short_login(self):
        """Тест валидации: короткий логин"""
        response = self.client.post(reverse('users:login'), {
            'login': 'short',
            'password': 'Admin123!'
        })
        self.assertEqual(response.status_code, 200)
    
    def test_logout(self):
        """Тест выхода из системы"""
        self.client.login(username='admin_test', password='Admin123!')
        response = self.client.get(reverse('users:logout'))
        self.assertEqual(response.status_code, 302)


class MBRTestCase(TestCase):
    """Тесты управления MBR"""
    
    def setUp(self):
        self.chief_tech = User.objects.create_user(
            login='chief_tech',
            password='Chief123!',
            role='главный технолог',
            last_name='Chief',
            first_name='Technologist'
        )
        self.product = Product.objects.create(
            product_name='Test Product',
            product_code='TP-001'
        )
        self.draft_status = MBRStatus.objects.create(status_name='Черновик')
        self.approved_status = MBRStatus.objects.create(status_name='Утверждён')
        self.doc_type = DocumentType.objects.create(type_name='MBR')
        self.document = Document.objects.create(type=self.doc_type)
    
    def test_mbr_creation(self):
        """Тест создания MBR"""
        self.client.force_login(self.chief_tech)
        
        mbr = MBR.objects.create(
            document=self.document,
            product=self.product,
            version='v1',
            status=self.draft_status,
            operations='Test operations',
            comments='Test comment'
        )
        
        self.assertEqual(mbr.product.product_code, 'TP-001')
        self.assertEqual(mbr.version, 'v1')
        self.assertEqual(mbr.status.status_name, 'Черновик')


class EBRTestCase(TestCase):
    """Тесты управления EBR"""
    
    def setUp(self):
        self.technologist = User.objects.create_user(
            login='tech_user',
            password='Tech1234!',
            role='технолог',
            last_name='Tech',
            first_name='User'
        )
        self.product = Product.objects.create(
            product_name='Test Product',
            product_code='TP-001'
        )
        self.approved_status = MBRStatus.objects.create(status_name='Утверждён')
        self.doc_type = DocumentType.objects.create(type_name='MBR')
        self.mbr_document = Document.objects.create(type=self.doc_type)
        
        self.mbr = MBR.objects.create(
            document=self.mbr_document,
            product=self.product,
            version='v1',
            status=self.approved_status,
            operations='Test operations'
        )
        
        self.ebr_status = EBRStatus.objects.create(status_name='В работе')
        self.ebr_doc_type = DocumentType.objects.create(type_name='EBR')
        self.ebr_document = Document.objects.create(type=self.ebr_doc_type)
    
    def test_ebr_creation_from_mbr(self):
        """Тест создания EBR из MBR"""
        ebr = EBR.objects.create(
            document=self.ebr_document,
            batch_number='B-TP-001-001',
            status=self.ebr_status,
            mbr=self.mbr,
            operator=self.technologist
        )
        
        self.assertEqual(ebr.batch_number, 'B-TP-001-001')
        self.assertEqual(ebr.status.status_name, 'В работе')
        self.assertEqual(ebr.mbr.product.product_code, 'TP-001')


class QualityControlTestCase(TestCase):
    """Тесты контроля качества"""
    
    def setUp(self):
        self.qc_specialist = User.objects.create_user(
            login='qc_spec',
            password='QC12345!',
            role='сотрудник ОКК',
            last_name='QC',
            first_name='Specialist'
        )
        
        # Создаём EBR для тестов
        self.product = Product.objects.create(product_name='Test', product_code='T-001')
        self.approved_status = MBRStatus.objects.create(status_name='Утверждён')
        self.doc_type = DocumentType.objects.create(type_name='MBR')
        self.mbr_doc = Document.objects.create(type=self.doc_type)
        self.mbr = MBR.objects.create(
            document=self.mbr_doc,
            product=self.product,
            version='v1',
            status=self.approved_status,
            operations='Test'
        )
        
        self.ebr_status = EBRStatus.objects.create(status_name='В работе')
        self.ebr_doc_type = DocumentType.objects.create(type_name='EBR')
        self.ebr_doc = Document.objects.create(type=self.ebr_doc_type)
        self.ebr = EBR.objects.create(
            document=self.ebr_doc,
            batch_number='B-TEST-001',
            status=self.ebr_status,
            mbr=self.mbr,
            operator=self.qc_specialist
        )
    
    def test_deviation_creation(self):
        """Тест создания отклонения"""
        deviation = Deviation.objects.create(
            ebr=self.ebr,
            deviation_type='critical',
            parameter_name='Усилие прессования',
            expected_value=50.0,
            actual_value=75.0,
            tolerance=10.0,
            description='Критическое отклонение',
            detected_by=self.qc_specialist
        )
        
        self.assertEqual(deviation.deviation_type, 'critical')
        self.assertEqual(deviation.parameter_name, 'Усилие прессования')


class AuditLogTestCase(TestCase):
    """Тесты журнали аудита"""
    
    def setUp(self):
        self.admin = User.objects.create_user(
            login='admin_audit',
            password='Audit1234!',
            role='системный администратор',
            last_name='Admin',
            first_name='Audit'
        )
        self.action = Action.objects.create(action_name='Вход в систему')
    
    def test_audit_log_creation(self):
        """Тест создания записи в журнале аудита"""
        log = AuditLog.objects.create(
            user=self.admin,
            action=self.action,
            comment='Тестовая запись'
        )
        
        self.assertEqual(log.user.login, 'admin_audit')
        self.assertEqual(log.action.action_name, 'Вход в систему')
        self.assertIsNotNone(log.timestamp)
