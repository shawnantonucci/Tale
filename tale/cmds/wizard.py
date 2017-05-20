"""
Wizard commands.

'Tale' mud driver, mudlib and interactive fiction framework
Copyright by Irmen de Jong (irmen@razorvine.net)
"""

import datetime
import inspect
import functools
import sys
import gc
import platform
import importlib
from typing import Dict, Callable, Generator
from .decorators import disabled_in_gamemode, cmdfunc_signature_valid
from ..errors import SecurityViolation, ParseError, ActionRefused, NonSoulVerb
from ..player import Player
from ..parseresult import ParseResult
from ..story import *
from .. import base, lang, util, pubsub, __version__

all_commands = {}   # type: Dict[str, Callable]
LIBRARY_MODULE_NAME = "tale"


def wizcmd(command: str, *aliases: str) -> Callable:
    """
    (Internal) decorator to add the command to the global dictionary of commands, with a privilege check wrapper.
    Note that the wizard command (and the aliases) are prefixed by a '!' to make them stand out from normal commands.
    User code should use @wizcmd from cmds.decorators.
    """
    # NOTE: this shares quite some lines of code with cmds.decorators, be sure to keep them in sync
    prefixed_command = "!" + command
    prefixed_aliases = ["!" + alias for alias in aliases]

    def wizcmd2(func: Callable) -> Callable:
        func.enable_notify_action = False   # type: ignore  # none of the wizard commands should be used with notify_action
        func.is_tale_command_func = True    # type: ignore
        func.is_generator = inspect.isgeneratorfunction(func)   # type: ignore  # contains async yields?

        @functools.wraps(func)
        def executewizcommand(player: Player, parsed: ParseResult, ctx: util.Context) \
                -> Callable[[Player, ParseResult, util.Context], None]:
            if "wizard" not in player.privileges:
                raise SecurityViolation("Wizard privilege required for verb " + parsed.verb)
            return func(player, parsed, ctx)

        if prefixed_command in all_commands:
            raise ValueError("Command defined more than once: " + prefixed_command)
        if cmdfunc_signature_valid(func):
            func.__doc__ = util.format_docstring(func.__doc__)
            all_commands[prefixed_command] = executewizcommand
            for alias in prefixed_aliases:
                if alias in all_commands:
                    raise ValueError("Command defined more than once: " + alias)
                all_commands[alias] = executewizcommand
            return executewizcommand
        else:
            raise SyntaxError("invalid wizcmd function signature or missing docstring: " + func.__name__)
    return wizcmd2


@wizcmd("ls")
def do_ls(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """List the contents of a module path under the library tree (try !ls .items.basic)
or in the story's zone module (try !ls zones)"""
    p = player.tell
    if not parsed.args:
        raise ParseError("ls what path?")
    path = parsed.args[0]
    if path == "zones" or path.startswith("zones."):
        module_name = path
    elif path.startswith("."):
        module_name = LIBRARY_MODULE_NAME
        if len(path) > 1:
            module_name += path
    else:
        raise ActionRefused("Path must start with '.' or 'zones'")
    try:
        module = importlib.import_module(module_name)
    except (ImportError, ValueError):
        raise ActionRefused("There's no module named " + path)
    p("<%s>" % path, end=True)
    m_items = vars(module).items()
    modules = [x[0] for x in m_items if inspect.ismodule(x[1])]
    classes = [x[0] for x in m_items if type(x[1]) is type and issubclass(x[1], base.MudObject)]
    items = [x[0] for x in m_items if isinstance(x[1], base.Item)]
    livings = [x[0] for x in m_items if isinstance(x[1], base.Living)]
    locations = [x[0] for x in m_items if isinstance(x[1], base.Location)]
    if locations:
        p("Locations: " + ", ".join(locations), end=True)
    if livings:
        p("Livings: " + ", ".join(livings), end=True)
    if items:
        p("Items: " + ", ".join(items), end=True)
    if modules:
        p("Submodules: " + ", ".join(modules), end=True)
    if classes:
        p("Classes: " + ", ".join(classes), end=True)


@wizcmd("clone")
def do_clone(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Clone an item or living directly from the room or inventory, or from an object in the module path"""
    # XXX missing actor bug
    # XXX support 'zones' path element just like ls
    if not parsed.args:
        raise ParseError("Clone what?")
    path = parsed.args[0]
    if path.startswith("."):
        # find an item somewhere in a module path
        # XXX don't duplicat this from ls command
        path, objectname = path.rsplit(".", 1)
        if not objectname:
            raise ActionRefused("Invalid object path")
        try:
            module_name = LIBRARY_MODULE_NAME
            if len(path) > 1:
                module_name += path
            module = importlib.import_module(module_name)
            obj = getattr(module, objectname, None)
        except (ImportError, ValueError):
            raise ActionRefused("There's no module named " + path)
    elif parsed.who_order:
        obj = parsed.who_order[0]
    else:
        raise ActionRefused("Object not found")
    obj.wiz_clone(player)  # actually clone it


@wizcmd("destroy")
def do_destroy(player: Player, parsed: ParseResult, ctx: util.Context) -> Generator:
    """Destroys an object or creature."""
    if not parsed.who_order:
        raise ParseError("Destroy what or who?")
    if parsed.unrecognized:
        raise ParseError("It's not clear what you mean by: " + ",".join(parsed.unrecognized))
    for victim in parsed.who_info:
        if not (yield "input", ("Are you sure you want to destroy %s?" % victim.title, lang.yesno)):
            player.tell("You leave %s be." % victim.subjective)
            continue
        victim.wiz_destroy(player, ctx)  # actually destroy it
        player.tell("You destroyed %r." % victim)
        player.tell_others("{Title} makes some gestures and a tiny black hole appears.\n"
                           "%s disappears in it, and the black hole immediately vanishes." % lang.capital(victim.title))


@wizcmd("clean")
def do_clean(player: Player, parsed: ParseResult, ctx: util.Context) -> Generator:
    """Destroys all objects contained in something or someones inventory, or the current location (.)"""
    p = player.tell
    if parsed.args and parsed.args[0] == '.':
        # clean the current location
        p("Cleaning the stuff in your environment.")
        player.tell_others("{Title} cleans out the environment.")
        for item in set(player.location.items):
            player.location.remove(item, player)
            item.destroy(ctx)
        for living in set(player.location.livings):
            if not isinstance(living, Player):
                player.location.remove(living, player)
                living.destroy(ctx)
        if player.location.items:
            p("Some items refused to be destroyed!")
    else:
        if len(parsed.who_order) != 1:
            raise ParseError("Clean what or who?")
        victim = parsed.who_order[0]
        if (yield "input", ("Are you sure you want to clean out %s?" % victim.title, lang.yesno)):
            p("Cleaning inventory of %s." % victim)
            player.tell_others("{Title} cleans out the inventory of %s." % victim.title)
            items = victim.inventory
            for item in items:
                victim.remove(item, player)
                item.destroy(ctx)
                p("destroyed %s" % item)
            if victim.inventory_size:
                p("Some items refused to be destroyed!")
        else:
            p("You leave %s be." % victim.subjective)


@wizcmd("pdb")
@disabled_in_gamemode(GameMode.MUD)
def do_pdb(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Starts a Python debugging session. (Only available in IF mode)"""
    ctx.conn.pause()
    print("----------Entering PDB debugger session----------")
    import pdb
    pdb.set_trace()
    print("----------Leaving PDB debugger session----------")
    ctx.conn.pause(unpause=True)


@wizcmd("wiretap")
def do_wiretap(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Adds a wiretap to something to overhear the messages they receive.
'wiretap .' taps the room, 'wiretap name' taps a creature with that name,
'wiretap -clear' gets rid of all taps."""
    if not parsed.args:
        raise ActionRefused("Wiretap who?")
    arg = parsed.args[0]
    if arg == ".":
        player.create_wiretap(player.location)
        player.tell("Wiretapped room '<location>%s</>'." % player.location.name)
    elif arg == "-clear":
        player.clear_wiretaps()
        player.tell("All wiretaps removed.")
    elif parsed.who_order:
        for living in parsed.who_order:
            if living is player:
                raise ActionRefused("Can't wiretap yourself.")
            if isinstance(living, base.Item):
                raise ActionRefused("Can't wiretap an item, try a living being or a location instead.")
            player.create_wiretap(living)
            player.tell("Wiretapped <living>%s</>." % living.name)
    else:
        raise ActionRefused("Wiretap who?")


@wizcmd("teleport", "teleport_to")
def do_teleport(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Teleport to a location or creature, or teleport a creature to you.
'!teleport[_to] .module.path.to.object' teleports [to] that object (location or creature).
'!teleport[_to] playername' teleports [to] that player.
'!teleport_to zones.zonename.locationname' teleports to the given location in a zone from the story.
'!teleport_to @start' teleports you to the starting location for wizards."""
    if not parsed.args:
        raise ActionRefused("Teleport what to where?")
    args = parsed.args
    teleport_self = parsed.verb == "!teleport_to"
    if args[0].startswith(".") or args[0] == "zones" or args[0].startswith("zones."):
        # teleport the wizard to a location somewhere in a module path
        # XXX don't copy this from ls command?
        path, objectname = args[0].rsplit(".", 1)
        if not objectname:
            raise ActionRefused("Invalid object path")
        try:
            if path.startswith("."):
                module_name = LIBRARY_MODULE_NAME
                if len(path) > 1:
                    module_name += path
            else:
                module_name = path
            module = importlib.import_module(module_name)
        except (ImportError, ValueError):
            raise ActionRefused("There's no module named " + path)
        target = getattr(module, objectname, None)
        if not target:
            raise ActionRefused("Object not found")
        if teleport_self:
            if isinstance(target, base.Living):
                target = target.location  # teleport to target living's location
            if not isinstance(target, base.Location):
                raise ActionRefused("Can't determine location to teleport to.")
            teleport_to(player, target)
        else:
            if isinstance(target, base.Location):
                raise ActionRefused("Can't teleport a room here, maybe you wanted to teleport TO somewhere?")
            teleport_someone_to_player(target, player)
    else:
        # target is a player (or @start - the wizard starting location)
        if args[0] == "@start":
            teleport_to(player, ctx.driver._lookup_location(ctx.config.startlocation_wizard))
        else:
            target = ctx.driver.search_player(args[0])
            if not target:
                raise ActionRefused("%s isn't here." % args[0])
            if teleport_self:
                teleport_to(player, target.location)
            else:
                teleport_someone_to_player(target, player)


def teleport_to(player: Player, location: base.Location) -> None:
    """helper function for teleport command, to teleport the player somewhere"""
    player.tell_others("{Title} makes some gestures and a portal suddenly opens.")
    player.tell_others("%s jumps into the portal, which quickly closes behind %s." % (lang.capital(player.subjective), player.objective))
    player.teleported_from = player.location  # used for the 'return' command
    player.move(location, silent=True)
    player.tell("You've been teleported.", end=True)
    player.look()
    location.tell("Suddenly, a shimmering portal opens!", exclude_living=player)
    location.tell("%s jumps out, and the portal quickly closes behind %s." %
                  (lang.capital(player.title), player.objective), exclude_living=player)


def teleport_someone_to_player(who: base.Living, player: Player) -> None:
    """helper function for teleport command, to teleport someone to the player"""
    who.location.tell("Suddenly, a shimmering portal opens!")
    room_msg = "%s is sucked into it, and the portal quickly closes behind %s." % (lang.capital(who.title), who.objective)
    player.location.tell("%s makes some gestures and a portal suddenly opens." % lang.capital(player.title), exclude_living=who)
    who.location.tell(room_msg, specific_targets={who}, specific_target_msg="You are sucked into it!")
    who.teleported_from = who.location  # used for the 'return' command
    who.move(player.location, silent=True)
    who.tell("You tumble out of the other end of the portal, and find yourself in <location>%s</>." % player.location.name)
    player.location.tell("%s tumbles out of it, and the portal quickly closes again." % lang.capital(who.title), exclude_living=who)


@wizcmd("return")
def do_return(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Return a player to the location where they were before a teleport."""
    if len(parsed.who_order) == 1:
        who = parsed.who_order[0]
    elif len(parsed.who_order) == 0:
        who = player
    else:
        raise ActionRefused("You can only return one person at a time.")
    previous_location = who.teleported_from
    if previous_location:
        player.tell("Returning <player>%s</> to <location>%s</>" % (who.name, previous_location.name))
        who.location.tell("Suddenly, a shimmering portal opens!")
        room_msg = "%s is sucked into it, and the portal quickly closes behind %s." % (lang.capital(who.title), who.objective)
        who.location.tell(room_msg, specific_targets={who}, specific_target_msg="You are sucked into it!")
        who.teleported_from = None
        who.move(previous_location, silent=True)
        who.tell_others("Suddenly, a shimmering portal opens!")
        who.tell_others("{Title} tumbles out of it, and the portal quickly closes again.")
    else:
        player.tell("Can't determine <player>%s</>'s previous location." % who.name)


@wizcmd("reload")
def do_reload(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Reload the given python module under the library tree (try !reload .items.basic)
or one of the story's zone module (try !reload zones.town). This is not always reliable
and may produce weird results just like when reloading modules that are still used in python!"""
    if not parsed.args:
        raise ActionRefused("Reload what?")
    path = parsed.args[0]
    if path == "zones" or path.startswith("zones."):  # XXX don't copy this from ls command
        module_name = path
    elif path.startswith("."):
        module_name = LIBRARY_MODULE_NAME
        if len(path) > 1:
            module_name += path
    else:
        raise ActionRefused("Path must start with '.' or 'zones'")
    try:
        module = importlib.import_module(module_name)
    except (ImportError, ValueError):
        raise ActionRefused("There's no module named " + path)
    importlib.reload(module)
    player.tell("Module has been reloaded: " + module.__name__)


@wizcmd("move")
def do_move(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Move something or someone to another location (.), item or creature.
This may work around possible restrictions that could prevent stuff
to be moved around normally. For instance you could use it to pick up
items that are normally fixed in place (move item to playername)."""
    if len(parsed.args) != 2 or len(parsed.who_order) < 1:
        raise ActionRefused("Move what where?")
    thing = parsed.who_order[0]
    if isinstance(thing, base.Living):
        raise ActionRefused("* use 'teleport' instead to move livings around.")
    if parsed.args[1] == "." and len(parsed.who_order) == 1:
        # current room is the target
        target = player.location
    elif len(parsed.who_order) == 2:
        target = parsed.who_order[1]
    else:
        raise ParseError("It's not clear what you want to move where.")
    if thing is target:
        raise ActionRefused("You can't move things inside themselves.")
    # determine the current container of the object that is being moved
    if thing in player:
        thing_container = player
    elif thing in player.location:
        thing_container = player.location       # type: ignore
    else:
        raise ParseError("There seems to be no <item>%s</> here." % thing.name)
    thing.move(target, player)
    player.tell("Moved <item>%s</> from %s to %s." % (thing.name, thing_container.name, target.name))
    player.tell_others("{Title} moved %s into %s." % (thing.title, target.title))


@wizcmd("debug")
def do_debug(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Dumps the internal attribute values of a location (.), item or creature."""
    if not parsed.args:
        raise ParseError("Debug what?")
    name = parsed.args[0]
    if name == ".":
        obj = player.location
    elif parsed.who_order:
        obj = parsed.who_order[0]
    else:
        raise ActionRefused("Can't find %s." % name)
    txt = ["<bright>%r</>" % obj, "Class defined in: " + inspect.getfile(obj.__class__)]
    for varname, value in sorted(vars(obj).items()):
        txt.append("<dim>.</>%s<dim>:</> %r" % (varname, value))
    if obj in ctx.driver.heartbeat_objects:
        txt.append("%s receives heartbeats." % obj.name)
    player.tell("\n".join(txt), format=False)


@wizcmd("set")
def do_set(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Set an internal attribute of a location (.), object or creature to a new value.
Usage is: set xxx.fieldname=value (you can use Python literals only)"""
    if not parsed.args:
        raise ParseError("Set what? (usage: set xxx.fieldname=value)")
    args = parsed.args[0].split("=")
    if len(args) != 2:
        raise ParseError("Set what? (usage: set xxx.fieldname=value)")
    name, field = args[0].split(".")
    if name == "":
        obj = player.location
    else:
        obj = player.search_item(name, include_inventory=True, include_location=True)   # type: ignore
    if not obj:
        obj = player.location.search_living(name)    # type: ignore
    if not obj:
        raise ActionRefused("Can't find %s." % name)
    player.tell(repr(obj), end=True)
    import ast
    value = ast.literal_eval(args[1])
    expected_type = type(getattr(obj, field))
    if expected_type is type(value):
        setattr(obj, field, value)
        player.tell("Field set: %s.%s = %r" % (name, field, value))
    else:
        raise ActionRefused("Data type mismatch, expected %s." % expected_type)


@wizcmd("server")
def do_server(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Dump some server information."""
    driver = ctx.driver
    config = ctx.config
    player.tell("<bright>Server information:</>", end=True)
    txt = []
    up_hours, up_minutes, up_seconds = driver.uptime
    realtime = datetime.datetime.now()
    realtime = realtime.replace(microsecond=0)
    pyversion = "{0.major}.{0.minor}.{0.micro}".format(sys.version_info)
    sixtyfour = "(%d bits)" % (sys.maxsize.bit_length() + 1)
    implementation = platform.python_implementation()
    txt.append("Python version: %s %s %s on %s" % (implementation, pyversion, sixtyfour, sys.platform))
    txt.append("Tale library:   %s" % __version__)
    txt.append("Game version:   %s %s" % (config.name, config.version))
    txt.append("Uptime:         %d:%02d:%02d  (since %s)" % (up_hours, up_minutes, up_seconds, driver.server_started))
    txt.append("Server mode:    %s" % config.server_mode)
    txt.append("Real time:      %s" % realtime)
    if config.server_tick_method == TickMethod.TIMER:
        txt.append("Game time:      %s  (%dx real time)" % (ctx.clock, ctx.clock.times_realtime))
    else:
        txt.append("Game time:      %s" % ctx.clock)
    txt.append("Python objects: %s" % len(gc.get_objects()))
    txt.append("Players:        %d" % len(ctx.driver.all_players))
    txt.append("Heartbeats:     %d" % len(driver.heartbeat_objects))
    txt.append("Deferreds:      %d" % len(driver.deferreds))
    txt.append("Loop tick:      %.1f sec" % config.server_tick_time)
    if config.server_tick_method == TickMethod.TIMER:
        avg_loop_duration = sum(driver.server_loop_durations) / len(driver.server_loop_durations)
        txt.append("Loop duration:  %.2f sec. (avg)" % avg_loop_duration)
    elif config.server_tick_method == TickMethod.COMMAND:
        txt.append("Loop duration:  n/a (command driven)")
    player.tell("\n".join(txt), format=False)


@wizcmd("events")
def do_events(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Dump pending actions."""
    driver = ctx.driver
    config = ctx.config
    player.tell("<bright>Pending actions overview.</>", end=True)
    player.tell("Heartbeat objects (%d):" % len(driver.heartbeat_objects))
    txt = []
    for hb in driver.heartbeat_objects:
        txt.append("  " + str(hb))
    player.tell("\n".join(txt), format=False)
    num_shown = min(50, len(driver.deferreds))
    player.tell("Deferreds (%d, showing %d):   (server tick: %.1f sec)" %
                (len(driver.deferreds), num_shown, config.server_tick_time), end=True)
    txt = ["<ul>  due   <dim>|</><ul> function            <dim>|</><ul> owner                       </>"]
    for d in sorted(driver.deferreds)[:50]:
        txt.append("%-7s <dim>|</> %-20s<dim>|</> %s" % (d.when_due(ctx.clock, realtime=True), d.action, d.owner))
    txt.append("")
    player.tell("\n".join(txt), format=False)


@wizcmd("pubsub")
def do_pubsub(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Give an overview of the pubsub topics."""
    pending = pubsub.pending()
    player.tell("<bright>Pending pubsub messages overview.</> Active topics (from %d total):" % len(pending))
    total_pending = 0
    txt = ["<ul>  topic                                            <dim>|</><ul>#pending<dim>|</><ul>idle sec.<dim>|</><ul>subs</>"]
    for topic in sorted(pending, key=lambda t: str(t)):
        num_pending, idle_time, subbers = pending[topic]
        total_pending += num_pending
        if num_pending or subbers or idle_time < 10:
            txt.append("%-50.50s <dim>|</>  %3d   <dim>|</>  %4d   <dim>|</> %d" % (topic, num_pending, int(idle_time), subbers))
    txt.append(("total pending:  " + str(total_pending)).rjust(56))
    txt.append("")
    player.tell("\n".join(txt), format=False)


@wizcmd("force")
def do_force(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Force another living being into performing a given command."""
    if len(parsed.args) < 2 or not parsed.who_order:
        raise ParseError("Force whom to do what?")
    target = parsed.who_order[0]
    if not isinstance(target, base.Living):
        raise ActionRefused("You cannot force <item>%s</> to do anything." % target.title)
    verb = parsed.args[1]
    # simple check for verb validness
    if verb not in ctx.driver.current_verbs(target) and not player.soul.is_verb(verb) and verb not in target.location.exits:
        raise ParseError("You cannot let them do '%s'; I don't know that verb." % verb)
    cmd_parts = parsed.unparsed.partition(verb)
    cmd = cmd_parts[1] + cmd_parts[2]
    room_msg = "<player>%s</> coerces <player>%s</> into doing something." % (lang.capital(player.title), target.title)
    target_msg = "<player>%s</> coerces you into doing something!" % lang.capital(player.title)
    player.tell("You coerce <player>%s</> into following your orders." % target.title)
    player.location.tell(room_msg, exclude_living=player, specific_targets={target}, specific_target_msg=target_msg)
    if isinstance(target, Player):
        target.store_input_line(cmd)   # insert the command into the target player's input buffer
        return
    # re-parse and execute the actual command for the target, from the viewpoint of the current player!
    # This duplicates some code from the driver (which executes it on the player's behalf)
    # but here we execute it on the target's behalf (and not support all possibilities)
    custom_verbs = set(ctx.driver.current_custom_verbs(target))
    command_verbs = set(ctx.driver.current_verbs(target))
    all_verbs = custom_verbs | command_verbs
    try:
        target_parsed = target.parse(cmd, all_verbs)
        # simple soul emote, deal with it by socializing
        # async: topic_pending_actions.send(lambda: target.do_socialize_cmd(target_parsed))
        target.do_socialize_cmd(target_parsed)
    except NonSoulVerb as x:
        # not a soul emote, find the appropriate command to run.
        # async: topic_pending_actions.send(lambda actor=player, parsed=x.parsed, ctx=ctx: target.do_forced_cmd(actor, parsed, ctx))
        target.do_forced_cmd(player, x.parsed, ctx)


@wizcmd("accounts")
@disabled_in_gamemode(GameMode.IF)
def do_accounts(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """Show all registered player accounts"""
    accounts = ctx.driver.mud_accounts.all_accounts()
    wizards = set()
    txt = ["<ul> account      <dim>|</><ul> logged in           <dim>|</><ul> email                <dim>|</><ul> privileges </>"]
    for account in accounts:
        if "wizard" in account.privileges:
            wizards.add(account.name)
        txt.append(" %-12s <dim>|</> %19s <dim>|</> %-20s <dim>|</> %s" %
                   (account.name, account.logged_in, account.email, lang.join(account.privileges, None)))
    txt.append("\nWizards: " + lang.join(wizards))
    player.tell("\n".join(txt), format=False)


@wizcmd("add_priv")
@disabled_in_gamemode(GameMode.IF)
def do_add_priv(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """
    Usage: add_priv <account> <privilege>. Adds a privilege to a user account. It will become active on next login.
    """
    if len(parsed.args) != 2:
        raise ParseError("For what account add what privilege?")
    name, priv = parsed.args
    try:
        account = ctx.driver.mud_accounts.get(name)
    except KeyError:
        raise ActionRefused("No such account.")
    account.privileges.add(priv)
    new_privs = ctx.driver.mud_accounts.update_privileges(name, account.privileges, player)
    player.tell("Privileges of account <player>%s</> updated to: %s." % (name, new_privs))
    player.tell("It will become active on their next login.")


@wizcmd("remove_priv")
@disabled_in_gamemode(GameMode.IF)
def do_remove_priv(player: Player, parsed: ParseResult, ctx: util.Context) -> None:
    """
    Usage: remove_priv <account> <privilege>.
    Remove a privilege from a user account.
    If the account is currently logged in, it will be forced to log off.
    """
    if len(parsed.args) != 2:
        raise ParseError("For what account remove what privilege?")
    name, priv = parsed.args
    try:
        account = ctx.driver.mud_accounts.get(name)
    except KeyError:
        raise ActionRefused("No such account.")
    if priv in account.privileges:
        account.privileges.remove(priv)
        new_privs = ctx.driver.mud_accounts.update_privileges(name, account.privileges, player)
        player.tell("Privileges of account <player>%s</> updated to: %s." % (name, new_privs))
        other = ctx.driver.search_player(name)
        if other:
            other.tell("%s has revoked a certain privilege from you. You are forced to log out and have to log in again. "
                       "Sorry for the inconvenience." % lang.capital(player.title))
            ctx.driver.defer(1, ctx.driver._disconnect_mud_player, other)
            player.tell("Player has been notified and forced to log off.")
    else:
        player.tell("No changes.")
