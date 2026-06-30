from urllib.parse import urlencode

from django.urls import reverse

from .models import DashboardFeatureExemption, DashboardFeaturePermission, get_dashboard_feature_catalog


def dashboard_features(request):
    if not request.user.is_authenticated:
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

        url_params = dict(feature.get('url_params', {}))
        url_params['feature_key'] = feature['key']
        if url_params:
            target_url = f"{reverse(feature['url_name'])}?{urlencode(url_params)}"
        else:
            target_url = reverse(feature['url_name'])

        visible_features.append({
            'key': feature['key'],
            'name': feature['name'],
            'icon': feature['icon'],
            'target_url': target_url,
            'description': feature['description'],
        })

    return {'dashboard_features': visible_features}
