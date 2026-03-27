from django import template

register = template.Library()

@register.simple_tag
def url_replace(request, field, value):
    """
    Replace or add a URL parameter while preserving other parameters
    Usage: {% url_replace request 'page' 2 %}
    """
    dict_ = request.GET.copy()
    dict_[field] = value
    return dict_.urlencode()
