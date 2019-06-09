
import random
from tale.base import Location, Exit, Door, Item, Living
from tale.util import call_periodically, Context
from zones.npcs import Zombie, Trader
from zones import house

street1 = Location("Lake Drive", "Your house is on Lake Drive, it overlooks the lake. "
                                      "The rest of the town lies eastwards.")
lot = Location("Parking Lot", "A small parking lot with a few cars parked in it.")

Door.connect(house.livingroom,
             ["door", "outside", "street"], "Your front door leads outside, to the street.\n",
             "There's a heavy front door here that leads to the streets outside.",
             street1,
             ["house", "door", "inside"], "You can go back inside your house.",
             "It's your house, on the north side of the street.")

deli = Location("Deli", "A deli. It is completely empty, all the food and items seem to be gone.")

Exit.connect(deli, ["lake drive", "outside", "street", "back"], "Lake drive is the street you came from.", None,
             street1, ["deli", "east"], "The east end of the street leads to a deli.", None)
Exit.connect(lot, ["back"], "Go back home.", None,
             street1, ["lot", "parking"], "There is a parking lot next to the deli.", None)

zombie =  w = Zombie("zombie", random.choice("mf"), descr="A bloody zombie lingering around.")
street1.insert(zombie, None)


trader = Trader("Creepy Trader", "m", title="Creepy Trader")
trader.extra_desc["bullets"] = "It is a a box of rounds with 5 bullets in it for your gun."
trader.extra_desc["ammo"] = trader.extra_desc["bullets"]
trader.aliases.add("trader")

# ammo
ammo = Item("ammo", "5 pistol bullets", descr="It looks like the ammo for your gun.")
ammo.value = Trader.ammo_price
ammo.aliases = {"bullets", "ammo"}
trader.init_inventory([ammo])
deli.insert(trader, None)
