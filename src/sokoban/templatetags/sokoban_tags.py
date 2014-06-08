from django import template
from django.forms import fields, CheckboxInput

__author__ = 'jay'


register = template.Library()


def add_attrs(widget_or_field, attrs, is_replace=True):
    """Add attributes from attrs to widget_or_field

    :param widget_or_field: object it can be a widget, field
    :param attrs: dict name, value map that contains all the attributes
     want to be added
    :param is_replace: whether replace the origin value, if not, will just
     append a space then attach the value
    """
    try:
        field = getattr(widget_or_field, 'field')  # for BoundField
    except AttributeError:
        field = widget_or_field
    try:
        widget = getattr(field, 'widget')
    except AttributeError:
        widget = field
    try:
        widget_attrs = getattr(widget, 'attrs')
    except AttributeError:
        # It's not a valid widget like object, so just do nothing
        return widget
    if is_replace:
        widget_attrs.update(attrs)
        return widget
    for name in attrs:
        if name in widget_attrs:
            widget_attrs[name] = widget_attrs[name] + ' ' + attrs[name]
        else:
            widget_attrs[name] = attrs[name]
    return widget_or_field


@register.filter
def add_cls(widget_or_field, cls):
    """Dynamic add class to widget or field.
    """
    return add_attrs(widget_or_field, {'class': cls}, is_replace=False)


@register.filter
def add_attr(widget_or_field, name_value_pair):
    """Add an attribute to an object

    :param widget_or_field: object it can be a widget, field
    :param name_value_pair: str attribute string,
     in "name:value[:isreplace]" format
    """
    name_value_pair = name_value_pair.split(':')
    assert len(name_value_pair) >= 2
    attr_dict = {name_value_pair[0]: name_value_pair[1]}
    if len(name_value_pair) == 2 or name_value_pair[2] == 'false':
        return add_attrs(widget_or_field, attr_dict, False)
    else:
        return add_attrs(widget_or_field, attr_dict, True)


@register.filter
def angularfy(origin_field, prefix):
    """Add bind attr to a field
    """
    widget = origin_field.field.widget
    if prefix:
        widget.attrs['ng-model'] = prefix + '.' + origin_field.name
    if not widget.attrs:
        widget.attrs = {}
    if 'maxlength' in widget.attrs:
        widget.attrs['ng-maxlength'] = widget.attrs['maxlength']
    if widget.is_required:
        widget.attrs['ng-required'] = 'true'
    if isinstance(origin_field.field, fields.EmailField):
        widget.input_type = 'email'
    elif isinstance(origin_field.field, fields.URLField):
        widget.input_type = 'url'
    elif isinstance(origin_field.field, fields.TimeInput):
        widget.input_type = 'datetime'
    elif isinstance(origin_field.field, fields.IntegerField):
        widget.input_type = 'number'
        if origin_field.field.min_value is not None:
            widget.attrs['min'] = origin_field.field.min_value
        if origin_field.field.max_value is not None:
            widget.attrs['max'] = origin_field.field.max_value
    return origin_field


@register.filter(name='is_checkbox')
def is_checkbox(field):
    return isinstance(field.field.widget, CheckboxInput)
