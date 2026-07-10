# Generated migration to seed Role records and migrate legacy group membership into role assignments.
from django.db import migrations
from django.utils import timezone
from django.utils.text import slugify


ROLE_DEFINITIONS = [
    ('System Administrator', 'admin', ['System Administrator']),
    ('Backup Administrator', 'backup', ['Backup Administrator']),
    ('Operations Manager', 'operations', ['Operations Manager']),
    ('Warehouse Operations', 'warehouse', ['Warehouse Operations', 'Warehouse Ops']),
    ('Compliance Auditor', 'auditor', ['Auditor', 'Compliance Auditor', 'IT Compliance Auditor']),
    ('Supreme Approver', 'supreme', ['Supreme Approver']),
    ('Courier', 'courier', ['Courier']),
    ('DR Team', 'dr', ['DR Team']),
    ('Information Security Officer', 'security', ['Security Officer', 'Information Security Officer']),
]

PRIMARY_PRIORITY = ['admin', 'backup', 'operations', 'warehouse', 'auditor', 'supreme', 'courier', 'dr', 'security']


def forwards(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model('inventory', 'CustomUser')
    Role = apps.get_model('inventory', 'Role')
    UserRoleAssignment = apps.get_model('inventory', 'UserRoleAssignment')

    role_by_key = {}
    for sort_order, (name, dashboard_key, group_names) in enumerate(ROLE_DEFINITIONS):
        group = None
        for group_name in group_names:
            group, _ = Group.objects.get_or_create(name=group_name)
            if group:
                break
        role, _ = Role.objects.get_or_create(
            dashboard_key=dashboard_key,
            defaults={
                'name': name,
                'slug': slugify(name),
                'group': group,
                'sort_order': sort_order,
                'is_active': True,
            },
        )
        role.name = name
        if not getattr(role, 'slug', ''):
            role.slug = slugify(name)
        role.group = group
        role.sort_order = sort_order
        role.is_active = True
        role.save(update_fields=['name', 'slug', 'group', 'sort_order', 'is_active', 'updated_at'])
        role_by_key[dashboard_key] = role

    for user in User.objects.filter(is_active=True):
        matched_keys = []
        if getattr(user, 'is_superuser', False):
            matched_keys.append('admin')

        legacy_role = (getattr(user, 'role', '') or '').strip().lower()
        legacy_role_map = {
            'operations_manager': 'operations',
            'auditor': 'auditor',
        }
        if legacy_role in legacy_role_map:
            matched_keys.append(legacy_role_map[legacy_role])

        group_names = [group.name.lower() for group in user.groups.all()]
        for dashboard_key, _, group_aliases in [(item[1], item[0], item[2]) for item in ROLE_DEFINITIONS]:
            if dashboard_key in matched_keys:
                continue
            if any(alias.lower() in group_names for alias in group_aliases):
                matched_keys.append(dashboard_key)

        ordered_keys = []
        for key in PRIMARY_PRIORITY:
            if key in matched_keys and key not in ordered_keys:
                ordered_keys.append(key)

        for index, dashboard_key in enumerate(ordered_keys):
            role = role_by_key.get(dashboard_key)
            if not role:
                continue
            assignment, created = UserRoleAssignment.objects.get_or_create(
                user=user,
                role=role,
                defaults={
                    'status': 'Active',
                    'is_primary_dashboard': index == 0,
                    'assigned_at': timezone.now(),
                    'activated_at': timezone.now(),
                    'audit_history': [{
                        'action': 'Migrated',
                        'user': 'System',
                        'timestamp': timezone.now().isoformat(),
                        'comment': 'Migrated from legacy group membership.',
                    }],
                },
            )
            if created:
                continue
            assignment.status = 'Active'
            assignment.is_primary_dashboard = index == 0 or assignment.is_primary_dashboard
            assignment.activated_at = assignment.activated_at or timezone.now()
            assignment.audit_history = list(assignment.audit_history or [])
            assignment.save(update_fields=['status', 'is_primary_dashboard', 'activated_at', 'audit_history', 'updated_at'])
            if role.group:
                user.groups.add(role.group)


def backwards(apps, schema_editor):
    UserRoleAssignment = apps.get_model('inventory', 'UserRoleAssignment')
    Role = apps.get_model('inventory', 'Role')
    UserRoleAssignment.objects.all().delete()
    Role.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [
        ('inventory', '0032_role_userroleassignment'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
