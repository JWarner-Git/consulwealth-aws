from django import template
from decimal import Decimal
import json
import decimal

register = template.Library()

@register.filter
def abs_value(value):
    """Return the absolute value of a number"""
    try:
        return abs(float(value))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return 0

@register.filter
def floatdiv(value, arg):
    """Divide the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0
    
@register.filter
def floatmult(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    
@register.filter
def min_value(value, arg):
    """Return the minimum of value and arg"""
    try:
        return min(float(value), float(arg))
    except (ValueError, TypeError):
        return 0

@register.filter
def jsonify(obj):
    """Convert an object to JSON string"""
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        return '{}' 

@register.filter
def make_percentage(value, total):
    """Calculate the percentage of value relative to total, capped at 100%"""
    try:
        if float(total) == 0:
            return 0
        percentage = (float(value) / float(total)) * 100
        return min(percentage, 100)  # Cap at 100% using built-in min
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    """Subtract arg from value"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0 