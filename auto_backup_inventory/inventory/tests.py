from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Reconciliation, Shipment, Tape


class InventoryReportExportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='pass1234',
        )

    def test_custody_reports_page_renders_without_template_error(self):
        Shipment.objects.create(
            shipment_date=date(2026, 6, 15),
            shipment_type='Off-Site Transfer',
            source_location='Vault A',
            destination_location='Vault B',
            releasing_custodian='Alice',
            receiving_custodian='Bob',
            approval_remarks='Transfer approved',
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('backup-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'custody',
                'report_period': '2026-06',
                'report_type': 'monthly',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Previous Custodian')
        self.assertContains(response, 'Transfer Date')

    def test_reconciliation_reports_page_renders_with_table_controls(self):
        Reconciliation.objects.create(
            reconciliation_date=date(2026, 6, 15),
            location='Vault A',
            status='Completed',
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('backup-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'reconciliation',
                'report_period': '2026-06',
                'report_type': 'monthly',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Reconciliation ID')
        self.assertContains(response, 'Search')

    def test_inventory_reports_page_renders_without_template_error(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('backup-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Month')
        self.assertContains(response, 'Export CSV')

    def test_inventory_report_export_includes_selected_month_data(self):
        Tape.objects.create(
            volser='ABC123',
            barcode='BAR001',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Room A',
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('backup-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
                'export_csv': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, 'ABC123')
        self.assertContains(response, 'BAR001')
        self.assertContains(response, 'VolSER')

    def test_inventory_search_controls_are_scoped_to_inventory_table(self):
        Tape.objects.create(
            volser='ABC123',
            barcode='BAR001',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Room A',
        )
        Tape.objects.create(
            volser='XYZ999',
            barcode='BAR002',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Room B',
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('backup-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
                'report_search_inventory': 'ABC123',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ABC123')
        self.assertNotContains(response, 'XYZ999')

    def test_inventory_pdf_export_uses_scoped_export_flag(self):
        Tape.objects.create(
            volser='ABC123',
            barcode='BAR001',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Room A',
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('backup-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period_inventory': '2026-06',
                'report_type': 'monthly',
                'export_pdf_inventory': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')

    def test_inventory_excel_export_uses_scoped_export_flag(self):
        Tape.objects.create(
            volser='ABC123',
            barcode='BAR001',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Room A',
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('backup-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period_inventory': '2026-06',
                'report_type': 'monthly',
                'export_excel_inventory': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    def test_inventory_report_share_sends_email_for_selected_report(self):
        Tape.objects.create(
            volser='ABC123',
            barcode='BAR001',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Room A',
        )

        self.client.force_login(self.user)
        with patch('inventory.views.EmailMessage') as mock_email_cls:
            mock_instance = mock_email_cls.return_value
            mock_instance.send.return_value = 1

            response = self.client.get(
                reverse('backup-dashboard'),
                {
                    'show_reports': '1',
                    'report_category': 'inventory',
                    'report_period_inventory': '2026-06',
                    'report_type': 'monthly',
                    'share_report': '1',
                    'share_email': 'recipient@example.com',
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(mock_email_cls.called)
        self.assertEqual(mock_email_cls.call_args.args[2], self.user.email)
        self.assertEqual(mock_email_cls.call_args.args[3], ['recipient@example.com'])
        self.assertTrue(mock_instance.attach.called)
        mock_instance.send.assert_called_once_with(fail_silently=False)

    def test_inventory_report_share_handles_smtp_errors_without_500(self):
        Tape.objects.create(
            volser='ABC123',
            barcode='BAR001',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Room A',
        )

        self.client.force_login(self.user)
        with patch('inventory.views.EmailMessage') as mock_email_cls:
            mock_instance = mock_email_cls.return_value
            mock_instance.send.side_effect = Exception('Authentication Required')

            response = self.client.get(
                reverse('backup-dashboard'),
                {
                    'show_reports': '1',
                    'report_category': 'inventory',
                    'report_period_inventory': '2026-06',
                    'report_type': 'monthly',
                    'share_report': '1',
                    'share_email': 'recipient@example.com',
                },
            )

        self.assertEqual(response.status_code, 302)
        follow_response = self.client.get(response.url)
        self.assertContains(follow_response, 'Report sharing failed')
