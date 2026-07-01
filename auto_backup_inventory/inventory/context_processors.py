from urllib.parse import urlencode

from django.urls import reverse

from .models import DashboardFeatureExemption, DashboardFeaturePermission, get_dashboard_feature_catalog


def build_feature_target_url(feature, feature_key):
    url_params = dict(feature.get('url_params', {}))
    if feature.get('url_name') == 'feature-module':
        url_params.pop('feature_key', None)
    else:
        url_params['feature_key'] = feature_key

    url_kwargs = dict(feature.get('url_kwargs', {}))
    url_kwargs.setdefault('feature_key', feature_key)

    base_url = reverse(feature['url_name'], kwargs=url_kwargs)
    return f"{base_url}?{urlencode(url_params)}" if url_params else base_url


def dashboard_features(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'dashboard_features': []}

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

    return {'dashboard_features': visible_features}
