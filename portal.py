import copy
import igraph

class Portal:
    # Portals would be called 'exits' if that didn't make it
    # perilously easy to exit the program by mistake. They link
    # one place to another. They are one-way; if you want two-way
    # travel, make another one in the other direction. Each portal
    # has a 'weight' that probably represents how far you have to
    # go to get to the other side; this can be zero. Portals are
    # likely to impose restrictions on what can go through them
    # and when. They might require some ritual to be performed
    # prior to becoming passable, e.g. opening a door before
    # walking through it. They might be diegetic, in which case
    # they point to a Thing that the player can interact with, but
    # the portal itself is not a Thing and does not require one.
    # 
    # These are implemented as methods, although they
    # will quite often be constant values, because it's not much
    # more work and I expect that it'd cause headaches to be
    # unable to tell whether I'm dealing with a number or not.
    def __init__(self, name, origin, destination, attributes={}, avatar=None, weight=0):
        self.name = name
        self.weight = weight
        self.avatar = avatar
        self.dest = destination
        self.orig = origin
        self.att = attributes
    def __repr__(self):
        return "(" + str(self.orig) + "->" + str(self.dest) + ")"
    def __eq__(self, other):
        return self.name == other.name
    def get_weight(self):
        return weight
    def get_avatar(self):
        return avatar
    def is_passable_now(self):
        return True
    def admits(self, traveler):
        return True
    def is_passable_by(self, traveler):
        return self.isPassableNow() and self.admits(traveler)
    def get_dest(self):
        return self.dest
    def get_orig(self):
        return self.orig
    def get_ends(self):
        return [self.orig, self.dest]
    def touches(self, place):
        return self.orig is place or self.dest is place
    def find_neighboring_portals(self):
        return self.orig.portals + self.dest.portals