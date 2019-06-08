"""
The house, where the player starts the game.
Their pet cat is also here and you can interact with him a little.

The generated demo code below is provided for you to use or modify as you wish.
(it creates a trivial location similar to the built-in demo story of the Tale library itself)
"""

import random

from tale.base import Location, Exit, Door, Key, Living, ParseResult, Item
from tale.errors import StoryCompleted
from tale.lang import capital
from tale.player import Player
from tale.util import call_periodically, Context
from tale.items.basic import elastic_band, woodenYstick
from tale.verbdefs import AGGRESSIVE_VERBS

# define the various locations

class GameEnd(Location):

    def notify_player_arrived(self, player: Player, previous_location: Location) -> None:
        # player has entered, and thus the story ends
        player.tell("\n")
        player.tell("\n")
        player.tell("<bright>Congratulations on escaping the house!</> Someone else has to look after the parakeet now though...")
        raise StoryCompleted

# Rooms
livingroom = Location("Living room", "The living room in your home in the outskirts of the city.")
bedroom = Location("Bed room", "A small bedroom with a single bed an a T.V in the corner.")
closet = Location("Closet", "A small room.")
# outside = Location("Outside", "Outside is Lake drive.")


# define the exits that connect the locations

Exit.connect(livingroom, "closet", "There's a small closet in your house.", None,
             closet, ["living room", "back"], "You can see the living room where you came from.", None)

Exit.connect(livingroom, "bedroom", "There is a bedroom to your left", None,
            bedroom, ["living room", "back"], "The living room is where you came from", None)

# define items and NPCs

class Bird(Living):
    def init(self) -> None:
        self.aliases = {"bird"}

    @call_periodically(1, 50)
    def do_birdaction(self, ctx: Context) -> None:
        if random.random() > 0.7:
            self.location.tell("%s chirps." % capital(self.title))
        else:
            self.location.tell("%s flys around the room." % capital(self.title))
        # it's possible to stop the periodical calling by setting:  call_periodically(0)(Cat.do_purr)

    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        if actor is self or parsed.verb in self.verbs:
            return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        if parsed.verb in ("pet", "stroke", "tickle", "cuddle", "caress", "rub"):
            self.tell_others("{Actor} Gets excited and dances around chirping.")
        elif parsed.verb in AGGRESSIVE_VERBS:
            if self in parsed.who_info:   # only give aggressive response when directed at the cat.
                self.tell_others("{Actor} latches onto you and bites you. He backs away from you." % self.objective)
        elif parsed.verb in ("hello", "hi", "greet", "chirp"):
            self.tell_others("{Actor} stares at {target} incomprehensibly.", target=actor)
        else:
            message = (parsed.message or parsed.unparsed).lower().split()
            if self.name in message or "bird" in message:
                self.tell_others("{Actor} looks up at {target} and tilts %s tail." % self.possessive, target=actor)


bird = Bird("Parakeet", "m", race="bird", descr="A small bird flapping around the room.")
livingroom.insert(bird, None)
