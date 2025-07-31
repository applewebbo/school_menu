from django import template

register = template.Library()


@register.filter(name="add_class")
def add_class(field, css):
    """
    A template filter to add a CSS class to a form field.
    """
    return field.as_widget(attrs={"class": css})
