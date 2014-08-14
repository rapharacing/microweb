from django import template
register = template.Library()

@register.inclusion_tag('block_profile.html',takes_context=True)
def profile(context, profile, **kwargs):

    if hasattr(profile,'item'):
        context['profile'] = profile
    else:
        context['profile'] = {'item': profile}

    if 'no_icon' in kwargs:
        context['no_icon'] = True

    if 'send_message' in kwargs:
        context['send_message'] = True

    return context
