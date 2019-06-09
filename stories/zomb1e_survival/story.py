#! /usr/bin/env python3
"""
'Zomb1e Survival'
by Shawn Antonucci - shawnantonucci6688@gmail.com
"""

import datetime
import sys
from typing import Optional

from tale.driver import Driver
from tale.player import Player
from tale.story import *


class Story(StoryBase):
    # Create your story configuration and customize it here.
    # Look at the options in StoryConfig to see what you can change.
    config = StoryConfig()
    config.name = "Zomb1e Survival"
    config.author = "Shawn Antonucci"
    config.author_address = "shawnantonucci6688@gmail.com"
    config.version = "1.0"
    config.requires_tale = "4.6"
    config.supported_modes = {GameMode.IF}
    # config.supported_modes = {GameMode.MUD}
    config.money_type = MoneyType.MODERN
    config.player_money = 100.0
    config.player_name = "TwistedZiefer"
    config.player_gender = "m"
    config.playable_races = {"human"}
    config.startlocation_player = "house.livingroom"
    config.zones = ["house", "outside_home"]
    config.server_tick_method = TickMethod.TIMER
    config.server_tick_time = 1.0
    config.gametime_to_realtime = 5
    config.display_gametime = True
    config.epoch = datetime.datetime(2015, 5, 14, 14, 0, 0)       # start date/time of the game clock\
    config.savegames_enabled = True
    config.show_exits_in_look = True
    config.mud_host = "localhost"
    config.mud_port = 1234
    config.license_file = "messages/license.txt"
    # Your story-specific configuration fields should be added below.
    # You can override various methods of the StoryBase class,
    # have a look at the Tale example stories to learn how you can use these.

    driver = None     # will be set by init()

    def init(self, driver: Driver) -> None:
        """Called by the game driver when it is done with its initial initialization."""
        self.driver = driver

    def init_player(self, player: Player) -> None:
        """
        Called by the game driver when it has created the player object (after successful login).
        You can set the hint texts on the player object, or change the state object, etc.
        """
        pass

    def welcome(self, player: Player) -> str:
        """
        Welcome text when player enters a new game
        If you return a string, it is used as an input prompt before continuing (a pause).
        """
        player.tell("<bright>Hello, %s!</> Welcome to the land of `%s'.  May your visit here be... interesting."
                    % (player.title, self.config.name), end=True)
        player.tell("--", end=True)
        return ""

    def welcome_savegame(self, player: Player) -> str:
        """
        Welcome text when player enters the game after loading a saved game
        If you return a string, it is used as an input prompt before continuing (a pause).
        """
        player.tell("<bright>Welcome back to `%s'.</>" % self.config.name, end=True)
        player.tell("\n")
        # player.tell_text_file(self.driver.resources["messages/welcome.txt"])
        # player.tell_text_file(self.driver.resources["messages/motd.txt"])
        player.tell("\n")
        return "<bright>Press enter to continue where you were before.</>"


if __name__ == "__main__":
    # story is invoked as a script, start it.
    from tale.main import run_from_cmdline
    run_from_cmdline(["--game", sys.path[0]])

