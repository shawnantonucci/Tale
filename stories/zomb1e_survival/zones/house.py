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
from zones.npcs import Trader, Zombie

# define the various locations

class GameEnd(Location):
    @call_periodically(30, 60)
    def spawn_zombie(self, ctx: Context) -> None:
        w = Zombie("blankly staring person", random.choice("mf"), descr="A person staring blankly somewhere.")
        w.aliases = {"person", "staring person"}
        w.move(self)

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
outside = GameEnd("Outside", "It is beautiful weather outside.")


# define the exits that connect the locations

door = Door(
    ["garden", "door"], outside,
    "A door leads to the garden.", "There's a heavy door here that leads to the garden outside the house.\n",
    locked=True, opened=False, key_code="1")    # oneway door, once outside you're finished, so no reason to go back in
livingroom.add_exits([door])

Exit.connect(livingroom, "closet", "There's a small closet in your house.", None,
             closet, ["living room", "back"], "You can see the living room where you came from.", None)

Exit.connect(livingroom, "bedroom", "There is a bedroom to your left", None,
            bedroom, ["living room", "back"], "The living room is where you came from", None)


# define items and NPCs

class Bird(Living):
    def init(self) -> None:
        self.aliases = {"bird"}

    @call_periodically(1, 90)
    def do_purr(self, ctx: Context) -> None:
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

zombie =  w = Zombie("zombie", random.choice("mf"), descr="A person staring blankly somewhere.")
livingroom.insert(zombie, None)

key = Key("key", "small rusty key", descr="This key is small and rusty. It has a label attached, reading \"garden door\".")
key.key_for(door)
closet.insert(key, None)

closet.insert(woodenYstick.clone(), None)
livingroom.insert(elastic_band.clone(), None)

trader = Trader("Old man", "m", title="Old man")
trader.extra_desc["bullets"] = "It is a a box of rounds with 5 bullets in it for your gun."
trader.extra_desc["ammo"] = trader.extra_desc["bullets"]
trader.aliases.add("trader")

# ammo
ammo = Item("ammo", "5 pistol bullets", descr="It looks like the ammo for your gun.")
ammo.value = Trader.ammo_price
ammo.aliases = {"bullets", "ammo"}
trader.init_inventory([ammo])
closet.insert(trader, None)
