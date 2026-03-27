from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def url_replace(context, field, value):
    request = context.get('request')
    if request:
        params = request.GET.copy()
        params[field] = value
        return params.urlencode()
    return f'{field}={value}'


@register.filter
def subtract(value, arg):
    try:
        return int(value) - int(arg)
    except (ValueError, TypeError):
        return value
