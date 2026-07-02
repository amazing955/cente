from django.test import TestCase, Client
from django.urls import reverse
from inventory.models import CustomUser, Shipment, AuditLog, BankBranch


class ShipmentAutoFillTest(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create a branch
        self.branch = BankBranch.objects.create(
            branch_code='TEST001',
            branch_name='Test Branch',
            region='Central',
            district='Test District',
            address='123 Test St',
            status='Active'
        )
        
        # Create an Operations Manager user with full name and email
        self.user = CustomUser.objects.create_user(
            username='testops',
            email='testops@example.com',
            first_name='John',
            last_name='Doe',
            password='testpass123',
            role='operations_manager',  # Must be lowercase with underscore
            assigned_branch=self.branch
        )
    
    def test_shipment_form_autofills_requester_name(self):
        """Test that the shipment form auto-fills requester name from user's full name"""
        self.client.login(username='testops', password='testpass123')
        
        # Get the start shipment page
        response = self.client.get(reverse('start-shipment-request'))
        
        # Check the form is displayed with pre-filled requester name
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'John Doe')  # User's full name should be in the response
    
    def test_shipment_creation_logs_user_email(self):
        """Test that creating a shipment logs the user's email in the audit log"""
        self.client.login(username='testops', password='testpass123')
        
        # Submit shipment request
        response = self.client.post(
            reverse('start-shipment-request'),
            {
                'branch_name': self.branch.branch_name,
                'requester_name': 'John Doe',
                'request_details': 'Test shipment request',
            },
            follow=True
        )
        
        # Check we're redirected after successful submission
        self.assertEqual(response.status_code, 200)
        
        # Verify shipment was created
        shipment = Shipment.objects.filter(requesting_branch=self.branch).latest('shipment_date')
        self.assertIsNotNone(shipment)
        self.assertEqual(shipment.releasing_custodian, 'John Doe')
        
        # Verify audit log includes email
        audit_log = AuditLog.objects.filter(
            name='Shipment Created',
            message__contains=shipment.shipment_id
        ).latest('timestamp')
        
        self.assertIsNotNone(audit_log)
        self.assertIn('testops@example.com', audit_log.message)
        self.assertIn(shipment.shipment_id, audit_log.message)
        print(f"\n✓ Audit Log Message: {audit_log.message}")
    
    def test_shipment_fallback_to_username_if_no_requester_name(self):
        """Test that if requester_name is left blank, it falls back to user's full name"""
        self.client.login(username='testops', password='testpass123')
        
        # Submit shipment request with empty requester name (browser will auto-fill, but let's test the fallback)
        response = self.client.post(
            reverse('start-shipment-request'),
            {
                'branch_name': self.branch.branch_name,
                'requester_name': '',  # Empty - should use user's full name or username
                'request_details': 'Test shipment request',
            },
            follow=True
        )
        
        # Check we're redirected after successful submission
        self.assertEqual(response.status_code, 200)
        
        # Verify shipment was created with fallback name
        shipment = Shipment.objects.filter(requesting_branch=self.branch).latest('shipment_date')
        self.assertIsNotNone(shipment)
        # Should use user's full name as fallback
        self.assertIn('John', shipment.releasing_custodian)


if __name__ == '__main__':
    import django
    django.setup()
