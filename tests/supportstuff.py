"""
Unittest support stuff

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import datetime
from typing import Any
from tale import pubsub, util, driver, base


class Thing:
    def __init__(self):
        self.x = []

    def append(self, value, ctx):
        assert ctx.driver is not None and isinstance(ctx.driver, TestDriver)
        self.x.append(value)


class TestDriver(driver.Driver):
    def __init__(self):
        super().__init__()
        # fix up some essential attributes on the driver that are normally only present after loading a story file
        self.game_clock = util.GameDateTime(datetime.datetime.now())


class Wiretap(pubsub.Listener):
    def __init__(self, target):
        self.clear()
        tap = target.get_wiretap()
        tap.subscribe(self)

    def pubsub_event(self, topicname, event):
        sender, message = event
        self.msgs.append((sender, message))
        self.senders.append(sender)

    def clear(self):
        self.msgs = []
        self.senders = []


class MsgTraceNPC(base.Living):
    def init(self):
        self._init_called = True
        self.clearmessages()

    def clearmessages(self):
        self.messages = []

    def tell(self, message: Any, *, end: bool=False, format: bool=True) -> base.Living:
        self.messages.append(message)
        return self
