import django.forms
from django.core.exceptions import ValidationError

longTextInput=django.forms.TextInput(attrs={'size':'80'})

def validate_no_spaces(value):
    if ' ' in value:
        raise ValidationError('Profile name cannot contain spaces ( )')
    if '+' in value:
        raise ValidationError('Profile name cannot contain pluses (+)')
    if '@' in value:
        raise ValidationError('Profile name cannot contain ats (@)')

def validate_name_too_short(value):
    if len(value) <= 1:
        raise ValidationError('Profile name is too short')


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
    comment_id = django.forms.IntegerField(required=False, widget=django.forms.HiddenInput)

    # Item ID and Item Type (e.g. 'event') to which this comment belongs.
    itemId = django.forms.IntegerField(widget=django.forms.HiddenInput)
    itemType = django.forms.CharField(widget=django.forms.HiddenInput)

    # Comment text in markdown format.
    markdown = django.forms.CharField(max_length='50000', widget=django.forms.Textarea)

    # ID of the comment this is a reply to (optional).
    # TODO: why is initial=0 ?
    inReplyTo = django.forms.IntegerField(required=False, initial=0, widget=django.forms.HiddenInput)

    attachments = django.forms.IntegerField(required=False, initial=0, widget=django.forms.HiddenInput)


class EventCreate(ItemForm):
    """
    Form for creating events.
    """

    title = django.forms.CharField(
        max_length='150',
        label='What is the name of the event?',
        error_messages={
            'required' : 'Please add a title',
            'max_length' : 'Title may not be longer than 150 characters'
        }
    )

    isoFormat = ('%Y-%m-%dT%H:%M:%SZ','%Y-%m-%dT%H:%M:%S.%fZ','%Y-%m-%dT%H:%M:%S.%f',)
    when = django.forms.DateTimeField(
        required=False,
        input_formats=isoFormat,
        label='When does the event begin?',
        error_messages={
            'required' : 'Please add a time and date for this event',
            'invalid' : 'Please check the date and time formatting'
        }
    )

    tz = django.forms.CharField(
        max_length='150',
        label='What timezone does the event occur in?',
        error_messages={
            'required' : 'Please select a timezone',
        }
    )

    duration = django.forms.IntegerField(
        required=False,
        label='How long (in minutes) does the event go on for?',
        error_messages={
            'required' : 'Please add a duration for this event',
            'invalid' : 'Please input an integer'
        }
    )

    where = django.forms.CharField(
        max_length='150',
        required=False,
        label='Where is the event being held?',
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

    invite = django.forms.CharField(widget=django.forms.HiddenInput,required=False)
    inviteObject = django.forms.CharField(widget=django.forms.HiddenInput,required=False)


class EventEdit(EventCreate):
    """
    Edit an Event, supplying id and editReason
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    editReason = django.forms.CharField(label='Reason for editing')

    @classmethod
    def from_event_instance(cls, event):
        """
        Populate form from an event instance.
        """
        repr = {}
        repr['id'] = event.id
        repr['microcosmId'] = event.microcosm_id
        repr['title'] = event.title
        if hasattr(event, 'when'): repr['when'] = event.when
        if hasattr(event, 'tz'): repr['tz'] = event.tz
        if hasattr(event, 'duration'): repr['duration'] = event.duration

        # Event location
        if hasattr(event, 'where'): repr['where'] = event.where
        if hasattr(event, 'lat'): repr['lat'] = event.lat
        if hasattr(event, 'lon'): repr['lon'] = event.lon
        if hasattr(event, 'north'): repr['north'] = event.north
        if hasattr(event, 'east'): repr['east'] = event.east
        if hasattr(event, 'south'): repr['south'] = event.south
        if hasattr(event, 'west'): repr['west'] = event.west

        # RSVP limit is optional
        if hasattr(event, 'rsvp_attend'): repr['rsvpAttend'] = event.rsvp_attend
        if hasattr(event, 'rsvp_limit'): repr['rsvpLimit'] = event.rsvp_limit
        if hasattr(event, 'rsvp_spaces'): repr['rsvpSpaces'] = event.rsvp_spaces

        return cls(repr)


class ConversationCreate(ItemForm):
    """
    Form for creating conversations (a group of comments).
    """

    title = django.forms.CharField(
        max_length='150',
        label='What is the subject of the conversation?',
        error_messages={
            'required' : 'Please add a subject',
            'max_length' : 'The subject may not be longer than 150 characters'
        }
    )


class ConversationEdit(ConversationCreate):
    """
    Form for editing conversations.
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    editReason = django.forms.CharField(label='Reason for editing')

    @classmethod
    def from_conversation_instance(cls, conversation):
        """
        Populate a conversation edit form from a conversation instance.
        """

        repr = {}
        repr['id'] = conversation.id
        repr['microcosmId'] = conversation.microcosm_id
        repr['title'] = conversation.title

        return cls(repr)


class HuddleCreate(django.forms.Form):
    """
    Form for creating huddles (a group of comments).
    """

    title = django.forms.CharField(
        max_length='150',
        label='What is the subject of the message?',
        error_messages={
            'required' : 'Please add a subject',
            'max_length' : 'The subject may not be longer than 150 characters'
        }
    )

    is_confidential = django.forms.ChoiceField(
        label='Is this message confidential',
        choices = [(1, 'yes'),(0, 'no')],
        widget=django.forms.RadioSelect,
        error_messages={
            'required' : 'Please choose either yes or no.'
        }
    )


class HuddleEdit(HuddleCreate):
    """
    Form for editing conversations.
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    editReason = django.forms.CharField(label='Reason for editing')

    @classmethod
    def from_huddle_instance(cls, huddle):
        """
        Populate a huddle edit form from a huddle instance.
        """

        repr = {}
        repr['id'] = huddle.id
        repr['title'] = huddle.title

        return cls(repr)


class MicrocosmCreate(django.forms.Form):
    """
    Form for creating Microcosms.
    """

    title = django.forms.CharField(
        max_length='50',
        label='What is the name of the forum?',
        error_messages={
            'required' : 'The name is required',
            'max_length' : 'Name may not be longer than 50 characters'
        }
    )
    description = django.forms.CharField(
        max_length='255',
        label='What is the forum about?',
        error_messages={
            'required' : 'A description is required and helps keep a forum on-topic',
            'max_length' : 'The description may not be longer than 255 characters'
        }
    )
    parentId = django.forms.IntegerField(
        widget=django.forms.HiddenInput,
    )

    itemTypes = django.forms.MultipleChoiceField(
        widget=django.forms.CheckboxSelectMultiple,
        label='What content can the forum contain?',
        choices=(
            ("microcosm", "Forums"),
            ("conversation", "Conversations"),
            ("event", "Events"),
        )
    )

    visibility = django.forms.CharField(
        initial='public',
        widget=django.forms.HiddenInput
    )


class MicrocosmEdit(MicrocosmCreate):
    """
    Form for editing a forum.
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    editReason = django.forms.CharField(label='Reason for editing')

class ProfileEdit(django.forms.Form):
    """
    Form for editing a profile.
    """

    id = django.forms.IntegerField(widget=django.forms.HiddenInput)
    avatar = django.forms.ImageField(required=False)
    profileName = django.forms.CharField(
        max_length='25',
        label='Choose a username by which you wish to be known',
        error_messages = {
            'required' : 'Please add a profile name',
            'max_length' : 'Profile name may not be longer than 25 characters',
            'valid_chars' : "Your user name may not contain spaces or the '+' and '@' characters."
        },
        validators=[validate_no_spaces, validate_name_too_short]
    )
    # Comment text in markdown format.
    markdown = django.forms.CharField(required=False, max_length='5000', widget=django.forms.Textarea)

class ProfilePatch(django.forms.Form):
    """
    Form for patching a profile.
    """

    member = django.forms.CharField(initial=False, max_length='10', widget=django.forms.HiddenInput, required=True)
