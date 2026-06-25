from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from openpyxl import Workbook

from .models import Reconciliation, Shipment, Tape, TapeRequest


class AuditorDashboardTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='IT Compliance Auditor')
        self.user = get_user_model().objects.create_user(
            username='auditor',
            email='auditor@example.com',
            password='pass1234',
        )
        self.user.groups.add(self.group)

    def test_auditor_dashboard_renders_read_only_compliance_sections(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse('auditor-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'IT Compliance Auditor')
        self.assertContains(response, 'Compliance Health')
        self.assertContains(response, 'Audit Trail Review')
        self.assertContains(response, 'Read-only view')

    def test_user_with_auditor_role_can_access_dashboard(self):
        role_user = get_user_model().objects.create_user(
            username='auditor-role',
            email='auditor-role@example.com',
            password='pass1234',
            role='auditor',
        )
        self.client.force_login(role_user)
        response = self.client.get(reverse('auditor-dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_auditor_reports_page_renders_report_module(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('auditor-reports'),
            {
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report types')
        self.assertContains(response, 'Export CSV')

    def test_reports_load_inside_dashboard_when_requested(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('auditor-dashboard'),
            {
                'view': 'reports',
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compliance Reports')
        self.assertContains(response, 'Report types')
        self.assertContains(response, 'Export CSV')
        self.assertContains(response, 'Compliance Health')
        self.assertContains(response, 'Audit Trail Review')

    def test_auditor_sections_render_inside_dashboard_shell(self):
        self.client.force_login(self.user)
        cases = [
            ('exceptions', 'Exception Review'),
            ('shipments', 'Shipment Compliance Review'),
            ('retention', 'Retention Compliance Review'),
            ('reconciliation', 'Reconciliation Review'),
        ]

        for view_name, expected_text in cases:
            with self.subTest(view=view_name):
                response = self.client.get(reverse('auditor-dashboard'), {'view': view_name})
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, expected_text)
                self.assertContains(response, 'IT Compliance Auditor Dashboard')

    def test_user_with_auditor_group_name_can_access_dashboard(self):
        group = Group.objects.create(name='Auditor')
        group_user = get_user_model().objects.create_user(
            username='auditor-group',
            email='auditor-group@example.com',
            password='pass1234',
        )
        group_user.groups.add(group)
        self.client.force_login(group_user)
        response = self.client.get(reverse('auditor-dashboard'))

        self.assertEqual(response.status_code, 200)

    def test_auditor_can_submit_pending_shipment_request(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('auditor-dashboard'),
            {
                'form_type': 'submit_shipment_request',
                'branch_name': 'Nairobi Branch',
                'request_details': 'Need secure transfer for tape inventory.',
            },
        )

        self.assertEqual(response.status_code, 302)
        shipment = Shipment.objects.get(created_by=self.user)
        self.assertEqual(shipment.status, 'Pending')
        self.assertEqual(shipment.source_location, 'Nairobi Branch')
        self.assertEqual(shipment.approval_remarks, 'Need secure transfer for tape inventory.')
        self.assertEqual(shipment.created_by, self.user)


class ShipmentFormTests(TestCase):
    def test_add_shipment_form_prefills_releasing_custodian_with_current_user(self):
        backup_group = Group.objects.create(name='Backup Administrator')
        user = get_user_model().objects.create_user(
            username='backup-admin',
            email='backup-admin@example.com',
            password='pass1234',
            first_name='Jane',
            last_name='Doe',
        )
        user.groups.add(backup_group)

        self.client.force_login(user)
        response = self.client.get(reverse('backup-dashboard'), {'show_add_shipment': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Jane Doe')


class TapeRequestWorkflowTests(TestCase):
    def test_operator_request_can_be_approved_into_a_shipment(self):
        operations_group = Group.objects.create(name='Operations Manager')
        backup_group = Group.objects.create(name='Backup Administrator')
        operator = get_user_model().objects.create_user(
            username='operator-one',
            email='operator-one@example.com',
            password='pass1234',
            first_name='Op',
            last_name='User',
        )
        operator.groups.add(operations_group)
        backup_admin = get_user_model().objects.create_user(
            username='backup-admin',
            email='backup-admin@example.com',
            password='pass1234',
            first_name='Backup',
            last_name='Admin',
        )
        backup_admin.groups.add(backup_group)
        tape = Tape.objects.create(
            volser='TAPE-100',
            barcode='BAR-100',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Vault A',
        )

        self.client.force_login(operator)
        response = self.client.post(
            reverse('operations-dashboard'),
            {
                'form_type': 'submit_tape_request',
                'tape': tape.pk,
                'quantity': 1,
                'destination_location': 'DR Site',
                'receiving_organization': 'Ops Team',
                'reason': 'Need this tape for a scheduled restore.',
            },
        )

        self.assertEqual(response.status_code, 302)
        request = TapeRequest.objects.get(requested_by=operator)
        self.assertEqual(request.status, 'Pending')

        self.client.force_login(backup_admin)
        response = self.client.post(
            reverse('backup-dashboard'),
            {
                'form_type': 'approve_tape_request',
                'request_id': request.pk,
                'approval_notes': 'Approved for immediate handoff.',
            },
        )

        self.assertEqual(response.status_code, 302)
        request.refresh_from_db()
        self.assertEqual(request.status, 'Approved')
        self.assertTrue(request.shipment_id is not None)
        shipment = Shipment.objects.get(pk=request.shipment_id)
        self.assertEqual(shipment.status, 'Approved')
        self.assertEqual(shipment.destination_location, 'DR Site')
        self.assertEqual(shipment.number_of_tapes, 1)


class OperationsDashboardShipmentRequestTests(TestCase):
    def test_operations_dashboard_can_submit_pending_shipment_request(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='ops-requestor',
            email='ops-requestor@example.com',
            password='pass1234',
            first_name='Op',
            last_name='User',
        )
        user.groups.add(group)

        self.client.force_login(user)
        response = self.client.post(
            reverse('operations-dashboard'),
            {
                'form_type': 'submit_shipment_request',
                'branch_name': 'Mombasa Branch',
                'request_details': 'Please arrange a secure shipment for backup tapes.',
            },
        )

        self.assertEqual(response.status_code, 302)
        shipment = Shipment.objects.get(created_by=user)
        self.assertEqual(shipment.status, 'Pending')
        self.assertEqual(shipment.source_location, 'Mombasa Branch')
        self.assertEqual(shipment.approval_remarks, 'Please arrange a secure shipment for backup tapes.')


class OperationsDashboardReportsTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='Operations Manager')
        self.user = get_user_model().objects.create_user(
            username='ops-reports',
            email='ops-reports@example.com',
            password='pass1234',
        )
        self.user.groups.add(self.group)

    def test_operations_dashboard_reports_panel_uses_shared_report_module(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('operations-dashboard'),
            {
                'show_reports': '1',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report types')
        self.assertContains(response, 'Export CSV')

    def test_operations_dashboard_inventory_report_search_filters_table_rows(self):
        Tape.objects.create(
            volser='TAPE-100',
            barcode='BAR-100',
            tape_type='LTO-8',
            status='Active',
            current_location='Vault A',
            retention_end_date=date(2030, 1, 1),
        )
        Tape.objects.create(
            volser='TAPE-200',
            barcode='BAR-200',
            tape_type='LTO-8',
            status='Active',
            current_location='Vault B',
            retention_end_date=date(2030, 1, 1),
        )

        self.client.force_login(self.user)
        response = self.client.get(
            reverse('operations-dashboard'),
            {
                'show_reports': 'reports',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
                'report_search_inventory': 'TAPE-100',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TAPE-100')
        self.assertNotContains(response, 'TAPE-200')

    def test_operations_dashboard_report_only_view_renders_report_table_without_full_dashboard(self):
        self.client.force_login(self.user)
        response = self.client.get(
            reverse('operations-dashboard'),
            {
                'show_reports': 'reports',
                'report_category': 'inventory',
                'report_period': '2026-06',
                'report_type': 'monthly',
                'report_only': '1',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Report types')
        self.assertContains(response, 'Inventory Report')
        self.assertContains(response, 'showReportsPanel();')


class ShipmentOperationsWorkflowTests(TestCase):
    def test_operations_manager_can_receive_tapes_and_mark_shipment_completed(self):
        operations_group = Group.objects.create(name='Operations Manager')
        operator = get_user_model().objects.create_user(
            username='ops-complete',
            email='ops-complete@example.com',
            password='pass1234',
            first_name='Ops',
            last_name='User',
        )
        operator.groups.add(operations_group)
        shipment = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            source_location='Vault A',
            destination_location='DR Site',
            receiving_organization='Ops Team',
            status='Approved',
            priority_level='High',
            releasing_custodian='Jane Doe',
        )

        self.client.force_login(operator)
        response = self.client.post(
            reverse('shipment-detail', args=[shipment.pk]),
            {
                'form_type': 'operator_receipt_completion',
                'receiving_custodian': 'Ops User',
                'receipt_notes': 'Tapes received and verified at the receiving site.',
            },
        )

        self.assertEqual(response.status_code, 200)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, 'Completed')
        self.assertEqual(shipment.received_by, 'Ops User')
        self.assertEqual(shipment.delivery_status, 'Delivered')
        self.assertEqual(shipment.delivery_notes, 'Tapes received and verified at the receiving site.')


class InventoryImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username='admin-import',
            email='admin-import@example.com',
            password='pass1234',
        )

    def test_excel_upload_creates_or_updates_tape_records(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.title = 'Inventory'
        sheet.append(['volser', 'barcode', 'tape_type', 'status', 'current_location', 'retention_end_date', 'manufacturer'])
        sheet.append(['ABC123', 'BAR001', 'LTO-8', 'Active', 'Room A', '2030-01-01', 'IBM'])
        sheet.append(['XYZ999', 'BAR002', 'LTO-9', 'Damaged', 'Room B', '2029-12-31', 'Quantum'])

        buffer = BytesIO()
        workbook.save(buffer)
        buffer.seek(0)

        self.client.force_login(self.user)
        response = self.client.post(
            reverse('backup-dashboard'),
            {
                'form_type': 'upload_inventory_excel',
                'inventory_file': SimpleUploadedFile('inventory.xlsx', buffer.getvalue(), content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Tape.objects.filter(volser='ABC123', barcode='BAR001').exists())
        self.assertTrue(Tape.objects.filter(volser='XYZ999', barcode='BAR002').exists())


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

    def test_inventory_report_export_accepts_non_numeric_export_flag(self):
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
                'show_reports': 'reports',
                'report_category': 'inventory',
                'report_period_inventory': '2026-06',
                'report_type': 'monthly',
                'export_csv_inventory': 'csv',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertContains(response, 'ABC123')

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
