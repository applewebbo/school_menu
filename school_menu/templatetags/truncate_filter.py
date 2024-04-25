from django import template

register = template.Library()


@register.filter()
def truncate(value, arg):
    """
    This cuts off the value of the string after a certain number of characters.
    If the length of the string is greater than the number of characters specified,
    the string is truncated without adding '...' to the end.
    """
    if len(value) > arg:
        return value[:arg]
    else:
        return value
