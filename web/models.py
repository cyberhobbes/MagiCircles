import hashlib, urllib, datetime, csv
from django.db import models
from django.contrib.auth.models import User
from django.core import validators
from django.utils.translation import ugettext_lazy as _, string_concat
from django.conf import settings as django_settings
from django.utils import timezone
from web.utils import AttrDict
from web.settings import ACCOUNT_MODEL, GAME_NAME, COLOR, SITE_STATIC_URL, DONATORS_STATUS_CHOICES, STATIC_UPLOADED_FILES_PREFIX, USER_COLORS, FAVORITE_CHARACTERS, SITE_URL
from web.model_choices import *

Account = ACCOUNT_MODEL

############################################################
# Utils

def avatar(user, size=200):
    """
    Preferences in user objects must always be prefetched
    """
    default = '{}img/avatar.png'.format(SITE_STATIC_URL if SITE_STATIC_URL.startswith('http') else ('http:' + SITE_STATIC_URL if SITE_STATIC_URL.startswith('//') else 'http://' + SITE_STATIC_URL))
    if user.preferences.twitter:
        default = '{}twitter_avatar/{}/'.format(SITE_URL if SITE_URL.startswith('http') else 'http:' + SITE_URL, user.preferences.twitter)
    return ("http://www.gravatar.com/avatar/"
            + hashlib.md5(user.email.lower()).hexdigest()
            + "?" + urllib.urlencode({'d': default, 's': str(size)}))

############################################################
# Internal Utils

def _split_data(data):
    """
    Takes a unicode CSV string and return a list of strings.
    """
    def utf_8_encoder(unicode_csv_data):
        for line in unicode_csv_data:
            yield line.encode('utf-8')

    def unicode_csv_reader(unicode_csv_data, **kwargs):
        csv_reader = csv.reader(utf_8_encoder(unicode_csv_data), **kwargs)
        for row in csv_reader:
            yield [unicode(cell, 'utf-8') for cell in row]

    if not data:
        return []
    reader = unicode_csv_reader([data])
    for reader in reader:
        return [r for r in reader]
    return []

def _join_data(*args):
    """
    Takes a list of unicode strings and return a CSV string.
    """
    return u'\"' + u'","'.join([unicode(value).replace('"','\"') for value in args]) + u'\"'

class UserImage(models.Model):
     image = models.ImageField(upload_to=STATIC_UPLOADED_FILES_PREFIX + 'user_images/')

     def __unicode__(self):
         return unicode(self.image)

############################################################
# User preferences

class UserPreferences(models.Model):
    user = models.OneToOneField(User, related_name='preferences', on_delete=models.CASCADE)
    language = models.CharField(_('Language'), max_length=4, choices=django_settings.LANGUAGES)
    description = models.TextField(_('Description'), null=True, help_text=_('Write whatever you want. You can add formatting and links using Markdown.'), blank=True)
    favorite_character1 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('1st')), null=True, max_length=200)
    favorite_character2 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('2nd')), null=True, max_length=200)
    favorite_character3 = models.CharField(verbose_name=_('{nth} Favorite Character').format(nth=_('3rd')), null=True, max_length=200)
    color = models.CharField(_('Color'), max_length=100, null=True, blank=True)
    birthdate = models.DateField(_('Birthdate'), blank=True, null=True)
    location = models.CharField(_('Location'), max_length=200, null=True, blank=True, help_text=string_concat(_('The city you live in.'), ' ', _('It might take up to 24 hours to update your location on the map.')))
    location_changed = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    following = models.ManyToManyField(User, related_name='followers')
    status = models.CharField(choices=STATUS_CHOICES, max_length=12, null=True)
    donation_link = models.CharField(max_length=200, null=True, blank=True)
    donation_link_title = models.CharField(max_length=100, null=True, blank=True)
    email_notifications_turned_off_string = models.CharField(max_length=15, null=True)
    unread_notifications = models.PositiveIntegerField(default=0)

    def localized_favorite_character(self, number):
        if getattr(self, 'favorite_character{}'.format(number)) and FAVORITE_CHARACTERS:
            try:
                return (_(localized) for (name, localized, __) in FAVORITE_CHARACTERS if unicode(name) == getattr(self, 'favorite_character{}'.format(number))).next()
            except: pass
        return ''
    @property
    def localized_favorite_character1(self): return self.localized_favorite_character(1)
    @property
    def localized_favorite_character2(self): return self.localized_favorite_character(2)
    @property
    def localized_favorite_character3(self): return self.localized_favorite_character(3)

    def favorite_character_image(self, number):
        if getattr(self, 'favorite_character{}'.format(number)) and FAVORITE_CHARACTERS:
            try:
                return (image for (name, __, image) in FAVORITE_CHARACTERS if unicode(name) == getattr(self, 'favorite_character{}'.format(number))).next()
            except: pass
        return ''
    @property
    def favorite_character1_image(self): return self.favorite_character_image(1)
    @property
    def favorite_character2_image(self): return self.favorite_character_image(2)
    @property
    def favorite_character3_image(self): return self.favorite_character_image(3)

    @property
    def localized_color(self):
        if self.color and USER_COLORS:
            try:
                return (_(localized) for (name, localized, __, __) in USER_COLORS if name == self.color).next()
            except: pass
        return ''

    @property
    def hex_color(self):
        if self.color and USER_COLORS:
            try:
                return (hex for (name, _, _, hex) in USER_COLORS if name == self.color).next()
            except: pass
        return COLOR

    @property
    def css_color(self):
        if self.color and USER_COLORS:
            try:
                return (css_color for (name, _, css_color, _) in USER_COLORS if name == self.color).next()
            except: pass
        return 'main'

    @property
    def email_notifications_turned_off(self):
        if not self.email_notifications_turned_off_string:
            return []
        return [int(t) for t in self.email_notifications_turned_off_string.split(',')]

    def is_notification_email_allowed(self, notification_type):
        for type in self.email_notifications_turned_off:
            if type == notification_type:
                return False
        return True

    def save_email_notifications_turned_off(self, turned_off):
        """
        Will completely replace any existing list of turned off email notifications.
        """
        self.email_notifications_turned_off_string = ','.join([str(i) for i in turned_off])

    # Cache
    _cache_twitter = models.CharField(max_length=32, null=True, blank=True) # changed when links are modified

    @property
    def twitter(self):
        return self._cache_twitter

    class Meta:
        verbose_name_plural = "list of userpreferences"

############################################################
# User links

class UserLink(models.Model):
    alphanumeric = validators.RegexValidator(r'^[0-9a-zA-Z-_\. ]*$', 'Only alphanumeric and - _ characters are allowed.')
    owner = models.ForeignKey(User, related_name='links')
    type = models.CharField(_('Platform'), max_length=20, choices=LINK_CHOICES)
    value = models.CharField(_('Username/ID'), max_length=64, help_text=_('Write your username only, no URL.'), validators=[alphanumeric])
    relevance = models.PositiveIntegerField(_('How often do you tweet/stream/post about {}?').format(GAME_NAME), choices=LINK_RELEVANCE_CHOICES, null=True, blank=True)

    def url(self):
        return LINK_URLS[self.type].format(self.value)

############################################################
# Activity

class Activity(models.Model):
    creation = models.DateTimeField(auto_now_add=True)
    modification = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, related_name='activities')
    message = models.TextField(_('Message'))
    likes = models.ManyToManyField(User, related_name="liked_activities")
    language = models.CharField(_('Language'), max_length=4, choices=django_settings.LANGUAGES)
    tags_string = models.TextField(blank=True, null=True)
    image = models.ImageField(_('Image'), upload_to=STATIC_UPLOADED_FILES_PREFIX + 'activities/', null=True, blank=True)

    @property
    def tags(self):
        return _split_data(self.tags_string)

    def add_tags(self, new_tags):
        self.tags_string = _join_data(*(self.tags + [tag for tag in new_tags if tag not in tags]))

    def remove_tags(self, tags_to_remove):
        self.tags_string = _join_data(*[tag for tag in self.tags if tag not in tags_to_remove])

    def save_tags(self, tags):
        """
        Will completely replace any existing list of tags.
        """
        self.tags_string = _join_data(*tags)

    # Cache
    _cache_days = 20
    _cache_last_update = models.DateTimeField(null=True)
    _cache_owner_username = models.CharField(max_length=32, null=True)
    _cache_owner_email = models.EmailField(blank=True)
    _cache_owner_preferences_status = models.CharField(choices=STATUS_CHOICES, max_length=12, null=True)
    _cache_owner_preferences_twitter = models.CharField(max_length=32, null=True, blank=True)

    def force_cache_owner(self):
        """
        Recommended to use select_related('owner', 'owner__preferences') when calling this method
        """
        self._cache_last_update = timezone.now()
        self._cache_owner_username = self.owner.username
        self._cache_owner_email = self.owner.email
        self._cache_owner_preferences_status = self.owner.preferences.status
        self._cache_owner_preferences_twitter = self.owner.preferences.twitter
        self.save()

    @property
    def cached_owner(self):
        now = timezone.now()
        if not self._cache_last_update or self._cache_last_update < now - datetime.timedelta(days=self._cache_days):
            self.force_cache_owner()
        cached_owner = AttrDict({
            'pk': self.owner_id,
            'id': self.owner_id,
            'username': self._cache_owner_username,
            'email': self._cache_owner_email,
            'preferences': AttrDict({
                'status': self._cache_owner_preferences_status,
                'twitter': self._cache_owner_preferences_twitter,
            }),
        })
        return cached_owner

    def __unicode__(self):
        """
        Return the first 100 characters without cutting words
        """
        length = 100
        if len(self.message) <= length:
            return self.message
        return ' '.join(self.message[:length+1].split(' ')[0:-1]) + '...'

    class Meta:
        verbose_name_plural = "activities"

############################################################
# Notification

class Notification(models.Model):
    owner = models.ForeignKey(User, related_name='notifications', db_index=True)
    message = models.PositiveIntegerField(choices=NOTIFICATION_CHOICES)
    message_data = models.TextField(blank=True, null=True)
    url_data = models.TextField(blank=True, null=True)
    email_sent = models.BooleanField(default=False)
    seen = models.BooleanField(default=False)
    image = models.ImageField(upload_to=STATIC_UPLOADED_FILES_PREFIX + 'notifications/', null=True, blank=True)

    @property
    def localized_message(self):
        data = _split_data(self.message_data)
        return _(NOTIFICATION_DICT[self.message]).format(*data)

    @property
    def website_url(self):
        data = _split_data(self.url_data if self.url_data else self.message_data)
        return NOTIFICATION_URLS[self.message].format(*data)

    @property
    def icon(self):
        return NOTIFICATION_ICONS[self.message]

    def __unicode__(self):
        return self.localized_message

############################################################
# Report

class Report(models.Model):
    creation = models.DateTimeField(auto_now_add=True)
    modification = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(User, related_name='reports')
    reported_thing = models.CharField(max_length=300)
    reported_thing_title = models.CharField(max_length=300)
    reported_thing_id = models.PositiveIntegerField()
    message = models.TextField(_('Message'))
    images = models.ManyToManyField(UserImage, related_name="report", verbose_name=_('Images'))
    staff = models.ForeignKey(User, related_name='staff_reports', null=True, on_delete=models.SET_NULL)
    staff_message = models.TextField(null=True)
    status = models.PositiveIntegerField(choices=REPORT_STATUSES, default=0)
    saved_data = models.TextField(null=True)

    def __unicode__(self):
        return unicode(_(self.reported_thing_title))
