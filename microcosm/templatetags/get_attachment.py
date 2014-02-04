from django import template
register = template.Library()

@register.assignment_tag(takes_context=True)
def get_attachment(context, comment_id):

    if str(comment_id) in context['attachments']:
      return context['attachments'][str(comment_id)]
    else:
      return False