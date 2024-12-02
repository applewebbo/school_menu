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


@register.filter(name="weeks")
def weeks(value):
    return range(1, value + 1)


@register.filter(name="days")
def remaining_days(value):
    """
    Calculate the number of days remaining from today until the given date plus 30 days.
    """
    from datetime import datetime, timedelta

    if isinstance(value, str):
        try:
            value = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return 0

    target_date = value + timedelta(days=30)
    today = datetime.now().date()
    remaining = (target_date.date() - today).days

    return max(0, remaining)
