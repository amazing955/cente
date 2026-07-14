from django.apps import AppConfig
from django.db.models.signals import post_migrate


def _seed_roles_and_features(**kwargs):
    import sys
    import os
    try:
        from django.conf import settings
    except Exception:
        settings = None

    # Skip seeding when running tests to avoid interfering with test setup
    is_test_run = False
    try:
        if any('test' in str(a).lower() for a in sys.argv):
            is_test_run = True
        if os.environ.get('PYTEST_CURRENT_TEST'):
            is_test_run = True
        if settings is not None and getattr(settings, 'TESTING', False):
            is_test_run = True
    except Exception:
        is_test_run = False

    if is_test_run:
        return
    from django.contrib.auth.models import Group
    from django.db.utils import OperationalError, ProgrammingError
    from django.urls import reverse

    from .models import Feature, Role, RoleFeature, get_dashboard_feature_catalog

    default_roles = [
        {'name': 'System Administrator', 'slug': 'system_administrator', 'dashboard_key': 'admin', 'group_name': 'System Administrator', 'sort_order': 0},
        {'name': 'Backup Administrator', 'slug': 'backup_administrator', 'dashboard_key': 'backup', 'group_name': 'Backup Administrator', 'sort_order': 10},
        {'name': 'Operations Manager', 'slug': 'operations_manager', 'dashboard_key': 'operations', 'group_name': 'Operations Manager', 'sort_order': 20},
        {'name': 'Warehouse Operations', 'slug': 'warehouse_operations', 'dashboard_key': 'warehouse', 'group_name': 'Warehouse Operations', 'sort_order': 30},
        {'name': 'Supreme Approver', 'slug': 'supreme_approver', 'dashboard_key': 'supreme', 'group_name': 'Supreme Approver', 'sort_order': 40},
        {'name': 'Compliance Auditor', 'slug': 'compliance_auditor', 'dashboard_key': 'auditor', 'group_name': 'Auditor', 'sort_order': 50},
        {'name': 'Information Security Officer', 'slug': 'information_security_officer', 'dashboard_key': 'security', 'group_name': 'Security Officer', 'sort_order': 60},
    ]

    def feature_seed(key, name, icon, url='', url_name='', url_params=None, scope='backup', menu_group='General', description='', display_order=0, sidebar_visible=True, requires_approval=False, requires_audit=False):
        return {
            'feature_key': key,
            'name': name,
            'icon': icon,
            'url': url,
            'url_name': url_name,
            'url_params': url_params or {},
            'scope': scope,
            'menu_group': menu_group,
            'description': description,
            'display_order': display_order,
            'sidebar_visible': sidebar_visible,
            'requires_approval': requires_approval,
            'requires_audit': requires_audit,
        }

    base_features = [
        feature_seed('backup_dashboard', 'Overview', 'bi bi-speedometer2', url_name='backup-dashboard', scope='backup', menu_group='Dashboard', description='Backup administration overview', display_order=10),
        feature_seed('alerts', 'Notifications', 'bi bi-bell', url_name='backup-dashboard', url_params={'show_alerts': '1'}, scope='backup', menu_group='Notifications', description='Alert notifications', display_order=20),
        feature_seed('add_tape', 'Add Tape', 'bi bi-plus-circle', url_name='add-tape', scope='backup', menu_group='Inventory', description='Register new tapes', display_order=10),
        feature_seed('tape_inventory', 'Tape Inventory', 'bi bi-hdd-stack', url_name='backup-dashboard', url_params={'show_tape_inventory': '1'}, scope='backup', menu_group='Inventory', description='Browse tape inventory', display_order=20),
        feature_seed('shipments', 'Shipments', 'bi bi-truck', url_name='backup-dashboard', url_params={'show_shipments': '1'}, scope='backup', menu_group='Operations', description='Shipment management', display_order=10),
        feature_seed('start_shipment_request', 'Start Shipment', 'bi bi-box-arrow-up-right', url_name='start-shipment-request', scope='operations', menu_group='Shipments', description='Submit a new shipment request', display_order=10),
        feature_seed('shipment_approvals', 'Shipment Approvals', 'bi bi-check2-square', url_name='shipment-approvals', scope='operations', menu_group='Shipments', description='Approve shipment requests', display_order=20),
        feature_seed('warehouse_operations_dashboard', 'Warehouse Operations', 'bi bi-box-seam', url_name='warehouse-operations-dashboard', scope='operations', menu_group='Warehouse', description='Warehouse operations overview', display_order=10),
        feature_seed('reconciliation', 'Reconciliation', 'bi bi-arrow-repeat', url_name='backup-dashboard', url_params={'show_reconciliation': '1'}, scope='backup', menu_group='Compliance', description='Reconciliation review', display_order=10),
        feature_seed('reconciliation_reports', 'Reconciliation Reports', 'bi bi-bar-chart-line-fill', url_name='reconciliation-reports', scope='backup', menu_group='Reports', description='Reconciliation reporting', display_order=20),
        feature_seed('audit_logs', 'Audit Logs', 'bi bi-shield-check', url_name='backup-dashboard', url_params={'show_audit': '1'}, scope='backup', menu_group='Audit', description='Audit trail review', display_order=10, requires_audit=True),
        feature_seed('reports', 'Reports', 'bi bi-file-earmark-bar-graph', url_name='backup-dashboard', url_params={'show_reports': 'reports'}, scope='backup', menu_group='Reports', description='Backup reporting', display_order=10),
        feature_seed('exception_management', 'Exception Management', 'bi bi-exclamation-triangle', url_name='operations-dashboard', url_params={'feature_key': 'exception_management'}, scope='operations', menu_group='Compliance', description='Review shipment exceptions', display_order=20, requires_audit=True),
        feature_seed('supreme_approver_dashboard', 'Approval Overview', 'bi bi-shield-lock', url_name='supreme-approver-dashboard', scope='backup', menu_group='Approvals', description='Supreme approver overview', display_order=10, requires_approval=True),
        feature_seed('approval-history', 'Approval History', 'bi bi-clock-history', url_name='approval-history', scope='backup', menu_group='Approvals', description='Review approval history', display_order=20, requires_audit=True),
        feature_seed('role_management', 'Role Management', 'bi bi-diagram-3', url='/dashboard/?active_tab=roles', scope='admin', menu_group='Administration', description='Manage roles', display_order=10, requires_approval=True),
        feature_seed('feature_management', 'Feature Management', 'bi bi-sliders', url='/dashboard/?active_tab=roles&active_panel=%23editRoleFeaturesPanel', scope='admin', menu_group='Administration', description='Manage role features', display_order=20, requires_approval=True),
        feature_seed('settings', 'Settings', 'bi bi-gear', url='/dashboard/?active_tab=settings', scope='admin', menu_group='Settings', description='System settings', display_order=30),
    ]

    role_feature_map = {
        'system_administrator': [feature['feature_key'] for feature in base_features],
        'admin': [feature['feature_key'] for feature in base_features],
        'backup_administrator': ['backup_dashboard', 'alerts', 'add_tape', 'tape_inventory', 'shipments', 'reconciliation', 'reconciliation_reports', 'audit_logs', 'reports', 'supreme_approver_dashboard', 'approval-history'],
        'operations_manager': ['start_shipment_request', 'shipment_approvals', 'warehouse_operations_dashboard', 'exception_management', 'reports'],
        'warehouse_operations': ['warehouse_operations_dashboard', 'shipment_approvals', 'shipments'],
        'supreme_approver': ['supreme_approver_dashboard', 'approval-history', 'role_management', 'feature_management'],
        'compliance_auditor': ['audit_logs', 'reports', 'reconciliation_reports', 'exception_management'],
        'information_security_officer': ['audit_logs', 'role_management', 'feature_management', 'settings'],
    }

    try:
        for name in ['Backup Administrator', 'Operations Manager', 'Warehouse Operations', 'Auditor', 'Security Officer', 'DR Team', 'System Administrator', 'Supreme Approver']:
            Group.objects.get_or_create(name=name)

        from django.db import IntegrityError

        for role_def in default_roles:
            group = Group.objects.filter(name=role_def['group_name']).first()
            try:
                role, _ = Role.objects.get_or_create(
                    slug=role_def['slug'],
                    defaults={
                        'name': role_def['name'],
                        'dashboard_key': role_def['dashboard_key'],
                        'group': group,
                        'sort_order': role_def['sort_order'],
                    },
                )
            except IntegrityError:
                # Another process or older data may have created a Role with the
                # same `name` but a different slug. Try to find an existing role
                # by slug or name and continue; if none found re-raise.
                role = Role.objects.filter(slug=role_def['slug']).first() or Role.objects.filter(name=role_def['name']).first()
                if not role:
                    raise
            updates = []
            if role.name != role_def['name']:
                role.name = role_def['name']
                updates.append('name')
            if role.dashboard_key != role_def['dashboard_key']:
                role.dashboard_key = role_def['dashboard_key']
                updates.append('dashboard_key')
            if group and role.group_id != group.id:
                role.group = group
                updates.append('group')
            if role.sort_order != role_def['sort_order']:
                role.sort_order = role_def['sort_order']
                updates.append('sort_order')
            if updates:
                role.save(update_fields=updates)

        feature_objects = {}
        for feature_def in base_features:
            feature, _ = Feature.objects.update_or_create(
                feature_key=feature_def['feature_key'],
                defaults=feature_def,
            )
            feature_objects[feature.feature_key] = feature

        for role_slug, feature_keys in role_feature_map.items():
            role = Role.objects.filter(slug=role_slug).first()
            if not role:
                continue
            for index, feature_key in enumerate(feature_keys):
                feature = feature_objects.get(feature_key)
                if not feature:
                    continue
                RoleFeature.objects.update_or_create(
                    role=role,
                    feature=feature,
                    defaults={'is_active': True},
                )
    except (OperationalError, ProgrammingError):
        pass


class InventoryConfig(AppConfig):
    name = 'inventory'

    def ready(self):
        from django.contrib.auth.models import Group
        from django.db.utils import OperationalError, ProgrammingError

        group_names = [
            'Backup Administrator',
            'Operations Manager',
            'Courier',
            'Auditor',
            'Security Officer',
            'DR Team',
            'System Administrator',
            'Supreme Approver',
        ]

        try:
            for name in group_names:
                Group.objects.get_or_create(name=name)
        except (OperationalError, ProgrammingError):
            # Database tables may not be ready yet (migrations running)
            pass

        post_migrate.connect(_seed_roles_and_features, sender=self, weak=False)
