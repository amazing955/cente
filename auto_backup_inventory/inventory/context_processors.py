from django.urls import reverse

from .models import DashboardFeatureExemption, DashboardFeaturePermission, Role, UserRoleAssignment, get_dashboard_feature_catalog


ROLE_DASHBOARD_ROUTE_MAP = {
    'admin': 'dashboard',
    'backup': 'backup-dashboard',
    'operations': 'operations-dashboard',
    'warehouse': 'warehouse-operations-dashboard',
    'auditor': 'auditor-dashboard',
    'supreme': 'supreme-approver-dashboard',
    'courier': 'courier-dashboard',
    'dr': 'investigation-dashboard',
    'security': 'dashboard',
}

ROLE_DISPLAY_LABELS = {
    'admin': 'System Administrator',
    'backup': 'Backup Administrator',
    'operations': 'Operations Manager',
    'warehouse': 'Warehouse Operations',
    'auditor': 'Compliance Auditor',
    'supreme': 'Supreme Approver',
    'courier': 'Courier',
    'dr': 'DR Team',
    'security': 'Information Security Officer',
}


def build_feature_target_url(feature, feature_key):
    from .views import build_dashboard_navigation_url

    params = dict(feature.get('url_params', {}) or {})
    if not params:
        params = {f'show_{feature_key}': '1'}

    dashboard = 'operations' if feature.get('scope') == 'operations' else 'backup'
    return build_dashboard_navigation_url(feature_key, params=params, dashboard=dashboard)


def dashboard_features(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {
            'dashboard_features': [],
            'user_dashboard_roles': [],
            'current_dashboard_key': None,
            'current_dashboard_label': None,
            'current_dashboard_url': None,
            'dashboard_selector_available': False,
        }

    if request.user.is_superuser:
        perms = DashboardFeaturePermission.objects.filter(can_view=True)
    else:
        group_ids = request.user.groups.values_list('id', flat=True)
        perms = DashboardFeaturePermission.objects.filter(role_id__in=group_ids, can_view=True)

    exempted_keys = set(
        DashboardFeatureExemption.objects.filter(user=request.user, is_active=True).values_list('feature_key', flat=True)
    )

    visible_features = []
    for feature in get_dashboard_feature_catalog():
        if feature['key'] in exempted_keys:
            continue
        if not perms.filter(feature_key=feature['key']).exists():
            continue

        target_url = build_feature_target_url(feature, feature['key'])

        visible_features.append({
            'key': feature['key'],
            'name': feature['name'],
            'icon': feature['icon'],
            'target_url': target_url,
            'api_url': reverse('api-feature-navigation', kwargs={'feature_key': feature['key']}),
            'description': feature['description'],
        })

    approved_assignments = UserRoleAssignment.objects.select_related('role', 'role__group').filter(
        user=user,
        status__in=['Backup Approved', 'Supreme Approved', 'Active'],
        role__is_active=True,
    ).order_by('-is_primary_dashboard', 'role__sort_order', 'role__name')

    role_entries = []
    seen_dashboard_keys = set()
    for assignment in approved_assignments:
        role = assignment.role
        if not role or role.dashboard_key in seen_dashboard_keys:
            continue
        seen_dashboard_keys.add(role.dashboard_key)
        role_entries.append({
            'id': str(role.id),
            'label': role.name,
            'dashboard_key': role.dashboard_key,
            'url_name': ROLE_DASHBOARD_ROUTE_MAP.get(role.dashboard_key, 'dashboard'),
            'url': reverse(ROLE_DASHBOARD_ROUTE_MAP.get(role.dashboard_key, 'dashboard')),
            'is_primary': assignment.is_primary_dashboard,
            'is_current': request.session.get('active_dashboard_key') == role.dashboard_key,
            'status': assignment.status,
        })

    if not role_entries:
        legacy_dashboard_key = getattr(user, 'get_primary_dashboard_key', lambda: None)()
        if legacy_dashboard_key:
            role_entries.append({
                'id': legacy_dashboard_key,
                'label': ROLE_DISPLAY_LABELS.get(legacy_dashboard_key, legacy_dashboard_key.replace('_', ' ').title()),
                'dashboard_key': legacy_dashboard_key,
                'url_name': ROLE_DASHBOARD_ROUTE_MAP.get(legacy_dashboard_key, 'dashboard'),
                'url': reverse(ROLE_DASHBOARD_ROUTE_MAP.get(legacy_dashboard_key, 'dashboard')),
                'is_primary': True,
                'is_current': request.session.get('active_dashboard_key') == legacy_dashboard_key,
                'status': 'Active',
            })

    current_dashboard_key = request.session.get('active_dashboard_key') or (role_entries[0]['dashboard_key'] if role_entries else None)
    current_dashboard_label = ROLE_DISPLAY_LABELS.get(current_dashboard_key, None) if current_dashboard_key else None
    current_dashboard_url = reverse(ROLE_DASHBOARD_ROUTE_MAP.get(current_dashboard_key, 'dashboard')) if current_dashboard_key else None

    return {
        'dashboard_features': visible_features,
        'user_dashboard_roles': role_entries,
        'current_dashboard_key': current_dashboard_key,
        'current_dashboard_label': current_dashboard_label,
        'current_dashboard_url': current_dashboard_url,
        'dashboard_selector_available': len(role_entries) > 1,
    }
