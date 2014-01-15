from django import template
import math
register = template.Library()

@register.inclusion_tag('block_profile.html',takes_context=True)
def profile(context, profile, **kwargs):

  context['profile'] = profile
  return context