"""
NPCS in the game.
"""
import random
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
