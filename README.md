<!-- [![saythanks](https://img.shields.io/badge/say-thanks-ff69b4.svg)](https://saythanks.io/to/irmen)
[![Build Status](https://travis-ci.org/irmen/Tale.svg?branch=master)](https://travis-ci.org/irmen/Tale)
[![Latest Version](https://img.shields.io/pypi/v/tale.svg)](https://pypi.python.org/pypi/tale/)

![Tale logo](docs/source/_static/tale-large.png)

'Tale' - mud, mudlib & interactive fiction framework
====================================================

This software is copyright (c) by Irmen de Jong (irmen@razorvine.net).

This software is released under the GNU LGPL v3 software license.
This license, including disclaimer, is available in the 'LICENSE.txt' file.



Tale requires Python 3.5 or newer.
(If you have an older version of Python, stick to Tale 2.8 or older, which still supports Python 2.7 as well)

Required third party libraries:
- ``appdirs`` (to load and save games and config data in the correct folder).
- ``colorama`` (for stylized console output)
- ``serpent`` (to be able to create save game data from the game world)
- ``smartypants`` (for nicely quoted string output)

Optional third party library:
- ``prompt_toolkit``  (provides a nicer console text interface experience)

Read the documentation for more details on how to get started, see http://tale.readthedocs.io/

EXAMPLE STORIES
---------------

There is a trivial example built into tale, you can start it when you have the library installed
by simply typing:  ``python -m tale.demo.story``

On github and in the source distribution there are several much larger [example stories](stories/) and MUD examples.
* 'circle' - MUD that interprets CircleMud's data files and builds the world from those
* 'demo' - a random collection of stuff including a shop with some people
* 'zed_is_me' - a small single player (interactive fiction) survival adventure

If my server is up, you can find the first two running online, see http://www.razorvine.net/ -->

Zomb1e Survival

Text adventure Mud built with 'Tale' - mud, mudlib & interactive fiction framework

To start server and get gui for Mud run

python -m tale.main --game ./stories/zomb1e_survival --mode mud
