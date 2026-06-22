from django import template

register = template.Library()

@register.filter
def get_group_template(role_templates_by_group, group):
    return role_templates_by_group.get(group.name)
