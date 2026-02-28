from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Заменяет одну строку другой в значении.
    Использование: {{ value|replace:"old,new" }}
    """
    if ',' not in arg:
        return value
    old, new = arg.split(',', 1)
    return value.replace(old, new)
