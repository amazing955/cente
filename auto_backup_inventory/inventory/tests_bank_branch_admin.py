from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from .models import BankBranch, BranchImportLog


class BankBranchAdminImportTests(TestCase):
    def test_superuser_can_upload_excel_and_import_branches(self):
        user = get_user_model().objects.create_superuser(
            username='branch-admin',
            email='branch-admin@example.com',
            password='pass1234',
        )
        BankBranch.objects.create(
            branch_code='BR-001',
            branch_name='Existing Branch',
            region='North',
            district='Nairobi',
            address='123 Main Street',
            status='Active',
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['Branch Code', 'Branch Name', 'Region', 'District', 'Address', 'Status'])
        sheet.append(['BR-001', 'Existing Branch Updated', 'North', 'Nairobi', '456 Main Street', 'Inactive'])
        sheet.append(['BR-002', 'New Branch', 'West', 'Mombasa', '789 Coast Road', 'Active'])

        excel_file = SimpleUploadedFile(
            'branches.xlsx',
            b'',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        excel_file.file = BytesIO()
        workbook.save(excel_file.file)
        excel_file.file.seek(0)
        excel_file.content = excel_file.file.getvalue()

        self.client.force_login(user)
        response = self.client.post(
            reverse('admin:inventory_bankbranch_upload_excel'),
            {'excel_file': excel_file},
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Import Preview')

        response = self.client.post(
            reverse('admin:inventory_bankbranch_preview_import'),
            {'confirm_import': '1'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(BankBranch.objects.filter(branch_code='BR-002').exists())
        updated_branch = BankBranch.objects.get(branch_code='BR-001')
        self.assertEqual(updated_branch.branch_name, 'Existing Branch Updated')
        self.assertEqual(updated_branch.status, 'Inactive')
        self.assertTrue(BranchImportLog.objects.exists())
