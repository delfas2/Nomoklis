from django import template
from nomoklis_app.utils import encrypt_id as utils_encrypt_id

register = template.Library()

@register.filter
def encrypt_id(value):
    return utils_encrypt_id(value)
