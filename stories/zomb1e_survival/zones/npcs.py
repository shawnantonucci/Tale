"""
NPCS in the game.
"""
import random
from tale import lang, util, mud_context
from typing import Optional
from tale.base import Living, Door, ParseResult, Item
from tale.player import Player
from tale.util import call_periodically, Context
from tale.errors import TaleError, ActionRefused, ParseError, StoryCompleted
from tale import lang, mud_context

            # A strange person wandering about the town, can kill the player if she's not careful to flee/run.
class Zombie(Living):
    def init(self):
        self.attacking = False

    def do_moan(self, ctx: util.Context) -> None:
        if random.random() < 0.3:
            self.location.tell("%s moans. better (run)." % lang.capital(self.title))
        else:
            target = random.choice(list(self.location.livings))
            if target is self:
                self.location.tell("%s grabs onto %sself." % (lang.capital(self.title), self.objective))
            else:
                title = lang.capital(self.title)
                self.location.tell("%s moans on %s." % (title, target.title),
                                   specific_targets={target}, specific_target_msg="%s grabs onto you." % title)

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

class Trader(Living):
    ammo_price = 10.0

    def init(self):
        super().init()
        self.verbs["buy"] = "Purchase something."
        self.verbs["sell"] = "Sell something."

    @property
    def description(self) -> str:
        if self.search_item("ammo", include_location=False):
            return "%s looks scared, and clenches a small bottle in %s hands." % (lang.capital(self.subjective), self.possessive)
        return "%s looks scared." % self.subjective

    @description.setter
    def description(self, value: str) -> None:
        raise TaleError("cannot set dynamic description")

    def handle_verb(self, parsed: ParseResult, actor: Living) -> bool:
        ammo = self.search_item("ammo", include_location=False)

        if parsed.verb == "buy":
            if not parsed.args:
                raise ParseError("Buy what?")
            if "ammo" in parsed.args or "bullets" in parsed.args:
                if not ammo:
                    raise ActionRefused("It is no longer available for sale.")
                self.do_buy_ammo(actor, ammo, self.ammo_price)
                return True
            if ammo:
                raise ParseError("The trader has ammo for your gun.")
            else:
                raise ParseError("There's nothing left to buy.")
        return False

    def do_buy_ammo(self, actor: Living, ammo: Item, price: float) -> None:
        if actor.money < price:
            raise ActionRefused("You don't have enough money!")
        actor.money -= price
        self.money += price
        ammo.move(actor, self)
        price_str = mud_context.driver.moneyfmt.display(price)
        actor.tell("After handing %s the %s, %s gives you the %s." % (self.objective, price_str, self.subjective, ammo.title))
        self.tell_others("{Actor} says: \"Here's your ammo, now get out of here!\"")

    def notify_action(self, parsed: ParseResult, actor: Living) -> None:
        if actor is self or parsed.verb in self.verbs:
            return  # avoid reacting to ourselves, or reacting to verbs we already have a handler for
        # react on mentioning the medicine
        if "bullets" in parsed.unparsed or "ammo" in parsed.unparsed:
            if self.search_item("ammo", include_location=False):  # do we still have the ammo?
                price = mud_context.driver.moneyfmt.display(self.ammo_price)
                self.tell_others("{Actor} clenches the bottle %s's holding even tighter. %s says: "
                                 "\"You won't get them for free! They will cost you %s!\""
                                 % (self.subjective, lang.capital(self.subjective), price))
            else:
                self.tell_others("{Actor} says: \"Good luck with it!\"")
        if random.random() < 0.5:
            actor.tell("%s glares at you." % lang.capital(self.title))
