"""
The house, where the player starts the game.
Their pet cat is also here and you can interact with him a little.

The generated demo code below is provided for you to use or modify as you wish.
(it creates a trivial location similar to the built-in demo story of the Tale library itself)
"""

import random

from tale.base import Location, Exit, Door, Key, Living, ParseResult
from tale.errors import StoryCompleted
from tale.lang import capital
from tale.player import Player
from tale.util import call_periodically, Context
from tale.items.basic import elastic_band, woodenYstick
from tale.verbdefs import AGGRESSIVE_VERBS
# from npcs import Zombie


# define the various locations

class GameEnd(Location):
    def notify_player_arrived(self, player: Player, previous_location: Location) -> None:
        # player has entered, and thus the story ends
        player.tell("\n")
        player.tell("\n")
        player.tell("<bright>Congratulations on escaping the house!</> Someone else has to look after Garfield now though...")
        raise StoryCompleted

# Rooms
livingroom = Location("Living room", "The living room in your home in the outskirts of the city.")
bedroom = Location("Bed room", "A small bedroom with a single bed an a T.V in the corner.")
closet = Location("Closet", "A small room.")
outside = GameEnd("Outside", "It is beautiful weather outside.")


# define the exits that connect the locations

door = Door(
    ["garden", "door"], outside,
    "A door leads to the garden.", "There's a heavy door here that leads to the garden outside the house.",
    locked=True, opened=False, key_code="1")    # oneway door, once outside you're finished, so no reason to go back in
livingroom.add_exits([door])

Exit.connect(livingroom, "closet", "There's a small closet in your house.", None,
             closet, ["living room", "back"], "You can see the living room where you came from.", None)

Exit.connect(livingroom, "bedroom", "There is a bedroom to your left", None,
            bedroom, ["living room", "back"], "The living room is where you came from", None)


# define items and NPCs

class Cat(Living):
    def init(self) -> None:
        self.aliases = {"cat"}

    @call_periodically(1, 60)
    def do_purr(self, ctx: Context) -> None:
        if random.random() > 0.7:
            self.location.tell("%s purrs happily." % capital(self.title))
        else:
            self.location.tell("%s yawns sleepily." % capital(self.title))
        # it's possible to stop the periodical calling by setting:  call_periodically(0)(Cat.do_purr)

    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        if actor is self or parsed.verb in self.verbs:
            return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        if parsed.verb in ("pet", "stroke", "tickle", "cuddle", "hug", "caress", "rub"):
            self.tell_others("{Actor} curls up in a ball and purrs contently.")
        elif parsed.verb in AGGRESSIVE_VERBS:
            if self in parsed.who_info:   # only give aggressive response when directed at the cat.
                self.tell_others("{Actor} hisses! I wouldn't make %s angry if I were you!" % self.objective)
        elif parsed.verb in ("hello", "hi", "greet", "meow", "purr"):
            self.tell_others("{Actor} stares at {target} incomprehensibly.", target=actor)
        else:
            message = (parsed.message or parsed.unparsed).lower().split()
            if self.name in message or "cat" in message:
                self.tell_others("{Actor} looks up at {target} and wiggles %s tail." % self.possessive, target=actor)

class Zombie(Living):
    def init(self):
        self.attacking = False

    @call_periodically(10, 20)
    def do_wander(self, ctx: Context) -> None:
        if not self.attacking:
            # Let the mob wander randomly.
            direction = self.select_random_move()
            if direction:
                self.move(direction.target, self, direction_names=direction.names)

    @call_periodically(4, 10)
    def do_attack(self, ctx: Context) -> None:
        if not self.attacking:
            for liv in self.location.livings:
                if isinstance(liv, Player):
                    self.start_attack(liv)
                    liv.tell("It may be a good idea to run away!")
                    self.attacking = True
                    ctx.driver.defer(5, self.kill_player, liv)      # give player a moment to react to the attack
                    break

    def kill_player(self, player: Player, ctx: Context) -> None:
        # player can only be killed if she is still here, obviously
        if self.attacking and player in self.location.livings:
            player.tell_text_file(ctx.resources["messages/completion_failed.txt"])
            raise StoryCompleted
        self.attacking = False


cat = Cat("garfield", "m", race="cat", descr="A very obese cat, orange and black. It looks tired, but glances at you happily.")
livingroom.insert(cat, None)

zombie =  w = Zombie("zombie", random.choice("mf"), descr="A person staring blankly somewhere.")
livingroom.insert(zombie, None)

key = Key("key", "small rusty key", descr="This key is small and rusty. It has a label attached, reading \"garden door\".")
key.key_for(door)
closet.insert(key, None)

closet.insert(woodenYstick.clone(), None)
livingroom.insert(elastic_band.clone(), None)
