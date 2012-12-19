"""
Utility stuff

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

from __future__ import absolute_import, print_function, division, unicode_literals
import datetime
import random
import os
import time
import sys
import copy
from . import lang
from .errors import ParseError

if sys.version_info < (3, 0):
    basestring_type = basestring
    import Queue as queue

    def next_iter(iterable):
        return iterable.next()
else:
    basestring_type = str
    import queue

    def next_iter(iterable):
        return next(iterable)


def roll_die(number=1, sides=6):
    """rolls a number (max 20) of dice with configurable number of sides"""
    assert 1 <= number <= 20
    values = [random.randint(1, sides) for _ in range(number)]
    return sum(values), values


def print_object_location(player, obj, container, print_parentheses=True):
    if not container:
        if print_parentheses:
            player.tell("(It's not clear where %s is)." % obj.name)
        else:
            player.tell("It's not clear where %s is." % obj.name)
        return
    if container in player:
        if print_parentheses:
            player.tell("(%s was found in %s, in your inventory)." % (obj.name, container.title))
        else:
            player.tell("%s was found in %s, in your inventory." % (lang.capital(obj.name), container.title))
    elif container is player.location:
        if print_parentheses:
            player.tell("(%s was found in your current location)." % obj.name)
        else:
            player.tell("%s was found in your current location." % lang.capital(obj.name))
    elif container is player:
        if print_parentheses:
            player.tell("(%s was found in your inventory)." % obj.name)
        else:
            player.tell("%s was found in your inventory." % lang.capital(obj.name))
    else:
        if print_parentheses:
            player.tell("(%s was found in %s)." % (obj.name, container.name))
        else:
            player.tell("%s was found in %s." % (lang.capital(obj.name), container.name))


class MoneyFormatter(object):
    """Display and parsing of money. Supports 'fantasy' and 'modern' style money."""
    money_words_fantasy = {"gold", "silver", "copper", "coppers"}
    money_words_modern = {"dollar", "dollars", "cent", "cents"}

    def __init__(self, money_type):
        if money_type == "fantasy":
            self.display = self.money_display_fantasy
            self.money_to_float = self.money_to_float_fantasy
            self.money_words = self.money_words_fantasy
        elif money_type == "modern":
            self.display = self.money_display_modern
            self.money_to_float = self.money_to_float_modern
            self.money_words = self.money_words_modern
        else:
            raise ValueError("invalid money type " + money_type)

    def money_display_fantasy(self, amount, short=False, zero_msg="nothing"):
        """
        Display amount of money in gold/silver/copper units,
        base unit=silver, 10 silver=1 gold, 0.1 silver=1 copper
        """
        gold, amount = divmod(amount, 10.0)
        silver, copper = divmod(amount, 1.0)
        copper = round(copper * 10.0)
        if short:
            return "%dg/%ds/%dc" % (gold, silver, copper)
        result = []
        if gold:
            result.append("%d gold" % gold)
        if silver:
            result.append("%d silver" % silver)
        if copper:
            result.append("%d copper" % copper)
        if result:
            return lang.join(result)
        return zero_msg

    def money_display_modern(self, amount, short=False, zero_msg="nothing"):
        """
        Display amount of money in modern currency (dollars/cents).
        """
        if short:
            return "$ %.2f" % amount
        dollar, cents = divmod(amount, 1.0)
        cents = round(cents * 100.0)
        result = []
        if dollar:
            result.append("%d dollar" % dollar)
        if cents:
            result.append("%d cent" % cents)
        if result:
            return lang.join(result)
        return zero_msg

    def money_to_float_fantasy(self, coins):
        """Either a dictionary containing the values per coin type, or a string '11g/22s/33c' is converted to float."""
        if type(coins) is not dict:
            if not coins:
                raise ValueError("That's not an amount of money.")
            result = 0.0
            while coins:
                c, _, coins = coins.partition("/")
                try:
                    if c.endswith("g"):
                        result += float(c[:-1]) * 10.0
                    elif c.endswith("s"):
                        result += float(c[:-1])
                    elif c.endswith("c"):
                        result += float(c[:-1]) / 10.0
                    else:
                        raise ValueError("invalid coin letter")
                except ValueError:
                    raise ValueError("That's not an amount of money.")
            return result
        result = coins.get("gold", 0.0) * 10.0
        result += coins.get("silver", 0.0)
        result += coins.get("copper", 0.0) / 10.0
        result += coins.get("coppers", 0.0) / 10.0
        return result

    def money_to_float_modern(self, coins):
        """Either a dictionary containing the values per coin type, or a string '$1234.55' is converted to float."""
        if type(coins) is not dict:
            if coins.startswith("$"):
                return float(coins[1:])
            else:
                raise ValueError("That's not an amount of money.")
        result = coins.get("dollar", 0.0)
        result += coins.get("dollars", 0.0)
        result += coins.get("cent", 0.0) / 100.0
        result += coins.get("cents", 0.0) / 100.0
        return result

    def parse(self, words):
        """Convert a parsed sequence of words to the amount of money it represents (foat)"""
        if len(words) == 1:
            try:
                return self.money_to_float(words[0])
            except ValueError:
                pass
        elif len(words) == 2:
            try:
                return self.money_to_float(words[0] + words[1])
            except ValueError:
                pass
        coins = {}
        for word in words:
            if word in self.money_words:
                # check if all words are either a number (currency) or a moneyword
                amount = None
                for word in words:
                    if word in self.money_words:
                        if amount:
                            if word in coins:
                                raise ParseError("What amount?")
                            coins[word] = amount
                            amount = None
                        else:
                            raise ParseError("What amount?")
                    else:
                        try:
                            amount = float(word)
                        except ValueError:
                            raise ParseError("What amount?")
                return self.money_to_float(coins)
        raise ParseError("That is not an amount of money.")


def get_motd(vfs):
    """
    Read the MOTD from its fixed location, and return it and its modification timestamp.
    If it's not there, return None for both.
    """
    try:
        with vfs.open_read("messages/motd.txt") as motd:
            message = motd.read().rstrip()
            if not message:
                return None, None
            mtime = os.fstat(motd.fileno()).st_mtime
            mtime = time.asctime(time.localtime(mtime))
            return message, mtime
    except IOError:
        return None, None


def message_nearby_locations(source_location, message):
    """Yells a message to adjacent locations."""
    if source_location.exits:
        yelled_locations = set()
        for exit in source_location.exits.values():
            if exit.target in yelled_locations:
                continue   # skip double locations (possible because there can be multiple exits to the same location)
            if exit.target is not source_location:
                exit.target.tell(message)
                yelled_locations.add(exit.target)
                for direction, return_exit in exit.target.exits.items():
                    if return_exit.target is source_location:
                        if direction in {"north", "east", "south", "west", "northeast", "northwest", "southeast",
                                         "southwest", "left", "right", "front", "back"}:
                            direction = "the " + direction
                        elif direction in {"up", "above", "upstairs"}:
                            direction = "above"
                        elif direction in {"down", "below", "downstairs"}:
                            direction = "below"
                        else:
                            continue  # no direction description possible for this exit
                        exit.target.tell("The sound is coming from %s." % direction)
                        break
                else:
                    exit.target.tell("You can't hear where the sound is coming from.")


def parse_time(args):
    """parses a time from args like: 13:44:59, or like a duration such as 1h 30m 15s"""
    try:
        duration = parse_duration(args)
        return (datetime.datetime.min + duration).time()
    except ParseError:
        if not args or len(args) > 1:
            raise ParseError("It's not clear what time you mean.")
        try:
            return datetime.datetime.strptime(args[0], "%H:%M:%S").time()
        except ValueError:
            try:
                return datetime.datetime.strptime(args[0], "%H:%M").time()
            except ValueError:
                if args[0] == "noon":
                    return datetime.time(hour=12)
                elif args[0] == "midnight":
                    return datetime.time(hour=0)
                elif args[0] in ("sunrise", "dawn"):
                    return datetime.time(hour=6)
                elif args[0] in ("sunset", "dusk"):
                    return datetime.time(hour=20)
                elif args[0] in ("evening", "morning", "later", "earlier", "future", "past"):
                    raise ParseError("You must be more specific about the time you mean.")
                else:
                    raise ParseError("It's not clear what time you mean.")


def parse_duration(args):
    """parses a duration from args like: 1 hour 20 minutes 15 seconds (hour/h, minutes/min/m, seconds/sec/s)"""
    hours = minutes = seconds = 0
    if args:
        number = None
        for arg in args:
            if len(arg) >= 2 and arg.endswith(("h", "m", "s")):
                try:
                    if arg[-1] == "h":
                        hours = int(arg[:-1])
                    elif arg[-1] == "m":
                        minutes = int(arg[:-1])
                    elif arg[-1] == "s":
                        seconds = int(arg[:-1])
                    continue
                except ValueError:
                    pass
            if arg in ("hours", "hour", "h"):
                hours = number
                number = None
            elif arg in ("minutes", "minute", "min", "m"):
                minutes = number
                number = None
            elif arg in ("seconds", "second", "sec", "s"):
                seconds = number
                number = None
            else:
                try:
                    number = float(arg)
                except ValueError:
                    raise ParseError("It's not clear what duration you mean.")
    if hours == minutes == seconds == 0:
        raise ParseError("It's not clear what duration you mean.")
    try:
        return datetime.timedelta(hours=hours, minutes=minutes, seconds=seconds)
    except TypeError:
        raise ParseError("It's not clear what duration you mean.")


def duration_display(duration):
    secs = duration.total_seconds()
    if secs == 0:
        return "no time at all"
    hours, secs = divmod(secs, 3600)
    minutes, secs = divmod(secs, 60)
    result = []
    if hours == 1:
        result.append("1 hour")
    elif hours > 1:
        result.append("%d hours" % hours)
    if minutes == 1:
        result.append("1 minute")
    elif minutes > 1:
        result.append("%d minutes" % minutes)
    if secs == 1:
        result.append("1 second")
    elif secs > 1:
        result.append("%d seconds" % secs)
    return lang.join(result)


def format_docstring(docstring):
    """Format a docstring according to the algorithm in PEP-257"""
    if not docstring:
        return ''
    # Convert tabs to spaces (following the normal Python rules)
    # and split into a list of lines:
    lines = docstring.expandtabs().splitlines()
    # Determine minimum indentation (first line doesn't count):
    indent = sys.maxsize
    for line in lines[1:]:
        stripped = line.lstrip()
        if stripped:
            indent = min(indent, len(line) - len(stripped))
    # Remove indentation (first line is special):
    trimmed = [lines[0].strip()]
    if indent < sys.maxsize:
        for line in lines[1:]:
            trimmed.append(line[indent:].rstrip())
    # Strip off trailing and leading blank lines:
    while trimmed and not trimmed[-1]:
        trimmed.pop()
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    # Return a single string:
    return '\n'.join(trimmed)


def clone(object):
    """Create a copy of an existing MudObject"""
    return copy.deepcopy(object)


class GameDateTime(object):
    """
    The datetime class that tracks game time.
    times_realtime means how much faster the game time is running than real time.
    """
    def __init__(self, datetime, times_realtime=1):
        assert times_realtime >= 0
        self.times_realtime = times_realtime
        self.clock = datetime

    def __str__(self):
        return str(self.clock)

    def add_gametime(self, timedelta):
        """advance the game clock by a time delta expressed in game time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock += timedelta

    def sub_gametime(self, timedelta):
        """rewind the game clock by a time delta expressed in game time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock -= timedelta

    def plus_realtime(self, timedelta):
        """return the game clock plus a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        return self.clock + timedelta * self.times_realtime

    def minus_realtime(self, timedelta):
        """return the game clock minus a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        return self.clock - timedelta * self.times_realtime

    def add_realtime(self, timedelta):
        """advance the game clock by a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock += timedelta * self.times_realtime

    def sub_realtime(self, timedelta):
        """rewind the game clock by a time delta expressed in real time"""
        assert isinstance(timedelta, datetime.timedelta)
        self.clock -= timedelta * self.times_realtime


def input_confirm(question, player):
    """
    Simple wrapper around player.input to ask the player for a yes/no confirmation. Returns True or False.
    """
    if not question.endswith(" "):
        question += " "
    while True:
        reply = player.input(question)
        if reply in ("y", "yes", "sure", "yep", "yeah"):
            return True
        if reply in ("n", "no", "nope"):
            return False
        if reply:
            player.tell("That is not a valid answer.")


def input_choice(question, choices, player):
    """
    Simple wrapper around player.input to ask the player for a choice from a set of options.
    You can optionally use the format string '{choices}' to get the list of choices in the question text.
    """
    question = question.format(choices="/".join(choices))
    if not question.endswith(" "):
        question += " "
    while True:
        reply = player.input(question)
        if reply in choices:
            return reply
        if reply:
            player.tell("That is not a valid answer.")


class AttrDict(dict):
    """A dict-like object that supports accessing its members as attributes."""
    def __init__(self, *vargs, **kwargs):
        if vargs:
            assert len(vargs) == 1
            assert not kwargs
            source = vargs[0]
            assert isinstance(source, dict)
        else:
            source = kwargs
        dict.__init__(self, source)
        self.__dict__.update(source)

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.__dict__[key] = value


class Context(AttrDict):
    """The context used for every command function and obj.destroy"""
    driver = None
    clock = None
    config = None
    state = None
