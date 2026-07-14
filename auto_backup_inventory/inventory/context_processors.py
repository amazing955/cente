from django.core.cache import cache
from django.urls import reverse

from .models import DashboardFeatureExemption, DashboardFeaturePermission, Feature, Role, RoleFeature, get_dashboard_feature_catalog


def build_feature_target_url(feature, feature_key):
    from .views import build_dashboard_navigation_url

    params = dict(feature.get('url_params', {}) or {})
    if not params:
        params = {f'show_{feature_key}': '1'}

    if feature.get('url'):
        return feature['url']

    dashboard = 'operations' if feature.get('scope') == 'operations' else 'backup'
    return build_dashboard_navigation_url(feature_key, params=params, dashboard=dashboard)


def _resolve_user_role(user):
    if not user or not user.is_authenticated:
        return None
    if hasattr(user, 'get_active_role'):
        role = user.get_active_role()
        if role:
            return role
    role_key = (getattr(user, 'role', '') or '').strip().lower()
    if not role_key:
        return None
    return Role.objects.filter(slug=role_key, is_active=True).first() or Role.objects.filter(dashboard_key=role_key, is_active=True).first()


def _build_sidebar_sections_for_role(role):
    if not role:
        return []

    cache_key = f'role-sidebar-sections:{role.pk}:{role.updated_at.isoformat()}'
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    sections = []
    grouped_features = {}
    role_features = RoleFeature.objects.filter(
        role=role,
        is_active=True,
        feature__is_active=True,
        feature__sidebar_visible=True,
    ).select_related('feature', 'feature__parent_feature').order_by('feature__menu_group', 'feature__display_order', 'feature__name')

    for role_feature in role_features:
        feature = role_feature.feature
        grouped_features.setdefault(feature.menu_group or 'General', []).append({
            'key': feature.feature_key,
            'name': feature.name,
            'description': feature.description,
            'icon': feature.icon,
            'target_url': feature.get_display_url() or build_feature_target_url({
                'url': feature.url,
                'url_params': feature.url_params,
                'scope': feature.scope,
            }, feature.feature_key),
            'requires_approval': feature.requires_approval,
            'requires_audit': feature.requires_audit,
            'parent_key': feature.parent_feature.feature_key if feature.parent_feature else None,
            'display_order': feature.display_order,
        })

    for menu_group, items in grouped_features.items():
        sections.append({
            'label': menu_group,
            'items': items,
        })

    cache.set(cache_key, sections, 300)
    return sections


def dashboard_features(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'dashboard_features': [], 'role_sidebar_sections': [], 'active_role': None}

    active_role = _resolve_user_role(user)
    role_sidebar_sections = _build_sidebar_sections_for_role(active_role)

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
        role_allows = False
        if active_role:
            role_allows = RoleFeature.objects.filter(role=active_role, feature__feature_key=feature['key'], is_active=True, feature__is_active=True).exists()
        if not role_allows and not perms.filter(feature_key=feature['key']).exists():
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

    return {
        'dashboard_features': visible_features,
        'role_sidebar_sections': role_sidebar_sections,
        'active_role': active_role,
    }
