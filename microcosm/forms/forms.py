import django.forms
from django.core.exceptions import ValidationError
from django.utils import formats

longTextInput=django.forms.TextInput(attrs={'size':'80'})


def validate_no_spaces(value):
    if ' ' in value:
        raise ValidationError('Profile name cannot contain spaces')


class ItemForm(django.forms.Form):
    """
    Base form for items (such as Event, Poll, Conversation).
    """

    # Indicates the 'parent' microcosm to which this item belongs.
    microcosmId = django.forms.IntegerField(widget=django.forms.HiddenInput)

    # Only users with specific permissions (e.g. moderator, owner) will be able to change these.
    sticky = django.forms.BooleanField(initial=False, widget=django.forms.HiddenInput, required=False)
    moderated = django.forms.BooleanField(initial=False, widget=django.forms.HiddenInput, required=False)
    deleted = django.forms.BooleanField(initial=False, widget=django.forms.HiddenInput, required=False)


class CommentForm(django.forms.Form):
    """
    Form for creating/editing comments.
    """

    # Comment ID - only required when editing.
    id = django.forms.IntegerField(required=False, widget=django.forms.HiddenInput)

    # Item ID and Item Type (e.g. 'event') to which this comment belongs.
    itemId = django.forms.IntegerField(widget=django.forms.HiddenInput)
    itemType = django.forms.CharField(widget=django.forms.HiddenInput)

    # Comment text in markdown format.
    markdown = django.forms.CharField(max_length='50000', widget=django.forms.Textarea)

    # ID of the comment this is a reply to (optional).
    # TODO: why is initial=0 ?
    inReplyTo = django.forms.IntegerField(required=False, initial=0, widget=django.forms.HiddenInput)


class EventCreate(ItemForm):
    """
    Form for creating events.
    """

    title = django.forms.CharField(
        max_length='150',
        label='Event title',
        error_messages={
            'required' : 'Please add a title',
            'max_length' : 'Title may not be longer than 150 characters'
        }
    )

    isoFormat = ('%Y-%m-%dT%H:%M:%SZ','%Y-%m-%dT%H:%M:%S.%fZ','%Y-%m-%dT%H:%M:%S.%f',) + \
        formats.get_format('DATETIME_INPUT_FORMATS')
    when = django.forms.DateTimeField(
        input_formats=isoFormat,
        error_messages={
            'required' : 'Please add a time and date for this event',
            'invalid' : 'Please check the date and time formatting'
        }
    )

    duration = django.forms.IntegerField(
        required=False,
        error_messages={
            'required' : 'Please add a duration for this event',
            'invalid' : 'Please input an integer'
        }
    )

    where = django.forms.CharField(
        max_length='150',
        widget=longTextInput,
        error_messages={
            'required' : 'Please add a location',
            'max_length' : 'This may not be longer than 150 characters'
        }
    )

    rsvpLimit = django.forms.IntegerField(label='RSVP limit', required=False)
    lat = django.forms.FloatField(widget=django.forms.HiddenInput, required=False)
    lon = django.forms.FloatField(widget=django.forms.HiddenInput, required=False)
    north = django.forms.FloatField(widget=django.forms.HiddenInput, required=False)
    east = django.forms.FloatField(widget=django.forms.HiddenInput, required=False)
    south = django.forms.FloatField(widget=django.forms.HiddenInput, required=False)
    west = django.forms.FloatField(widget=django.forms.HiddenInput, required=False)


class EventEdit(EventCreate):
    """
    Edit an Event, supplying id and editReason
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    editReason = django.forms.CharField(label='Reason for editing')


class ConversationCreate(ItemForm):
    """
    Form for creating conversations (a group of comments).
    """

    title = django.forms.CharField(
        max_length='150',
        label='Topic',
        error_messages={
            'required' : 'Please add a title',
            'max_length' : 'Title may not be longer than 150 characters'
        }
    )


class ConversationEdit(ConversationCreate):
    """
    Form for editing conversations.
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    editReason = django.forms.CharField(label='Reason for editing')


class MicrocosmCreate(django.forms.Form):
    """
    Form for creating Microcosms.
    """

    title = django.forms.CharField(
        max_length='150',
        label='Title',
        error_messages={
            'required' : 'Please add a title',
            'max_length' : 'Title may not be longer than 150 characters'
        }
    )
    description = django.forms.CharField(
        max_length='150',
        label='Description',
        error_messages={
            'required' : 'Please add a description',
            'max_length' : 'Description may not be longer than 150 characters'
        }
    )

    visibility = django.forms.ChoiceField(
        choices=(
            ('public', 'public'),
            #('private', 'private')
            ),
        label='All microcosms are currently public'
    )


class MicrocosmEdit(MicrocosmCreate):
    """
    Form for editing a microcosm.
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    editReason = django.forms.CharField(label='Reason for editing')


class ProfileEdit(django.forms.Form):
    """
    Form for editing a profile.
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    # This is the email address a user supplies associated with their gravatar.
    gravatar = django.forms.EmailField(widget=django.forms.HiddenInput, required=False)
    profileName = django.forms.CharField(
        max_length='25',
        label='Profile Name',
        error_messages = {
            'required' : 'Please add a profile name',
            'max_length' : 'Profile name may not be longer than 25 characters'
        },
        validators=[validate_no_spaces]
    )