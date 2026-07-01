import json
from datetime import date
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.http import HttpResponseForbidden
from django.test import RequestFactory, TestCase, override_settings
from django.urls import path, reverse
from openpyxl import Workbook

from .forms import BackupShipmentAssignmentForm, RoleCreationForm
from .models import (
    ApplicationSetting,
    AuditLog,
    CourierProfile,
    DashboardFeatureExemption,
    DashboardFeaturePermission,
    DeliveryConfirmation,
    Reconciliation,
    Shipment,
    ShipmentApprovalHistory,
    ShipmentReceipt,
    ShipmentTransportEvent,
    Tape,
    TapeRequest,
    SchemaChangeLog,
    get_dashboard_feature_catalog,
)
from .serializer import TapeSerializer
from .views import custom_permission_denied, is_backup_administrator, is_operations_manager


def forbidden_view(request):
    return HttpResponseForbidden('Forbidden')


urlpatterns = [
    path('protected-page/', forbidden_view),
]


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

    @override_settings(ROOT_URLCONF='inventory.tests')
    def test_custom_permission_denied_view_uses_403_template(self):
        response = self.client.get('/protected-page/')

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, 'Access denied', status_code=403)
        self.assertContains(response, 'Return home', status_code=403)

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

    def test_audit_logs_render_inside_auditor_dashboard(self):
        self.client.force_login(self.user)
        AuditLog.objects.create(
            name='System',
            action='Tape inventory reconciliation completed',
            user=self.user,
            severity='info',
        )

        response = self.client.get(reverse('auditor-dashboard'), {'view': 'audit-logs'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tape inventory reconciliation completed')
        self.assertContains(response, 'Audit Trail Review')

    def test_audit_logs_filter_form_submits_audit_logs_view_param(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('auditor-dashboard'), {'view': 'audit-logs'})

        self.assertContains(response, 'name="view"')
        self.assertContains(response, 'value="audit-logs"')

    def test_unknown_page_uses_custom_404_template(self):
        response = self.client.get('/definitely-not-a-real-page/')

        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Page not found', status_code=404)
        self.assertContains(response, 'Return home', status_code=404)

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


class BackupDashboardSettingsTests(TestCase):
    def test_backup_dashboard_settings_save_reconciliation_schedule(self):
        user = get_user_model().objects.create_superuser(
            username='backup-settings-admin',
            email='backup-settings-admin@example.com',
            password='pass1234',
        )
        application_settings = ApplicationSetting.objects.create()

        self.client.force_login(user)
        response = self.client.post(
            reverse('backup-dashboard'),
            {
                'form_type': 'system_settings',
                'backup_retention_days': '180',
                'shipment_notification_enabled': 'on',
                'email_alerts_enabled': 'on',
                'allow_offsite_transfers': 'on',
                'max_tapes_per_shipment': '60',
                'audit_logging_level': 'warning',
                'audit_retention_years': '8',
                'default_dashboard_section': 'reports',
                'maintenance_window_start': '02:00',
                'maintenance_window_end': '04:00',
                'next_reconciliation_date': '2026-08-15',
                'reconciliation_alert_start_days_before': '5',
                'reconciliation_alert_duration_days': '10',
            },
        )

        self.assertEqual(response.status_code, 302)
        application_settings.refresh_from_db()
        self.assertEqual(application_settings.next_reconciliation_date, date(2026, 8, 15))
        self.assertEqual(application_settings.reconciliation_alert_start_days_before, 5)
        self.assertEqual(application_settings.reconciliation_alert_duration_days, 10)


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


class ExcelSchemaSynchronizationTests(TestCase):
    def test_uploading_excel_with_new_columns_shows_schema_preview(self):
        user = get_user_model().objects.create_superuser(
            username='excel-preview-admin',
            email='excel-preview-admin@example.com',
            password='pass1234',
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['volser', 'barcode', 'tape_type', 'status', 'current_location', 'retention_end_date', 'manufacturer', 'RFID Tag', 'Vault Number'])
        sheet.append(['TAPE-001', 'BC-001', 'LTO-8', 'Active', 'Vault A', '2026-12-31', 'IBM', 'RFID-001', 'V1'])

        excel_file = SimpleUploadedFile(
            'inventory_template.xlsx',
            b'',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        excel_file.file = BytesIO()
        workbook.save(excel_file.file)
        excel_file.file.seek(0)
        excel_file.content = excel_file.file.getvalue()

        self.client.force_login(user)
        response = self.client.post(
            reverse('backup-dashboard'),
            {'form_type': 'upload_inventory_excel', 'inventory_file': excel_file},
            format='multipart',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('schema_preview', response.context)
        self.assertEqual(response.context['schema_preview']['table_name'], 'inventory_tape')
        self.assertEqual(len(response.context['schema_preview']['new_columns']), 2)
        self.assertContains(response, 'Schema Synchronization Preview')
        self.assertContains(response, 'Approve & Synchronize')

    def test_approving_schema_sync_adds_columns_and_imports_rows(self):
        user = get_user_model().objects.create_superuser(
            username='excel-sync-admin',
            email='excel-sync-admin@example.com',
            password='pass1234',
        )

        workbook = Workbook()
        sheet = workbook.active
        sheet.append(['volser', 'barcode', 'tape_type', 'status', 'current_location', 'retention_end_date', 'manufacturer', 'RFID Tag', 'Vault Number'])
        sheet.append(['TAPE-100', 'BC-100', 'LTO-8', 'Active', 'Vault A', '2026-12-31', 'IBM', 'RFID-100', 'V2'])

        excel_file = SimpleUploadedFile(
            'inventory_template.xlsx',
            b'',
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        excel_file.file = BytesIO()
        workbook.save(excel_file.file)
        excel_file.file.seek(0)
        excel_file.content = excel_file.file.getvalue()

        self.client.force_login(user)
        self.client.post(
            reverse('backup-dashboard'),
            {'form_type': 'upload_inventory_excel', 'inventory_file': excel_file},
            format='multipart',
        )

        response = self.client.post(
            reverse('backup-dashboard'),
            {'form_type': 'approve_excel_schema_sync'},
        )

        self.assertEqual(response.status_code, 302)
        with connection.cursor() as cursor:
            columns = [column[1] for column in connection.introspection.get_columns(cursor, 'inventory_tape')]
        self.assertIn('rfid_tag', columns)
        self.assertIn('vault_number', columns)
        self.assertTrue(SchemaChangeLog.objects.filter(status='applied').exists())
        self.assertTrue(Tape.objects.filter(volser='TAPE-100').exists())


class DashboardFeatureNavigationTests(TestCase):
    def test_role_form_includes_django_admin_permissions_as_assignable_features(self):
        content_type = ContentType.objects.get(app_label='inventory', model='tape')
        permission = Permission.objects.get(content_type=content_type, codename='view_tape')

        form = RoleCreationForm()
        feature_choices = dict(form.fields['features'].choices)

        self.assertIn(f'{permission.content_type.app_label}.{permission.codename}', feature_choices)

    def test_dashboard_context_processor_exposes_permitted_features(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='nav-user',
            email='nav-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='operations_dashboard', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('operations-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(any(entry['key'] == 'operations_dashboard' for entry in response.context['dashboard_features']))

    def test_dashboard_context_processor_exposes_api_navigation_urls_for_permitted_features(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='nav-api-user',
            email='nav-api-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='operations_dashboard', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('operations-dashboard'))

        self.assertEqual(response.status_code, 200)
        entry = next((item for item in response.context['dashboard_features'] if item['key'] == 'operations_dashboard'), None)
        self.assertIsNotNone(entry)
        self.assertIn('api_url', entry)
        self.assertEqual(entry['api_url'], reverse('api-feature-navigation', kwargs={'feature_key': 'operations_dashboard'}))

    def test_dashboard_feature_exemptions_hide_feature_for_individual_user(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='nav-exempt',
            email='nav-exempt@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='operations_dashboard', can_view=True)
        DashboardFeatureExemption.objects.create(user=user, feature_key='operations_dashboard', is_active=True, reason='Temporary exemption')

        self.client.force_login(user)
        response = self.client.get(reverse('operations-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertFalse(any(entry['key'] == 'operations_dashboard' for entry in response.context['dashboard_features']))

    def test_feature_catalog_uses_feature_module_routes_instead_of_dashboard_urls(self):
        features = get_dashboard_feature_catalog()

        self.assertTrue(features)
        for feature in features:
            self.assertEqual(feature['url_name'], 'feature-module')
            self.assertEqual(feature['url_kwargs']['feature_key'], feature['key'])

    def test_feature_navigation_api_returns_standalone_page_payload_for_features(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='nav-fragment-user',
            email='nav-fragment-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='shipment_approvals', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('api-feature-navigation', kwargs={'feature_key': 'shipment_approvals'}))

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload['load_mode'], 'page')
        self.assertIn(reverse('feature-module', kwargs={'feature_key': 'shipment_approvals'}), payload['target_url'])
        self.assertNotIn('partial=1', payload['target_url'])
        self.assertIn('partial=1', payload['fragment_url'])

    def test_feature_permission_does_not_confer_backup_admin_role(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='feature-role-ops',
            email='feature-role-ops@example.com',
            password='pass1234',
        )
        user.groups.add(group)
        DashboardFeaturePermission.objects.create(role=group, feature_key='tape_inventory', can_view=True)

        self.assertTrue(is_operations_manager(user))
        self.assertFalse(is_backup_administrator(user))

    def test_feature_page_hides_sidebar_when_feature_key_is_present(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='feature-page-sidebar-user',
            email='feature-page-sidebar-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        self.client.force_login(user)
        response = self.client.get(reverse('shipment-approvals'), {'feature_key': 'shipment_approvals'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'class="app-sidebar')
        self.assertNotContains(response, 'id="sidebarPanel"')

    def test_feature_permission_does_not_grant_dashboard_access_for_custom_group_name(self):
        group = Group.objects.create(name='Warehouse Ops')
        user = get_user_model().objects.create_user(
            username='custom-group-user',
            email='custom-group-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='operations_dashboard', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('operations-dashboard'))

        self.assertEqual(response.status_code, 302)

    def test_feature_module_allows_feature_access_without_dashboard_role(self):
        group = Group.objects.create(name='Warehouse Ops')
        user = get_user_model().objects.create_user(
            username='feature-module-user',
            email='feature-module-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='shipment_approvals', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('feature-module', kwargs={'feature_key': 'shipment_approvals'}))

        self.assertEqual(response.status_code, 200)

    def test_feature_module_renders_backup_feature_without_dashboard_sidebar(self):
        group = Group.objects.create(name='Backup Administrator')
        user = get_user_model().objects.create_user(
            username='backup-feature-shell-user',
            email='backup-feature-shell-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='tape_inventory', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('feature-module', kwargs={'feature_key': 'tape_inventory'}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Back to dashboard')
        self.assertNotContains(response, 'class="sidebar"')
        self.assertEqual(response.context['active_feature_key'], 'tape_inventory')

    def test_feature_link_opens_selected_section_inside_backup_dashboard(self):
        group = Group.objects.create(name='Backup Administrator')
        user = get_user_model().objects.create_user(
            username='backup-feature-user',
            email='backup-feature-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='tape_inventory', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('backup-dashboard'), {'feature_key': 'tape_inventory'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_tape_inventory_panel'])
        self.assertEqual(response.context['active_feature_key'], 'tape_inventory')

    def test_feature_link_opens_selected_section_inside_operations_dashboard(self):
        group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='operations-feature-user',
            email='operations-feature-user@example.com',
            password='pass1234',
        )
        user.groups.add(group)

        DashboardFeaturePermission.objects.create(role=group, feature_key='exception_management', can_view=True)

        self.client.force_login(user)
        response = self.client.get(reverse('operations-dashboard'), {'feature_key': 'exception_management'})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['show_exception_panel'])
        self.assertEqual(response.context['active_feature_key'], 'exception_management')


class ApiEndpointTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='api-user',
            email='api-user@example.com',
            password='pass1234',
        )
        self.client.force_login(self.user)

    def test_dashboard_summary_api_returns_counts(self):
        Tape.objects.create(
            volser='TAPE-001',
            barcode='BAR-001',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
        )
        Shipment.objects.create(
            shipment_id='SHP-1001',
            source_location='HQ',
            destination_location='DR',
            shipment_type='Off-Site Transfer',
            priority_level='Normal',
            status='Pending',
            created_by=self.user,
        )
        AuditLog.objects.create(
            name='System',
            action='API endpoint tested',
            user=self.user,
            severity='info',
        )

        response = self.client.get('/api/dashboard-summary/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['tape_count'], 1)
        self.assertEqual(response.json()['shipment_count'], 1)
        self.assertEqual(response.json()['audit_log_count'], 1)

    def test_tape_list_api_returns_tape_payload(self):
        Tape.objects.create(
            volser='TAPE-002',
            barcode='BAR-002',
            tape_type='LTO-9',
            retention_end_date=date(2031, 1, 1),
        )

        response = self.client.get('/api/tapes/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['volser'], 'TAPE-002')

    def test_tape_serializer_returns_expected_fields(self):
        tape = Tape.objects.create(
            volser='TAPE-003',
            barcode='BAR-003',
            tape_type='LTO-8',
            retention_end_date=date(2032, 1, 1),
            status='Active',
            current_location='Vault A',
        )

        payload = TapeSerializer(tape).data

        self.assertEqual(payload['volser'], 'TAPE-003')
        self.assertEqual(payload['status'], 'Active')
        self.assertEqual(payload['location'], 'Vault A')

    def test_tape_creation_via_api_returns_created_payload(self):
        response = self.client.post(
            '/api/tapes/',
            json.dumps({
                'volser': 'TAPE-004',
                'tape_type': 'LTO-8',
                'retention_end_date': '2035-01-01',
                'current_location': 'Vault B',
                'status': 'Active',
            }),
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Tape.objects.count(), 1)
        self.assertEqual(response.json()['result']['volser'], 'TAPE-004')

    def test_shipments_api_returns_collection(self):
        Shipment.objects.create(
            shipment_id='SHP-2001',
            source_location='HQ',
            destination_location='DR',
            shipment_type='Off-Site Transfer',
            priority_level='Normal',
            status='Pending',
            created_by=self.user,
        )

        response = self.client.get('/api/shipments/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['shipment_id'], 'SHP-2001')

    def test_audit_logs_api_returns_collection(self):
        AuditLog.objects.create(
            name='System',
            action='Audit log fetched through API',
            user=self.user,
            severity='info',
        )

        response = self.client.get('/api/audit-logs/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['count'], 1)
        self.assertEqual(response.json()['results'][0]['action'], 'Audit log fetched through API')


class TapeStatusProtectionTests(TestCase):
    def test_scratch_status_change_is_rejected_for_tape_on_legal_hold(self):
        backup_group = Group.objects.create(name='Backup Administrator')
        backup_admin = get_user_model().objects.create_user(
            username='backup-admin-protect',
            email='backup-admin-protect@example.com',
            password='pass1234',
        )
        backup_admin.groups.add(backup_group)
        tape = Tape.objects.create(
            volser='TAPE-200',
            barcode='BAR-200',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Vault A',
            legal_hold=True,
        )

        self.client.force_login(backup_admin)
        response = self.client.post(
            reverse('backup-dashboard'),
            {
                'form_type': 'tape_action',
                'selected_tape': tape.pk,
                'action': 'edit_details',
                'volser': tape.volser,
                'barcode': tape.barcode,
                'current_location': tape.current_location,
                'retention_end_date': '2030-01-01',
                'status': 'Scratch Eligible',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Cannot mark tape as Scratch')
        tape.refresh_from_db()
        self.assertEqual(tape.status, 'Active')


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


class ShipmentWorkflowTests(TestCase):
    def test_start_shipment_request_renders_embedded_fragment_when_requested_partially(self):
        operations_group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='operator-fragment',
            email='operator-fragment@example.com',
            password='pass1234',
        )
        user.groups.add(operations_group)

        self.client.force_login(user)
        response = self.client.get(reverse('start-shipment-request'), {'partial': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'start_shipment_request_fragment.html')
        self.assertContains(response, 'Start a shipment request')
        self.assertNotContains(response, '<!DOCTYPE html>')

    def test_operator_shipment_request_stores_branch_name_as_destination(self):
        operations_group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='operator-destination',
            email='operator-destination@example.com',
            password='pass1234',
        )
        user.groups.add(operations_group)

        self.client.force_login(user)
        response = self.client.post(
            reverse('operations-dashboard'),
            {
                'form_type': 'submit_shipment_request',
                'branch_name': 'Nairobi Branch',
                'requester_name': 'Operator One',
                'request_details': 'Move tapes to Nairobi Branch.',
            },
        )

        self.assertEqual(response.status_code, 302)
        shipment = Shipment.objects.get(created_by=user)
        self.assertEqual(shipment.destination_location, 'Nairobi Branch')

    def test_operator_shipment_request_flow_reaches_courier_acceptance(self):
        operations_group = Group.objects.create(name='Operations Manager')
        backup_group = Group.objects.create(name='Backup Administrator')
        courier_group = Group.objects.create(name='Courier')

        operator = get_user_model().objects.create_user(
            username='operator-flow',
            email='operator-flow@example.com',
            password='pass1234',
            first_name='Op',
            last_name='User',
        )
        operator.groups.add(operations_group)

        backup_admin = get_user_model().objects.create_user(
            username='backup-flow',
            email='backup-flow@example.com',
            password='pass1234',
            first_name='Backup',
            last_name='Admin',
        )
        backup_admin.groups.add(backup_group)

        courier_user = get_user_model().objects.create_user(
            username='courier-flow',
            email='courier-flow@example.com',
            password='pass1234',
            first_name='Courier',
            last_name='Guy',
        )
        courier_user.groups.add(courier_group)
        courier_profile = CourierProfile.objects.create(
            user=courier_user,
            courier_id='CR-100',
            full_name='Courier Guy',
            phone_number='555-1000',
            email='courier-flow@example.com',
        )

        tape = Tape.objects.create(
            volser='TAPE-900',
            barcode='BAR-900',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Vault A',
        )

        self.client.force_login(operator)
        response = self.client.post(
            reverse('operations-dashboard'),
            {
                'form_type': 'submit_shipment_request',
                'branch_name': 'Nairobi Branch',
                'request_details': 'Need transfer of tapes to DR site.',
            },
        )

        self.assertEqual(response.status_code, 302)
        shipment = Shipment.objects.get(created_by=operator)
        self.assertEqual(shipment.status, 'Pending')
        self.assertEqual(shipment.source_location, 'Nairobi Branch')

        self.client.force_login(backup_admin)
        response = self.client.post(
            reverse('shipment-approvals'),
            {
                'form_type': 'backup_admin_decision',
                'shipment_id': shipment.pk,
                'tape_id': tape.pk,
                'courier_id': courier_profile.pk,
                'decision': 'approve',
                'comments': 'Approved for dispatch.',
            },
        )

        shipment.refresh_from_db()
        self.assertEqual(shipment.status, 'Approved')
        self.assertEqual(shipment.tapes.count(), 1)
        self.assertEqual(shipment.courier_name, 'Courier Guy')

        self.client.force_login(courier_user)
        response = self.client.post(
            reverse('pickup-confirmation', args=[shipment.pk]),
            {
                'manifest_reference': 'MANIFEST-1',
                'pickup_date': '2026-06-26',
                'pickup_time': '09:00',
                'pickup_location': 'Vault A',
                'notes': 'Pickup confirmed',
                'all_tapes_scanned': 'on',
                'manifest_verified': 'on',
                'tape_count_matched': 'on',
                'no_damaged_tapes': 'on',
                'custody_accepted': 'on',
            },
        )

        shipment.refresh_from_db()
        self.assertEqual(shipment.status, 'Picked Up')




class OperationsDashboardCustodyGovernanceTests(TestCase):
    def test_custody_governance_cards_use_receipt_and_delivery_records(self):
        operations_group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='ops-custody-metrics',
            email='ops-custody-metrics@example.com',
            password='pass1234',
        )
        user.groups.add(operations_group)

        courier = CourierProfile.objects.create(
            courier_id='CR-200',
            full_name='Test Courier',
            email='courier@example.com',
        )

        open_transfer = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            status='Picked Up',
            source_location='Vault A',
            destination_location='Nairobi Branch',
            created_by=user,
        )
        ShipmentReceipt.objects.create(
            shipment=open_transfer,
            courier=courier,
            pickup_location='Vault A',
            custody_confirmed=True,
            custody_accepted=True,
        )

        missing_handoff = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            status='Dispatched',
            source_location='Vault A',
            destination_location='Nairobi Branch',
            created_by=user,
        )

        delivered_without_confirmation = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            status='Delivered',
            source_location='Vault A',
            destination_location='Nairobi Branch',
            created_by=user,
        )

        completed_transfer = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            status='Delivered',
            source_location='Vault A',
            destination_location='Nairobi Branch',
            created_by=user,
        )
        DeliveryConfirmation.objects.create(
            shipment=completed_transfer,
            courier=courier,
            destination_location='Nairobi Branch',
            receiving_custodian='Ops Lead',
            delivery_status='Delivered',
            manifest_matched=True,
            all_tapes_delivered=True,
            discrepancies_resolved=True,
        )

        self.client.force_login(user)
        response = self.client.get(reverse('operations-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['custody_transfers_open'], 1)
        self.assertEqual(response.context['custody_transfers_completed'], 1)
        self.assertEqual(response.context['missing_handoffs'], 1)
        self.assertEqual(response.context['unverified_deliveries'], 1)


class OperationsDashboardNotificationsTests(TestCase):
    def test_notification_view_links_render_with_target_url_hooks(self):
        operations_group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='ops-notifications',
            email='ops-notifications@example.com',
            password='pass1234',
        )
        user.groups.add(operations_group)
        AuditLog.objects.create(
            name='Shipment Request Submitted',
            action='Shipment request was submitted for review.',
            user=user,
            severity='warning',
            is_read=False,
        )

        self.client.force_login(user)
        response = self.client.get(reverse('operations-dashboard'), {'show_notifications': '1'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'notification-view-link')
        self.assertContains(response, 'data-target-url=')


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


class TwoFactorLoginTests(TestCase):
    def test_signin_sends_terminal_otp_and_completes_login(self):
        operations_group = Group.objects.create(name='Operations Manager')
        user = get_user_model().objects.create_user(
            username='otp-user',
            email='otp-user@example.com',
            password='pass1234',
        )
        user.groups.add(operations_group)

        with patch('builtins.print') as mocked_print:
            response = self.client.post(reverse('signin'), {'username': 'otp-user', 'password': 'pass1234'})

            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Verification Code')
            self.assertTrue(self.client.session.get('pending_2fa_user_id'))
            otp_code = self.client.session.get('pending_2fa_otp')
            self.assertTrue(otp_code)
            mocked_print.assert_called()

            final_response = self.client.post(reverse('signin'), {'otp_code': otp_code})

            self.assertEqual(final_response.status_code, 302)
            self.assertRedirects(final_response, reverse('operations-dashboard'))
            self.assertIn('_auth_user_id', self.client.session)


class BackupDashboardShipmentApprovalTests(TestCase):
    def test_backup_dashboard_alert_bell_counts_only_unread_alerts(self):
        backup_group = Group.objects.create(name='Backup Administrator')
        backup_admin = get_user_model().objects.create_user(
            username='backup-bell-count',
            email='backup-bell-count@example.com',
            password='pass1234',
            first_name='Backup',
            last_name='Admin',
        )
        backup_admin.groups.add(backup_group)

        AuditLog.objects.create(
            name='Shipment Rejected',
            action='An alert arrived for review.',
            user=backup_admin,
            severity='warning',
            is_read=False,
        )
        AuditLog.objects.create(
            name='Shipment Approved',
            action='A previous alert was already reviewed.',
            user=backup_admin,
            severity='error',
            is_read=True,
        )

        self.client.force_login(backup_admin)
        response = self.client.get(reverse('backup-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['alert_count'], 1)

    def test_backup_dashboard_marks_alerts_read_when_panel_is_opened(self):
        backup_group = Group.objects.create(name='Backup Administrator')
        backup_admin = get_user_model().objects.create_user(
            username='backup-new-badge',
            email='backup-new-badge@example.com',
            password='pass1234',
            first_name='Backup',
            last_name='Admin',
        )
        backup_admin.groups.add(backup_group)

        alert = AuditLog.objects.create(
            name='Shipment Rejected',
            action='Shipment REQ-100 was rejected by the backup administrator.',
            user=backup_admin,
            severity='warning',
            is_read=False,
        )

        self.client.force_login(backup_admin)
        initial_response = self.client.get(reverse('backup-dashboard'))
        self.assertEqual(initial_response.status_code, 200)
        self.assertContains(initial_response, '<span class="badge bg-primary">New</span>')
        self.assertContains(initial_response, alert.action)

        panel_response = self.client.get(reverse('backup-dashboard'), {'show_alerts': '1'})
        self.assertEqual(panel_response.status_code, 200)
        self.assertNotContains(panel_response, '<span class="badge bg-primary">New</span>')
        alert.refresh_from_db()
        self.assertTrue(alert.is_read)
        self.assertIsNotNone(alert.read_at)

    def test_backup_admin_can_approve_pending_shipment_from_dashboard_with_barcode_and_courier(self):
        operations_group = Group.objects.create(name='Operations Manager')
        backup_group = Group.objects.create(name='Backup Administrator')
        courier_group = Group.objects.create(name='Courier')

        operator = get_user_model().objects.create_user(
            username='operator-approve',
            email='operator-approve@example.com',
            password='pass1234',
            first_name='Op',
            last_name='User',
        )
        operator.groups.add(operations_group)

        backup_admin = get_user_model().objects.create_user(
            username='backup-approve',
            email='backup-approve@example.com',
            password='pass1234',
            first_name='Backup',
            last_name='Admin',
        )
        backup_admin.groups.add(backup_group)

        courier_user = get_user_model().objects.create_user(
            username='courier-approve',
            email='courier-approve@example.com',
            password='pass1234',
            first_name='Courier',
            last_name='Guy',
        )
        courier_user.groups.add(courier_group)
        courier_profile = CourierProfile.objects.create(
            user=courier_user,
            courier_id='CR-200',
            full_name='Courier Guy',
            phone_number='555-2000',
            email='courier-approve@example.com',
        )

        tape = Tape.objects.create(
            volser='TAPE-777',
            barcode='BAR-777',
            tape_type='LTO-8',
            retention_end_date=date(2030, 1, 1),
            status='Active',
            current_location='Vault A',
        )

        shipment = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            source_location='Nairobi Branch',
            status='Pending',
            releasing_custodian='Op User',
            created_by=operator,
        )

        self.client.force_login(backup_admin)
        response = self.client.post(
            reverse('backup-dashboard'),
            {
                'form_type': 'backup_admin_assignment',
                'shipment_id': shipment.pk,
                'barcode': tape.barcode,
                'courier': courier_profile.pk,
                'decision': 'approve',
                'comments': 'Approved for dispatch.',
            },
        )

        self.assertEqual(response.status_code, 302)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, 'Approved')
        self.assertTrue(shipment.tapes.filter(pk=tape.pk).exists())
        self.assertEqual(shipment.courier_name, 'Courier Guy')
        self.assertTrue(
            shipment.created_by and
            ShipmentApprovalHistory.objects.filter(shipment=shipment, action='Approved').exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(user=operator, action__icontains='approved').exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(user=courier_user, action__icontains='approved').exists()
        )

    def test_assignment_form_includes_courier_group_user_without_existing_profile(self):
        courier_group = Group.objects.create(name='Courier')
        courier_user = get_user_model().objects.create_user(
            username='carrier-no-profile',
            email='carrier-no-profile@example.com',
            password='pass1234',
            first_name='Carrier',
            last_name='User',
        )
        courier_user.groups.add(courier_group)

        form = BackupShipmentAssignmentForm()
        choices = dict(form.fields['courier'].choices)

        self.assertIn(f'user:{courier_user.pk}', choices)
        self.assertEqual(choices[f'user:{courier_user.pk}'], 'Carrier User')

    def test_assignment_form_includes_user_with_courier_role_even_without_group(self):
        courier_user = get_user_model().objects.create_user(
            username='role-courier',
            email='role-courier@example.com',
            password='pass1234',
            first_name='Courier',
            last_name='Role',
        )
        courier_user.role = 'courier'
        courier_user.save(update_fields=['role'])

        form = BackupShipmentAssignmentForm()
        choices = dict(form.fields['courier'].choices)

        self.assertIn(f'user:{courier_user.pk}', choices)
        self.assertEqual(choices[f'user:{courier_user.pk}'], 'Courier Role')

    def test_assignment_form_renders_courier_options_in_select(self):
        courier_group = Group.objects.create(name='Courier')
        courier_user = get_user_model().objects.create_user(
            username='rendered-courier',
            email='rendered-courier@example.com',
            password='pass1234',
            first_name='Rendered',
            last_name='Courier',
        )
        courier_user.groups.add(courier_group)

        form = BackupShipmentAssignmentForm()
        rendered = form['courier'].as_widget()

        self.assertIn('Rendered Courier', rendered)

    def test_assigned_shipments_page_shows_shipments_for_courier_user(self):
        courier_group = Group.objects.create(name='Courier')
        courier_user = get_user_model().objects.create_user(
            username='assigned-courier',
            email='assigned-courier@example.com',
            password='pass1234',
            first_name='Assigned',
            last_name='Courier',
        )
        courier_user.groups.add(courier_group)

        operator_user = get_user_model().objects.create_user(
            username='operator-assignee',
            email='operator-assignee@example.com',
            password='pass1234',
            first_name='Operator',
            last_name='Assignee',
        )

        shipment = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            source_location='Nairobi Branch',
            destination_location='Mombasa Branch',
            status='Approved',
            releasing_custodian='Ops User',
            created_by=operator_user,
            courier_name='Assigned Courier',
            courier_contact='assigned-courier@example.com',
        )

        self.client.force_login(courier_user)
        response = self.client.get(reverse('assigned-shipments'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, shipment.shipment_id)
        self.assertContains(response, 'Mombasa Branch')

    def test_pickup_confirmation_works_for_courier_group_user_without_profile(self):
        courier_group = Group.objects.create(name='Courier')
        courier_user = get_user_model().objects.create_user(
            username='pickup-no-profile',
            email='pickup-no-profile@example.com',
            password='pass1234',
            first_name='Pickup',
            last_name='Courier',
        )
        courier_user.groups.add(courier_group)

        operator = get_user_model().objects.create_user(
            username='pickup-operator',
            email='pickup-operator@example.com',
            password='pass1234',
            first_name='Pickup',
            last_name='Operator',
        )

        shipment = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            source_location='Nairobi Branch',
            status='Approved',
            releasing_custodian='Ops User',
            created_by=operator,
        )

        self.client.force_login(courier_user)
        response = self.client.post(
            reverse('pickup-confirmation', args=[shipment.pk]),
            {
                'manifest_reference': 'MANIFEST-2',
                'pickup_date': '2026-06-26',
                'pickup_time': '09:00',
                'pickup_location': 'Vault A',
                'notes': 'Pickup confirmed',
                'all_tapes_scanned': 'on',
                'manifest_verified': 'on',
                'tape_count_matched': 'on',
                'no_damaged_tapes': 'on',
                'custody_accepted': 'on',
            },
        )

        shipment.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(shipment.status, 'Picked Up')
        self.assertTrue(CourierProfile.objects.filter(user=courier_user).exists())

    def test_courier_dashboard_activity_log_shows_pickup_for_specific_user(self):
        courier_group = Group.objects.create(name='Courier')
        courier_user = get_user_model().objects.create_user(
            username='activity-courier',
            email='activity-courier@example.com',
            password='pass1234',
            first_name='Activity',
            last_name='Courier',
        )
        courier_user.groups.add(courier_group)

        operator = get_user_model().objects.create_user(
            username='activity-operator',
            email='activity-operator@example.com',
            password='pass1234',
            first_name='Activity',
            last_name='Operator',
        )

        shipment = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            source_location='Nairobi Branch',
            status='Approved',
            releasing_custodian='Ops User',
            created_by=operator,
        )

        self.client.force_login(courier_user)
        self.client.post(
            reverse('pickup-confirmation', args=[shipment.pk]),
            {
                'manifest_reference': 'MANIFEST-ACT',
                'pickup_date': '2026-06-26',
                'pickup_time': '09:00',
                'pickup_location': 'Vault A',
                'notes': 'Pickup confirmed',
                'all_tapes_scanned': 'on',
                'manifest_verified': 'on',
                'tape_count_matched': 'on',
                'no_damaged_tapes': 'on',
                'custody_accepted': 'on',
            },
        )

        dashboard_response = self.client.get(reverse('courier-dashboard'))
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertContains(dashboard_response, 'Picked Up')
        self.assertTrue(
            ShipmentTransportEvent.objects.filter(
                shipment=shipment,
                courier__user=courier_user,
                event_type='Picked Up',
            ).exists()
        )

    def test_backup_admin_can_reject_pending_shipment_with_comment_and_notify_operator(self):
        operations_group = Group.objects.create(name='Operations Manager')
        backup_group = Group.objects.create(name='Backup Administrator')

        operator = get_user_model().objects.create_user(
            username='operator-reject',
            email='operator-reject@example.com',
            password='pass1234',
            first_name='Op',
            last_name='User',
        )
        operator.groups.add(operations_group)

        backup_admin = get_user_model().objects.create_user(
            username='backup-reject',
            email='backup-reject@example.com',
            password='pass1234',
            first_name='Backup',
            last_name='Admin',
        )
        backup_admin.groups.add(backup_group)

        shipment = Shipment.objects.create(
            shipment_type='Off-Site Transfer',
            source_location='Nairobi Branch',
            status='Pending',
            releasing_custodian='Op User',
            created_by=operator,
        )

        self.client.force_login(backup_admin)
        response = self.client.post(
            reverse('backup-dashboard'),
            {
                'form_type': 'backup_admin_assignment',
                'shipment_id': shipment.pk,
                'submit_action': 'reject',
                'comments': 'Please resubmit with the full shipment details.',
            },
        )

        self.assertEqual(response.status_code, 302)
        shipment.refresh_from_db()
        self.assertEqual(shipment.status, 'Rejected')
        self.assertEqual(shipment.approval_remarks, 'Please resubmit with the full shipment details.')
        self.assertTrue(
            ShipmentApprovalHistory.objects.filter(shipment=shipment, action='Rejected').exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(user=operator, action__icontains='rejected').exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(user=operator, action__icontains='Please resubmit').exists()
        )


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
