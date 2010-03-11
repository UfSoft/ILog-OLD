# -*- coding: utf-8 -*-
# vim: sw=4 ts=4 fenc=utf-8 et
# ==============================================================================
# Copyright © 2010 UfSoft.org - Pedro Algarvio <ufs@ufsoft.org>
#
# License: BSD - Please view the LICENSE file for additional information.
# ==============================================================================

from os import listdir
from os.path import join, isfile
from babel.core import Locale, UnknownLocaleError
from babel.dates import get_timezone_location
from babel.support import Format, LazyProxy, Translations

from ilog.environment import LOCALE_DOMAIN, LOCALE_PATH

from pytz import common_timezones, timezone

class ILogTranslations(Translations):

    # Always use the unicode versions, we don't support byte strings
    gettext = Translations.ugettext
    ngettext = Translations.ungettext


def get_translations():
    """Return the translations set for the current request."""
    from ilog.application import get_request
    try:
        return get_request().translations
    except AttributeError:
        return None


def get_locale():
    """Return the locale set for the current request."""
    from ilog.application import get_request
    try:
        return get_request().locale
    except AttributeError:
        return None


def get_tzinfo():
    """Return the locale set for the current request."""
    from ilog.application import get_request
    try:
        return get_request().tz_info
    except AttributeError:
        return None


def gettext(string):
    """Translate a given string to the language of the current request."""
    translations = get_translations()
    if translations is None:
        return unicode(string)
    return translations.gettext(string)


def ngettext(singular, plural, n):
    """Translate the possible pluralised string to the language of the
    current request.
    """
    translations = get_translations()
    if translations is None:
        if n == 1:
            return unicode(singular)
        return unicode(plural)
    return translations.ngettext(singular, plural, n)


def lazy_gettext(string):
    """A lazy version of `gettext`."""
    if isinstance(string, LazyProxy):
        return string
    return LazyProxy(gettext, string)


def lazy_ngettext(singular, plural, n):
    """A lazy version of `ngettext`"""
    return LazyProxy(ngettext, singular, plural, n)


def __format_obj():
    from ilog.application import get_request
    current_request = get_request()
    if not hasattr(current_request, '_formats'):
        current_request._formats = Format(get_locale(), get_tzinfo())
    return current_request._formats


def format_date(date=None, format="medium"):
    """Return a date formatted according to the given pattern.

    >>> fmt = Format('en_US')
    >>> fmt.date(date(2007, 4, 1))
    u'Apr 1, 2007'

    :see: `babel.dates.format_date`
    """
    return __format_obj().date(date=None, format="medium")


def format_datetime(self, datetime=None, format='medium'):
    """Return a date and time formatted according to the given pattern.

    >>> from pytz import timezone
    >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
    >>> fmt.datetime(datetime(2007, 4, 1, 15, 30))
    u'Apr 1, 2007 11:30:00 AM'

    :see: `babel.dates.format_datetime`
    """
    return __format_obj().datetime(datetime, format, tzinfo=self.tzinfo,
                                   locale=self.locale)

def format_time(self, time=None, format='medium'):
    """Return a time formatted according to the given pattern.

    >>> from pytz import timezone
    >>> fmt = Format('en_US', tzinfo=timezone('US/Eastern'))
    >>> fmt.time(datetime(2007, 4, 1, 15, 30))
    u'11:30:00 AM'

    :see: `babel.dates.format_time`
    """
    return __format_obj().time(time, format, tzinfo=self.tzinfo,
                               locale=self.locale)

def format_timedelta(self, delta, granularity='second', threshold=.85):
    """Return a time delta according to the rules of the given locale.

    >>> fmt = Format('en_US')
    >>> fmt.timedelta(timedelta(weeks=11))
    u'3 months'

    :see: `babel.dates.format_timedelta`
    """
    return __format_obj().format_timedelta(delta, granularity=granularity,
                                           threshold=threshold,
                                           locale=self.locale)

def format_number(self, number):
    """Return an integer number formatted for the locale.

    >>> fmt = Format('en_US')
    >>> fmt.number(1099)
    u'1,099'

    :see: `babel.numbers.format_number`
    """
    return __format_obj().number(number)

def format_decimal(self, number, format=None):
    """Return a decimal number formatted for the locale.

    >>> fmt = Format('en_US')
    >>> fmt.decimal(1.2345)
    u'1.234'

    :see: `babel.numbers.format_decimal`
    """
    return __format_obj().decimal(number, format)

def format_currency(self, number, currency):
    """Return a number in the given currency formatted for the locale.

    :see: `babel.numbers.format_currency`
    """
    return __format_obj().currency(number, currency)

def format_percent(self, number, format=None):
    """Return a number formatted as percentage for the locale.

    >>> fmt = Format('en_US')
    >>> fmt.percent(0.34)
    u'34%'

    :see: `babel.numbers.format_percent`
    """
    return __format_obj().percent(number, format)

def format_scientific(self, number):
    """Return a number formatted using scientific notation for the locale.

    :see: `babel.numbers.format_scientific`
    """
    return __format_obj().scientific(number)

_  = gettext


FOUND_LANGUAGES = set(['en'])
KNOWN_LANGUAGES = [('en', Locale('en').display_name)]

def list_languages():
    for locale in listdir(LOCALE_PATH):
        if locale == 'en' or locale in FOUND_LANGUAGES:
            continue
        try:
            l = Locale.parse(locale)
        except (ValueError, UnknownLocaleError):
            continue

        mo_file = join(LOCALE_PATH, locale, 'LC_MESSAGES', 'messages.mo')
        if isfile(mo_file):
            KNOWN_LANGUAGES.append((str(l), l.display_name))
            FOUND_LANGUAGES.add(str(l))

    KNOWN_LANGUAGES.sort(key=lambda x: x[1].lower())
    return KNOWN_LANGUAGES[:]

def has_language(language):
    list_languages()
    return language in FOUND_LANGUAGES

LOADED_TRANSLATIONS = {}

def load_translations(locale):
    if locale not in LOADED_TRANSLATIONS:
        LOADED_TRANSLATIONS[locale] = ILogTranslations.load(LOCALE_PATH,
                                                            [locale],
                                                            LOCALE_DOMAIN)
    return LOADED_TRANSLATIONS[locale]

TIMEZONES = {}

def list_timezones(locale=None):
    from ilog.application import get_request
    if not locale:
        request = get_request()
        if not request:
            locale = 'en'
        else:
            locale = request.locale

    if str(locale) not in TIMEZONES:
        result = [(x, get_timezone_location(timezone(x), locale))
                  for x in common_timezones]
        result.sort(key=lambda x: x[1].lower())
        TIMEZONES[str(locale)] = result
    return TIMEZONES[str(locale)]
