import sys, os
sys.path.append(os.curdir)

import sqlite3
from place import Place
from portal import Portal
from widgets import *
from thing import Thing
from attrcheck import *

defaultCommit=True
testDB=False

def untuple(tuplist):
    r = []
    for tup in tuplist:
        r += list(tup)
    return r

def valuesrow(n):
    if n < 1:
        return
    elif n == 1:
        return '(?)'
    else:
        left = '('
        mid = '?, ' * (n - 1)
        right = '?)'
        return left+mid+right

def valuesrows(x, y):
    return ', '.join([ valuesrow(x) for i in xrange(0,y) ])

def valuesins(tab, x, y):
    return "insert into " + tab + " values " + valuesrows(x, y) + ";"

def valuesknow(tab, keyexp, x, y):
    return "select count(*) from " + tab + " where " + keyexp + " in (" + valuesrows(x, y) + ");"

class Database:
    """
    Method naming conventions:

    mksomething(...) means write a record for a new entity

    updsomething(...) means update the record for an entity--blithely
    assuming it exists

    writesomething(...) calls mksomething or updsomething depending on
    whether or not an entity already exists in the database. As
    arguments it takes the same things that mksomething does.

    savesomething(...) takes a Python object of one of the game's
    classes as its first argument, and calls writesomething with
    arguments taken from the appropriate attributes of the Python
    object.

    loadsomething(...) fetches data from the database, constructs an
    appropriate Python object out of it, puts the object in
    somethingmap, and returns the object.

    getsomething(...) fetches and returns an object from somethingmap
    if possible. But if somethingmap doesn't have it, get it from
    loadsomething instead.

    knowsomething(...) checks to see if the database has a record with
    the given information

    havesomething(...) takes a Python object and calls knowsomething
    with the appropriate attributes. It only exists if the table
    called something stores data for Python objects.

    delsomething(...) takes only what's necessary to identify
    something, and deletes the thing from the database and from the
    dictionaries.

    cullsomething(...) takes a partial key and a list of somethings,
    and deletes those somethings that match the partial key but aren't
    in the list.

    """

    def __init__(self, dbfile, xfuncs = {}, defaultCommit=True):
        self.conn = sqlite3.connect(dbfile)
        self.readcursor = self.conn.cursor()
        self.writecursor = self.conn.cursor()
        self.placemap = {}
        self.portalmap = {}
        self.portalorigdestmap = {}
        self.thingmap = {}
        self.spotmap = {}
        self.imgmap = {}
        self.spotgraphmap = {}
        self.canvasmap = {}
        self.menumap = {}
        self.menuitemmap = {}
        self.attrvalmap = {}
        self.attrcheckmap = {}
        self.pawnmap = {}
        self.stylemap = {}
        self.colormap = {}

        self.contained_in = {} # This maps strings to other strings, not to Python objects.
        self.func = { 'saveplace' : self.saveplace,
                      'getplace' : self.getplace,
                      'delplace' : self.delplace,
                      'savething' : self.savething,
                      'getthing' : self.getthing,
                      'delthing' : self.delthing,
                      'getitem' : self.getitem,
                      'getattribute' : self.getattribute,
                      'saveattribute' : self.saveattribute,
                      'writeattribute' : self.writeattribute,
                      'delattribute' : self.delattribute }
        self.typ = { 'str' : str,
                     'int' : int,
                     'float' : float,
                     'bool' : bool }
        self.func.update(xfuncs)
    def __del__(self):
        self.readcursor.close()
        self.writecursor.close()
        self.conn.commit()
        self.conn.close()
    def mkschema(self):
        # items shall cover everything that has attributes.
        # items may or may not correspond to anything in the gameworld.
        # they may be places. they may be things. they may be people.
        self.writecursor.execute("create table item (name text primary key);")
        self.writecursor.execute("create table place (name text primary key, foreign key(name) references item(name));")
        self.writecursor.execute("create table thing (name text primary key, foreign key(name) references item(name));")
        self.writecursor.execute("create table portal (name text primary key, from_place, to_place, foreign key(name) references item(name), foreign key(from_place) references place(name), foreign key(to_place) references place(name), check(from_place<>to_place));")
        self.writecursor.execute("create table containment (contained, container, foreign key(contained) references item(name), foreign key(container) references item(name), check(contained<>container), primary key(contained));")
        self.writecursor.execute("create table spot (place primary key, x, y, r, spotgraph, foreign key(place) references place(name));")
        self.writecursor.execute("create table attrtype (name text primary key);")
        self.writecursor.execute("create table attribute (name text primary key, type, lower, upper, foreign key(type) references attrtype(name));")
        self.writecursor.execute("create table attribution (attribute, attributed_to, value, foreign key(attribute) references permitted_values(attribute), foreign key(attributed_to) references item(name), foreign key(value) references permitted_values(value), primary key(attribute, attributed_to));")
        self.writecursor.execute("create table permitted (attribute, value, foreign key(attribute) references attribute(name), primary key(attribute, value));")
        self.writecursor.execute("create table img (name text primary key, path, rltile);")
        self.writecursor.execute("create table canvas (name text primary key, width integer, height integer, wallpaper, foreign key(wallpaper) references image(name));")
        self.writecursor.execute("create table pawn (name text primary key, img, item, x integer, y integer, spot text, foreign key(img) references img(name), foreign key(item) references item(name), foreign key(spot) references place(name));")
        self.writecursor.execute("create table color (name text primary key, red integer not null check(red between 0 and 255), green integer not null check(green between 0 and 255), blue integer not null check(blue between 0 and 255));")
        self.writecursor.execute("create table style (name text primary key, fontface text not null, fontsize integer not null, spacing integer, bg_inactive, bg_active, fg_inactive, fg_active, foreign key(bg_inactive) references color(name), foreign key(bg_active) references color(name), foreign key(fg_inactive) references color(name), foreign key(fg_active) references color(name));")
        self.writecursor.execute("create table menu (name text primary key, x integer not null, y integer not null, width integer not null, height integer not null, style text default 'Default', foreign key(style) references style(name));")
        self.writecursor.execute("create table menuitem (menu text, idx integer, text text, onclick text, closer boolean, foreign key(menu) references menu(name), primary key(menu, idx));")

        # I think maybe I will want to actually store pawns in the database eventually.
        # Later...
        self.conn.commit()

    def initialized(self):
        try:
            for tab in ["thing", "place", "attribute", "img"]:
                self.readcursor.execute("select * from ? limit 1;", (tab,))
        except:
            return False
        return True

    def insert_defaults(self, d, commit=defaultCommit):
        self.mkcolors(default.colors, commit=False)
        self.mkstyles(default.styles, commit=False)
        self.mkmenus(default.menus, commit=False)
        self.mkmenuitems(default.menuitems, commit=False)
        self.mkplaces(default.places, commit=False)
        self.mkportals(default.portals, commit=False)
        self.mkthings(default.things, commit=False)
        self.mkattributes(default.attributes, commit=False)
        self.mkattributions(default.attributions, commit=False)
        if commit:
            self.conn.commit()

    def mkmany(self, tname, valtups, commit=defaultCommit):
        querystr = valsins(tname, len(valtups[0]), len(valtups))
        vals = untuple(valtups)
        self.writecursor.execute(querystr, vals)
        if commit:
            self.conn.commit()

    def knowany(self, tname, keyexp, keytups):
        querystr = valsknow(tname, keyexp, len(keytups[0]), len(keytups))
        keys = untuple(keytups)
        self.readcursor.execute(querystr, keys)
        r = self.readcursor.fetchone()
        if r in [None, []]:
            return False
        elif r[0] == 0:
            return False
        else:
            return True

    def knowall(self, tname, keyexp, keytups):
        numkeys = len(keytups)
        keylen = len(keytups[0])
        querystr = valsknow(tname, keyexp, keylen, numkeys)
        keys = untuple(keytups)
        self.readcursor.execute(querystr, keys)
        r = self.readcursor.fetchone()
        if r in [None, []]:
            return False
        elif r[0] == numkeys:
            return True
        else:
            return False

    def knowplace(self, name):
        self.readcursor.execute("select count(*) from place where name=?;",
                                (name,))
        return self.readcursor.fetchone()[0] == 1

    def knowsomeplace(self, keytups):
        return self.knowany("place", "(name)", keytups)

    def knowsomeplaces(self, keytups):
        return self.knowsomeplace(keytups)

    def knowallplace(self, keytups):
        return self.knowall("place", "(name)", keytups)

    def knowallplaces(self, keytups):
        return self.knowallplace(keytups)

    def haveplace(self, place):
        return self.knowplace(place.name)

    def mkplace(self, name, commit=defaultCommit):
        # Places should always exist in the database before they are Python objects.
        self.writecursor.execute("insert into item values (?);", (name,))
        self.writecursor.execute("insert into place values (?);", (name,))
        if commit:
            self.conn.commit()

    def mkplaces(self, placetups, commit=defaultCommit):
        self.mkmany("thing", placetups, commit=False)
        self.mkmany("place", placetups, commit=False)
        if commit:
            self.conn.commit()

    def writeplace(self, name, contents=[], atts=[], commit=defaultCommit):
        if not self.knowplace(name):
            self.mkplace(name, commit=False)
        self.writecontainments(contents, commit=False)
        self.writeattributions(atts, commit=False)
        if commit:
            self.conn.commit()

    def saveplace(self, place, commit=defaultCommit):
        self.writeplace(place.name, place.contents, list(place.att.iteritems()), commit)

    def loadplace(self, name):
        if not self.knowplace(name):
            return None
        self.readcursor.execute("select name from portal where from_place=?;", (name,))
        portals = self.readcursor.fetchall()
        self.readcursor.execute("select contained from containment where container=?;", (name,))
        contents = self.readcursor.fetchall()
        p = Place(name) # I think I might have to handle nulls special
        self.placemap[name] = p
        for port in portals:
            p.portals.append(self.getportal(port[0]))
        for item in contents:
            th = self.getthing(item[0])
            p.addthing(th)
        return p

    def getplace(self, name):
        # Remember that this returns the *loaded* version, if there is one.
        if self.placemap.has_key(name):
            return self.placemap[name]
        else:
            return self.loadplace(name)

    def delplace(self, name):
        if self.placemap.has_key(name):
            del self.placemap[name]
        self.writecursor.execute("delete from place where name=?;", (name,))
        self.writecursor.execute("delete from item where name=?;", (name,))

    def knowthing(self, name):
        self.readcursor.execute("select count(*) from thing where name=?;",
                                (name,))
        return self.readcursor.fetchone()[0] == 1
        
    def knowsomething(self, namesingletons):
        return self.knowany("thing", "(name)", namesingletons)

    def knowsomethings(self, namesingletons):
        return self.knowsomething(namesingletons)

    def knowallthing(self, namesingletons):
        return self.knowall("thing", "(name)", namesingletons)

    def knowallthings(self, namesingletons):
        return self.knowallthing(namesingletons)

    def havething(self, thing):
        return self.knowthing(thing.name)

    def mkthing(self, name, loc=None, commit=defaultCommit):
        self.writecursor.execute("insert into item values (?);", (name,))
        self.writecursor.execute("insert into thing values (?);", (name,))
        if loc is not None:
            self.writecontainment(name, loc, commit=False)
        if commit:
            self.conn.commit()

    def mkthings(self, thingtups, commit=defaultCommit):
        self.mkmany("item", thingtups, commit=False)
        self.mkmany("thing", thingtups commit=False)
        if commit:
            self.conn.commit()

    def updthing(self, name, loc=None, atts=[], commit=defaultCommit):
        for att in atts:
            self.writeattribution(att[0], name, att[1])
        if loc is not None:
            self.writecontainment(name, loc)
        self.cullattribution(name, atts)
        self.cullcontainment(name)

    def writething(self, name, loc="", atts=[], commit=defaultCommit):
        if self.knowthing(name):
            self.updthing(name, loc, atts, commit)
        else:
            self.mkthing(name, loc, atts, commit)

    def savething(self, thing, commit=defaultCommit):
        if thing.loc is None:
            loc = ''
        else:
            loc = thing.loc.name
        self.writething(thing.name, loc, thing.att.iteritems(), commit)

    def loadthing(self, name):
        self.readcursor.execute("select container from containment where contained=?;", (name,))
        loc_s = self.readcursor.fetchone()[0]
        loc = self.getplace(loc_s)
        self.readcursor.execute("select attribute, value from attribution where attributed_to=?;", (name,))
        atts_s_l = self.readcursor.fetchall()
        atts_l = [att for att in atts_s_l]
        th = Thing(name, loc, dict(atts_l))
        self.thingmap[name] = th
        return th

    def getthing(self, name):
        if self.thingmap.has_key(name):
            return self.thingmap[name]
        else:
            return self.loadthing(name)

    def delthing(self, thing, commit=defaultCommit):
        if self.thingmap.has_key(thing):
            del self.thingmap[thing]
        self.writecursor.execute("delete from containment where contained=? or container=?;", (thing, thing))
        self.writecursor.execute("delete from thing where name=?;", (thing,))
        self.writecursor.execute("delete from item where name=?;", (thing,))
        if commit:
            self.conn.commit()

    def loaditem(self, name):
        if self.knowthing(name):
            return self.loadthing(name)
        elif self.knowplace(name):
            return self.loadplace(name)
        elif self.knowportal(name):
            return self.loadportal(name)
        else:
            return None

    def getitem(self, name):
        if self.thingmap.has_key(name):
            return self.thingmap[name]
        elif self.placemap.has_key(name):
            return self.placemap[name]
        elif self.portalmap.has_key(name):
            return self.portalmap[name]
        else:
            return self.loaditem(name)
            
    def knowcontainment(self, contained):
        self.readcursor.execute("select count(*) from containment where contained=?;",
                       (contained,))
        return self.readcursor.fetchone()[0] == 1

    def knowsomecontainment(self, singletons):
        return self.knowany("containment", "(contained)", singletons)

    def knowallcontainment(self, singletons):
        return self.knowall("containment", "(contained)", singletons)

    def havecontainment(self, item):
        contained = item.loc
        return self.knowcontainment(item)

    def mkcontainment(self, contained, container, commit=defaultCommit):
        self.writecursor.execute("insert into containment values (?, ?);",
                  (contained, container))
        if commit:
            self.conn.commit()

    def mkcontainments(self, conttups, commit=defaultCommit):
        querystr = valuesins("containment", 2, len(conttups))
        flattups = []
        for tup in conttups:
            if type(tup) is tuple:
                flattups.append(tup[0])
                flattups.append(tup[1])
            else:
                flattups.append(tup)
        self.writecursor.execute(querystr, flattups)
        if commit:
            self.conn.commit()

    def updcontainment(self, contained, container, commit=defaultCommit):
        self.writecursor.execute("update containment set container=? where contained=?;",
                  (container, contained))
        if commit:
            self.conn.commit()

    def writecontainment(self, contained, container, commit=defaultCommit):
        if self.knowcontainment(contained):
            self.updcontainment(contained, container, commit)
        else:
            self.mkcontainment(contained, container, commit)

    def savecontainment(self, contained, commit=defaultCommit):
        self.writecontainment(contained, contained.loc)

    def loadcontainment(self, contained):
        self.readcursor.execute("select container from containment where contained=?;", (contained,))
        try:
            item = self.readcursor.fetchone()[0]
        except IndexError:
            return None
        self.contained_in[contained] = item
        return item

    def getcontainment(self, contained):
        if self.contained_in.has_key(contained):
            return self.contained_in[contained]
        else:
            return self.loadcontainment(contained)

    def getcontainer(self, contained):
        contained_name = self.getcontainment(contained)
        container_name = self.contained_in[contained_name]
        return self.getitem(container_name)
        
    def delcontainment(self, contained, container, commit=defaultCommit):
        self.writecursor.execute("delete from containment where contained=? and container=?;",
                       (contained, container))
        if commit:
            self.conn.commit()

    def cullcontainment(self, container, keeps=[], commit=defaultCommit):
        if len(keeps) == 0:
            self.writecursor.execute("delete from containment where container=?;", (container,))
        else:
            inner = "?, " * (len(keeps) - 1)
            left = "delete from containment where container=? and contained not in ("
            right = "?);"
            sqlitefmtstr = left + inner + right
            self.writecursor.execute(sqlitefmtstr, [container] + keeps)
        if commit:
            self.conn.commit()

    def knowattribute(self, name):
        self.readcursor.execute("select count(*) from attribute where name=?;", (name,))
        return self.readcursor.fetchone()[0] == 1

    def knowanyattribute(self, singletons):
        return self.knowany("attribute", "(name)", singletons)

    def knowallattribute(self, singletons):
        return self.knowall("attribute", "(name)", singletons)

    def mkattribute(self, name, typ=None, permitted=[], lower=None, upper=None, commit=defaultCommit):
        """Define an attribute type for LiSE items to have.

        Call this method to define an attribute that an item in the
        game can have. These attributes are not the same as the ones
        that every Python object has, although they behave similarly.

        You can define an attribute with just a name, but you might
        want to limit what values are acceptable for it. To do this,
        you may supply any of the other parameters:

        typ is a string. Valid types here are 'str', 'int',
        'float', and 'bool'.

        permitted is a list of values that the attribute is allowed to
        take on. Every value in this list will be permitted, even if
        it's the wrong type, or it falls out of the bounds.

        lower and upper should be numbers. Values of the attribute
        that are below lower or above upper will be rejected unless
        they're in the permitted list.

        """
        if typ=='':
            typ=None
        self.writecursor.execute("insert into attribute values (?, ?, ?, ?);", (name, typ, lower, upper))
        for perm in permitted:
            self.writecursor.execute("insert into permitted values (?, ?);", (name, perm))
        if commit:
            self.conn.commit()

    def updattribute(self, name, typ, permitted, lower, upper, commit):
        self.writecursor.execute("update attribute set type=?, lower=?, upper=? where name=?;",
                                 (typ, lower, upper))
        self.readcursor.execute("select value from permitted where attribute=?;", (name,))
        knownperms = [ row[0] for row in self.readcursor ]
        createdperms = [ perm for perm in permitted if perm not in knownperms ]
        deletedperms = [ perm for perm in knownperms if perm not in permitted ]
        for perm in createdperms:
            self.writepermitted(name, perm, commit=False)
        for perm in deletedperms:
            self.delpermitted(name, perm, commit=False)
        if commit:
            self.conn.commit()
            
    def writeattribute(self, name, typ=None, permitted=[], lower=None, upper=None, commit=defaultCommit):
        if False in [lower.hasattr(s) for s in ["__lt__", "__eq__", "__gt__"]]:
            lower=None
        if False in [upper.hasattr(s) for s in ["__lt__", "__eq__", "__gt__"]]:
            upper=None
        if typ not in self.typ.keys():
            typ=None
        if self.knowattribute(name):
            self.updattribute(name, typ, permitted, lower, upper, commit)
        else:
            self.mkattribute(name, typ, permitted, lower, upper, commit)

    def saveattribute(self, attrcheck, commit=defaultCommit):
        assert(isinstance(attrcheck, AttrCheck))
        permitted = []
        lo = None
        hi = None
        typ = None
        for check in attrcheck.checks:
            if isinstance(check, LowerBoundCheck):
                lo = check.bound
            elif isinstance(check, UpperBoundCheck):
                hi = check.bound
            elif isinstance(check, TypeCheck):
                typ = check.typ
            elif isinstance(check, ListCheck):
                permitted += check.list
        self.writeattribute(attrcheck.name, typ, permitted, lo, hi, commit)

    def loadattribute(self, name):
        self.readcursor.execute("select type, lower, upper from attribute where name=?;",
                                (name,))
        (typ, lo, hi) = self.readcursor.fetchone()
        self.readcursor.execute("select value from permitted where attribute=?;", (name,))
        perms = [ row[0] for row in self.readcursor ]
        attrcheck = AttrCheck(typ, perms, lo, hi)
        attrcheck.name = name
        self.attrcheckmap[name] = attrcheck
        return attrcheck

    def getattribute(self, name):
        if self.attrcheckmap.has_key(name):
            return self.attrcheckmap[name]
        else:
            return self.loadattribute(name)

    def delattribute(self, name, commit=defaultCommit):
        if self.attrcheckmap.has_key(name):
            del self.attrcheckmap[name]
        self.writecursor.execute("delete from attribute where name=?;", (name,))
        if commit:
            self.conn.commit()

    def knowpermitted(self, attr, val=None):
        if val is None:
            self.readcursor.execute("select count(*) from permitted where attribute=?;", (attr,))
        else:
            self.readcursor.execute("select count(*) from permitted where attribute=? and value=?;",
                                    (attr, val))
        return self.readcursor.fetchone()[0] > 0

    def knowanypermitted(self, attrval):
        if len(attrval[0]) == 1: # names only
            return self.knowany("permitted", "(attribute)", attrval)
        else:
            return self.knowany("permitted", "(attribute, value)", attrval)

    def knowallpermitted(self, attrval):
        if len(attrval[0]) == 1:
            return self.knowall("permitted", "(attribute)", attrval)
        else:
            return self.knowall("permitted", "(attribute, value)", attrval)

    def havepermitted(self, attrcheck):
        perms = [ n for n in check.lst for check in attrcheck.checks if isinstance(check, ListCheck) ]
        numperm = len(perms)
        left = "select count(*) from permitted where attribute=? and value in ("
        middle = "?, " * numperm - 1
        right = "?);"
        querystr = left + middle + right
        self.readcursor.execute(querystr, perms)
        return numperm == self.readcursor.fetchone()[0]

    def mkpermitted(self, attr, val, commit=defaultCommit):
        self.writecursor.execute("insert into permitted values (?, ?);", (attr, val))
        if commit:
            self.conn.commit()

    def writepermitted(self, attr, val, commit=defaultCommit):
        if not self.knowpermitted(attr, val):
            self.mkpermitted(attr, val, commit)

    def loadpermitted(self, attr):
        self.readcursor.execute("select val from permitted where attribute=?;", (attr,))
        perms = [ row[0] for row in self.readcursor ]
        if self.attrcheckmap.has_key(attr):
            attrcheck = self.attrcheckmap[attr]
            attrcheck.lstcheck = ListCheck(perms)
        else:
            attrcheck = AttrCheck(vals=perms)
            self.attrcheckmap[attr] = attrcheck
        return attrcheck

    def getpermitted(self, attr):
        if self.attrcheckmap.has_key(attr):
            attrcheck = self.attrcheckmap[attr]
            if isinstance(attrcheck, ListCheck):
                return attrcheck.lst
            else:
                return []
        else:
            return self.loadpermitted(attr)

    def delpermitted(self, attr, val, commit=defaultCommit):
        self.writecursor.execute("delete from permitted where attribute=? and value=?;",
                                 (attr, val))
        if commit:
            self.conn.commit()
            
    def knowattribution(self, attr, item):
        self.readcursor.execute("select count(*) from attribution where attribute=? and attributed_to=?;",
                       (attr, item))
        return self.readcursor.fetchone()[0] > 0

    def knowanyattribution(self, pairs):
        return self.knowany("attribution", "(attribute, attributed_to)",
                            pairs)

    def knowallattribution(self, pairs):
        return self.knowall("attribution", "(attribute, attributed_to)",
                            pairs)

    def mkattribution(self, attr, item, val, commit=defaultCommit):
        self.writecursor.execute("insert into attribution values (?, ?, ?);",
                                     (attr, item, val))
        if commit:
            self.conn.commit()
        
    def mkattributions(self, attups, commit=defaultCommit):
        querystr = valuesins("attribution", 3, len(attups))
        flatatts = []
        for att in attups:
            self.flatatts += list(att)
        self.writecursor.execute(querystr, flatatts)
        if commit:
            self.conn.commit()

    def updattribution(self, item, attr, val, commit=defaultCommit):
        attrcheck = self.getattribute(attr)
        if attrcheck.check(val):
            self.writecursor.execute("update attribution set value=? where attributed_to=? and attribute=?;",
                                     (val, item, attr))
        else:
            raise ValueError("%s is not a legal value for %s" % (str(val), attr))

    def writeattribution(self, attr, item, val, commit=defaultCommit):
        self.readcursor.execute("select count(*) from attribution where attribute=? and attributed_to=?;", (attr, item))
        if self.readcursor.fetchone()[0] == 1:
            self.updattribution(attr, item, val, commit)
        else:
            self.mkattribution(attr, item, val, commit)

    def writeattributionson(self, itemname, commit=defaultCommit):
        for attrval in self.attrvalmap[itemname].iteritems():
            self.writeattribution(attrval[0], itemname, attrval[1], commit)

    def saveattributionson(self, item, commit=defaultCommit):
        self.writeattributionson(item.name, commit)

    def delattribution(self, attr, item, commit=defaultCommit):
        self.writecursor.execute("delete from attribution where attribute=? and attributed_to=?;",
                                 (attr, item))
        if commit:
            self.conn.commit()

    def cullattribution(self, item, keeps=[], commit=defaultCommit):
        if len(keeps) == 0:
            self.writecursor.execute("delete from attribution where attributed_to=?;", (item,))
        else:
            inner = "?, " * (len(keeps) - 1)
            left = "delete from attribution where attributed_to=? and attribute not in ("
            right = "?);"
            sqlitefmtstr = left + inner + right
            self.writecursor.execute(sqlitefmtstr, [item] + keeps)
        if commit:
            self.conn.commit()

    def set_attr_upper_bound(self, attr, upper, commit=defaultCommit):
        self.readcursor.execute("select count(*) from attribute where name=?;", (attr,))
        if self.readcursor.fetchone()[0] == 0:
            self.writecursor.execute("insert into attribute values (?, ?, ?, ?);", (attr, None, None, upper))
        else:
            self.writecursor.execute("update attribute set upper=? where name=?;", (upper, attr))
        if commit:
            self.conn.commit()

    def set_attr_lower_bound(self, attr, lower, commit=defaultCommit):
        self.readcursor.execute("select count(*) from attribute where name=?;", (attr,))
        if self.readcursor.fetchone()[0] == 0:
            self.writecursor.execute("insert into attribute values (?, ?, ?, ?)'", (attr, None, lower, None))
        else:
            self.writecursor.execute("update attribute set lower=? where name=?;", (lower, attr))
        if commit:
            self.conn.commit()

    def set_attr_bounds(self, attr, lower, upper, commit=defaultCommit):
        self.readcursor.execute("select count(*) from attribute where name=?;", (attr,))
        if self.readcursor.fetchone()[0] == 0:
            self.writecursor.execute("insert into attribute values (?, ?, ?, ?);", (attr, None, lower, upper))
        else:
            self.writecursor.execute("update attribute set lower=?, upper=? where name=?;", (lower, upper, attr))
        if commit:
            self.conn.commit()

    def set_attr_type(self, attr, typ):
        self.readcursor.execute("select count(*) from attribute where name=?;", (attr,))
        if self.readcursor.fetchone()[0] == 0:
            self.writecursor.execute("insert into attribute values (?, ?, ?, ?);", (attr, typ, None, None))
        else:
            self.writecursor.execute("update attribute set type=? where name=?;", (typ, attr))
        if commit:
            self.conn.commit()

    def loadattribution(self, attr, item):
        self.readcursor.execute("select val from attribution where attribute=? and attributed_to=?;", (attr, item))
        v = self.readcursor.fetchone()[0]
        if self.getattribute(attr).check(v):
            self.attrvalmap[item][attr] = v
            return v
        else:
            raise ValueError("Loaded the value %s for the attribute %s, yet it isn't a legal value for that attribute. How did it get there?" % (str(v), attr))

    def loadattributionson(self, item):
        self.readcursor.execute("select attr, val from attribution where attributed_to=?;", (item,))
        for row in self.readcursor:
            if self.getattribute(row[0]).check(row[1]):
                self.attrvalmap[item][row[0]] = row[1]
            else:
                raise ValueError("Loaded the value %s for the attribute %s, yet it isn't a legal value for that attribute. How did it get there?" % (str(row[1]), row[0]))

    def getattribution(self, attr, item):
        if self.attrvalmap.has_key(item):
            if self.attrvalmap[item].has_key[attr]:
                return self.attrvalmap[item][attr]
            else:
                return self.loadattribution(attr, item)
        else:
            return self.loadattribution(attr, item)

    def getattributionson(self, item):
        # This assumes all the attribute values have been loaded already. What if they haven't?
        # The process for checking each and every one would require just as much disk access
        # as the loader, so I'd might as well alias it. Figure to leave this as is, and just
        # be mindful...
        return self.attrvalmap[item].itervalues()

    def knowportal(self, orig_or_name, dest=None):
        if dest is None:
            self.readcursor.execute("select count(*) from portal where name=?;",
                           (orig_or_name,))
        else:
            self.readcursor.execute("select count(*) from portal where from_place=? and to_place=?;",
            (orig_or_name, dest))
        return self.readcursor.fetchone()[0] == 1

    def knowanyportal(self, tups):
        if len(tups[0]) == 1:
            return self.knowany("portal", "(name)", tups)
        else:
            return self.knowany("portal", "(from_place, to_place)", tups)

    def knowallportal(self, tups):
        if len(tups[0]) == 1:
            return self.knowall("portal", "(name)", tups)
        else:
            return self.knowall("portal", "(from_place, to_place)", tups)

    def haveportal(self, portal):
        return self.knowportal(portal.name)

    def mkportal(self, name, orig, dest, reciprocal=True, commit=defaultCommit):
        self.writecursor.execute("insert into portal values (?, ?, ?);", (name, orig, dest))
        othername = 'portal[%s->%s]' % (dest, orig)
        if reciprocal and not self.knowportal(othername):
            self.writecursor.execute("insert into portal values (?, ?, ?);", (othername, dest, orig))
        if commit:
            self.conn.commit()

    def mkportals(self, porttups, commit=defaultCommit):
        pnames = [(tup[0],) for tup in porttups]
        self.mkmany("item", pnames, commit=False)
        self.mkmany("portal", porttups, commit=False)
        if commit:
            self.conn.commit()

    def updportal(self, name, orig, dest, commit=defaultCommit):
        self.writecursor.execute("update portal set from_place=?, to_place=? where name=?;", (orig, dest, name))
        if commit:
            self.conn.commit()

    def writeportal(self, name, orig, dest, commit=defaultCommit):
        if self.knowportal(name):
            self.updportal(name, orig, dest, commit)
        else:
            self.mkportal(name, orig, dest, commit)

    def saveportal(self, port, commit=defaultCommit):
        self.writeportal(port.name, port.orig, port.dest, commit)

    def loadportal(self, name):
        self.readcursor.execute("select from_place, to_place from portal where name=?", (name,))
        row = self.readcursor.fetchone()
        if row is None:
            return None
        else:
            port = Portal(name, row[0], row[1])
            self.portalmap[name] = port
            return port

    def getportal(self, orig_or_name, dest=None):
        if self.portalmap.has_key(orig_or_name):
            return self.portalmap[orig_or_name]
        elif dest is not None:
            if self.portalorigdestmap.has_key(orig_or_name):
                if self.portalorigdestmap[orig_or_name].has_key(dest):
                    return self.portalorigdestmap[orig_or_name][dest]
                else:
                    raise Exception("No portal connecting %s to %s." % (orig_or_name, dest))
            else:
                raise Exception("No portals from %s." % orig_or_name)
        else:
            return self.loadportal(orig_or_name)

    def delportal(self, orig_or_name, dest=None, commit=defaultCommit):
        if dest is None:
            self.writecursor.execute("delete from portal where name=?", (orig_or_name,))
            iname = orig_or_name
        else:
            self.writecursor.execute("delete from portal where from_place=? and to_place=?", (orig_or_name, dest))
            iname = "portal[%s->%s]" % (orig_or_name, dest)
        self.writecursor.execute("delete from item where name=?;", (iname,))
        if commit:
            self.conn.commit()

    def cullportals(self, orig, keeps, commit=defaultCommit):
        self.readcursor.execute("select name from portal where from_place=?;", (orig,))
        flatnames = [ row[0] for row in self.readcursor ]
        undesired = [ trash for trash in flatnames if trash not in keeps ]
        left = "delete from portal where name in ("
        mid = "?, " * len(undesired) - 1
        right = "?);"
        querystr = left + mid + right
        self.writecursor.execute(querystr, undesired)
        left = left.replace("portal", "item")
        querystr = left + mid + right
        self.writecursor.execute(querystr, undesired)
        if commit:
            self.conn.commit()

    def knowspot(self, place):
        self.readcursor.execute("select count(*) from spot where place=?;", (place,))
        return self.readcursor.fetchone()[0] > 0

    def knowanyspot(self, tups):
        return self.knowany("spot", "(place)", tups)

    def knowallspot(self, tups):
        return self.knowall("spot", "(place)", tups)

    def havespot(self, place):
        return self.knowspot(place.name)

    def mkspot(self, place, x, y, r, graph, commit=defaultCommit):
        self.writecursor.execute("insert into spot values (?, ?, ?, ?, ?);", (place, x, y, r, graph))
        if commit:
            self.conn.commit()

    def updspot(self, place, x, y, r, graph, commit=defaultCommit):
        self.writecursor.execute("update spot set x=?, y=?, r=?, spotgraph=? where place=?;"
                                 (x, y, r, graph, place))
        if commit:
            self.conn.commit()

    def writespot(self, place, x, y, r, graph, commit=defaultCommit):
        if self.knowspot(place):
            self.updspot(place, x, y, r, graph, commit)
        else:
            self.mkspot(place, x, y, r, graph, commit)

    def savespot(self, spot, commit=defaultCommit):
        self.writespot(spot.place.name, spot.x, spot.y, spot.r, spot.spotgraph.name, commit)

    def loadspot(self, place):
        self.readcursor.execute("select * from spot where place=?;", (place,))
        q = self.readcursor.fetchone()
        r = Spot(self.getplace(q[0]), int(q[1]), int(q[2]), int(q[3]), self.getgraph(q[4]))
        r.spotgraph.add_spot(r)
        self.spotmap[place] = r
        return r

    def getspot(self, placen):
        if self.spotmap.has_key(placen):
            return self.spotmap[placen]
        else:
            return self.loadspot(placen)

    def delspot(self, place, commit=defaultCommit):
        self.writecursor.execute("delete from spot where place=?;", (place,))
        if commit:
            self.conn.commit()

    def loadspotgraph(self, graphn):
        self.readcursor.execute("select spot from spotgraph where graph=?;", (graphn,))
        g = SpotGraph()
        for spotstring in self.readcursor:
            g.add_spot(self.getspot(spotstring))
        self.spotgraphmap[graphn] = g
        return g

    def getspotgraph(self, graphn):
        if spotgraph.has_key(graphn):
            return self.spotgraphmap[graphn]
        else:
            return self.loadgraph(graphn)

    def knowimg(self, name):
        self.readcursor.execute("select count(*) from img where name=?;", (name,))
        return self.readcursor.fetchone()[0] == 1

    def knowanyimg(self, tups):
        return self.knowany("img", "(name)", tups)

    def knowallimg(self, tups):
        return self.knowall("img", "(name)", tups)

    def haveimg(self, img):
        return self.knowimg(img.name)

    def mkimg(self, name, path, rl=False, commit=defaultCommit):
        self.writecursor.execute("insert into img values (?, ?, ?);", (name, path, rl))
        if commit:
            self.conn.commit()

    def updimg(self, name, path, rl=False, commit=defaultCommit):
        self.writecursor.execute("update img set path=?, rltile=? where name=?;", (path, rl, name))
        if commit:
            self.conn.commit()

    def writeimg(self, name, path, rl=False, commit=defaultCommit):
        if self.knowimg(name):
            self.updimg(name, path, rl, commit)
        else:
            self.mkimg(name, path, rl, commit)

    def loadrltile(self, name, path):
        badimg = pyglet.resource.image(path)
        badimgd = badimg.get_image_data()
        bad_rgba = badimgd.get_data('RGBA', badimgd.pitch)
        badimgd.set_data('RGBA', badimgd.pitch, bad_rgba.replace('\xffGll','\x00Gll').replace('\xff.', '\x00.'))
        rtex = badimgd.get_texture()
        rtex.name = name
        self.imgmap[name] = rtex
        return rtex

    def loadimgfile(self, name, path):
        tex = pyglet.resource.image(path).get_image_data().get_texture()
        tex.name = name
        self.imgmap[name] = tex
        return tex

    def loadimg(self, name):
        self.readcursor.execute("select * from imgfile where name=?", (name,))
        row = self.readcursor.fetchone()
        if row is None:
            return
        elif row[2]:
            return self.loadrltile(name, row[1])
        else:
            return self.loadimgfile(name, row[1])

    def getimg(self, name):
        if self.imgmap.has_key(name):
            return self.imgmap[name]
        else:
            return self.loadimg(name)

    def delimg(self, name, commit=defaultCommit):
        if self.imgmap.has_key(name):
            del self.imgmap[name]
        self.writecursor.execute("delete from img where name=?;", (name,))
        if commit:
            self.conn.commit()

    def cullimgs(self, commit=defaultCommit):
        keeps = self.imgmap.keys()
        left = "delete from img where name not in ("
        middle = "?, " * (len(keeps) - 1)
        right = "?);"
        querystr = left + middle + right
        self.writecursor.execute(querystr, keeps)
        if commit:
            self.conn.commit()

    def mkmenuitem(self, menuname, idx, text, onclick, closer=True, commit=defaultCommit):
        self.writecursor.execute("insert into menuitem values (?, ?, ?, ?, ?);", (menuname, idx, text, onclick, closer))
        if commit:
            self.conn.commit()

    def mkmenuitems(self, mitup, commit=defaultCommit):
        self.mkmany("menuitem", mitup, commit)

    def knowmenuitem(self, menuname, idx):
        self.readcursor.execute("select count(*) from menuitem where menu=? and idx=? limit 1;", (menuname, idx))
        return self.readcursor.fetchone()[0] == 1

    def knowanymenuitem(self, pairs):
        return self.knowany("menuitem", "(menu, idx)", pairs)

    def knowallmenuitem(self, pairs):
        return self.knowall("menuitem", "(menu, idx)", pairs)

    def havemenuitem(self, menuitem):
        return self.knowmenuitem(menuitem.menuname, menuitem.i)

    def updmenuitem(self, menuname, idx, text, onclick, closer, commit=defaultCommit):
        self.writecursor.execute("update menuitem set text=?, onclick=?, closer=? where menu=? and idx=?;", (text, onclick, closer, menuname, idx))
        if commit:
            self.conn.commit()

    def writemenuitem(self, menu, i, text, onclick, closer=True, commit=defaultCommit):
        if self.knowmenuitem(menu, i):
            self.updmenuitem(menu, i, text, onclick, closer, commit)
        else:
            self.mkmenuitem(menu, i, text, onclick, closer, commit)

    def loadmenuitem(self, menuname, idx):
        self.readcursor.execute("select text, onclick, closer from menuitem where menu=? and idx=?;", (menuname, idx))
        row = self.readcursor.fetchone()
        if len(row) != 3:
            return None
        else:
            menu = self.getmenu(menuname)
            it = menu.insert_item(idx, row[0], row[1], row[2])
            self.menuitemmap[(menuname, idx)] = it
            return it

    def getmenuitem(self, menuname, idx):
        if self.menuitemmap.has_key((menuname, idx)):
            return self.menuitemmap[(menuname, idx)]
        else:
            return self.loadmenuitem(menuname, idx)

    def delmenuitem(self, menuname, i, commit=defaultCommit):
        if self.menumap.has_key(menuname):
            self.menumap[menuname].remove_item(i)
        if self.menuitemmap.has_key(menuname):
            if self.menuitemmap[menuname].has_key(i):
                del self.menuitemmap[menuname][i]
        self.writecursor.execute("delete from menuitem where menu=? and index=?;",
                                 (menuname, i))
        if commit:
            self.conn.commit()

    def loaditemsinmenu(self, name, window=None):
        self.readcursor.execute("select i, text, onclick, closer from menuitem where menu=?;", (name,))
        menu = self.getmenu(name, window)
        i = 0
        for row in self.readcursor:
            menuitem = menu.insert_item(*row)
            self.menuitemmap[name][i] = menuitem
            i += 1

    def getitemsinmenu(self, name):
        return self.menumap[name].itervalues()

    def delitemsinmenu(self, name, commit=defaultCommit):
        if self.menumap.has_key(name):
            for key in self.menumap[name].iterkeys():
                del self.menumap[name][key]
        self.writecursor.execute("delete from menuitem where menu=?;", (name,))
        if commit:
            self.conn.commit()

    def getmenu(self, name, window=None):
        if self.menu.has_key(name):
            return self.menu[name]
        elif window is not None:
            return self.loadmenu(name, window)
        else:
            raise Exception("When getting a menu for the first time, you need to supply the window to put it in.")


    def knowcanvas(self, name, w, h, wallpaper):
        self.readcursor.execute("select count(*) from canvas where name=?;", (name,))
        return self.readcursor.fetchone()[0] == 1

    def havecanvas(self, canvas):
        return self.knowcanvas(canvas.name)

    def mkcanvas(self, name, w, h, wallpaper, commit=defaultCommit):
        self.writecursor.execute("insert into canvas values (?, ?, ?, ?);",
                                 (name, w, h, wallpaper))
        if commit:
            self.conn.commit()

    def updcanvas(self, name, w, h, wallpaper, commit=defaultCommit):
        self.writecursor.execute("update canvas set width=?, height=?, wallpaper=? where name=?;",
                                 (w, h, wallpaper, name))
        if commit:
            self.conn.commit()

    def writecanvas(self, name, w, h, wallpaper, commit=defaultCommit):
        if self.knowcanvas(name):
            self.updcanvas(name, w, h, wallpaper, commit)
        else:
            self.mkcanvas(name, w, h, wallpaper, commit)

    def loadcanvas(self, name):
        self.readcursor.execute("select width, height, wallpaper from canvas where name=?;",
                                (name,))
        (w, h, wall) = self.readcursor.fetchone()
        canvas = Canvas(w, h, wall)
        canvas.name = name
        self.canvasmap[name] = canvas
        return canvas

    def getcanvas(self, name):
        if self.canvasmap.has_key(name):
            return self.canvasmap[name]
        else:
            return self.loadcanvas(name)

    def delcanvas(self, name, commit=defaultCommit):
        if self.canvasmap.has_key(name):
            del self.canvasmap[name]
        self.writecursor.execute("delete from canvas where name=?;", (name,))
        if commit:
            self.conn.commit()

    def knowpawn(self, name):
        self.readcursor.execute("select count(*) from pawn where name=?;", (name,))
        return self.readcursor.fetchone()[0] == 1

    def havepawn(self, pawn):
        return self.knowpawn(pawn.name)

    def mkpawn(self, name, img, item, canvas, x, y, spot, commit=defaultCommit):
        self.writecursor.execute("insert into pawn values (?, ?, ?, ?, ?, ?);",
                                 (name, img, item, canvas, x, y, spot))
        if commit:
            self.conn.commit()

    def updpawn(self, name, img, item, canvas, x, y, spot, commit=defaultCommit):
        self.writecursor.execute("update pawn set img=?, item=?, canvas=?, x=?, y=?, spot=? where name=?;",
                                 (name, img, item, canvas, x, y, spot))
        if commit:
            self.conn.commit()

    def writepawn(self, name, img, item, canvas, x, y, commit=defaultCommit):
        if self.knowpawn(name):
            self.updpawn(name, img, item, canvas, x, y, commit)
        else:
            self.mkpawn(name, img, item, canvas, x, y, commit)

    def loadpawn(self, name):
        self.readcursor.execute("select img, item, x, y, spot from pawn where name=?;",
                                (name,))
        (imgn, itemn, canvasn, x, y, spotn) = self.readcursor.fetchone()
        img = self.getimg(imgn)
        item = self.getitem(itemn)
        spot = self.getspot(spotn)
        spotgraph = spot.spotgraph
        place = self.getplace(spotn)
        pawn = Pawn(place, spotgraph, img, item, x, y)
        self.pawnmap[name] = pawn
        return pawn

    def getpawn(self, name):
        if self.pawnmap.has_key(name):
            return self.pawnmap[name]
        else:
            return self.loadpawn()

    def delpawn(self, name, commit=defaultCommit):
        if self.pawnmap.has_key(name):
            del self.pawnmap[name]
        self.writecursor.execute("delete from pawn where name=?;", (name,))
        if commit:
            self.conn.commit()

    def cullpawns(self, commit=defaultCommit):
        keeps = self.pawnmap.keys()
        left = "delete from pawn where name not in ("
        middle = "?, " * (len(keeps) - 1)
        right = "?);"
        querystr = left + middle + right
        self.writecursor.execute(querystr, keeps)
        if commit:
            self.conn.commit()

    def knowcolor(self, name):
        self.readcursor.execute("select count(*) from color where name=?;", (name,))
        return self.readcursor.fetchone()[0] == 1

    def havecolor(self, color):
        return self.knowcolor(color.name)

    def mkcolor(self, name, r, g, b, commit=defaultCommit):
        self.writecursor.execute("insert into color values (?, ?, ?, ?);", (name, r, g, b))
        if commit:
            self.conn.commit()

    def mkcolors(self, colortups, commit=defaultCommit):
        self.mkmany("color", colortups, commit)
    
    def updcolor(self, name, r, g, b, commit=defaultCommit):
        self.writecursor.execute("update color set red=?, green=?, blue=? where name=?;",
                                 (r, g, b, name))
        if commit:
            self.conn.commit()

    def writecolor(self, name, r, g, b, commit=defaultCommit):
        if self.knowcolor(name):
            self.updcolor(name, r, g, b, commit)
        else:
            self.mkcolor(name, r, g, b, commit)

    def savecolor(self, color, commit=defaultCommit):
        self.writecolor(color.name, color.red, color.green, color.blue)
        if commit:
            self.conn.commit()

    def loadcolor(self, name):
        self.readcursor.execute("select name, red, green, blue from color where name=?;", (name,))
        color = Color(*self.readcursor.fetchone())
        color.name = name
        self.colormap[name] = color
        return color

    def getcolor(self, name):
        if self.colormap.has_key(name):
            return self.colormap[name]
        else:
            return self.loadcolor(name)

    def delcolor(self, name, commit=defaultCommit):
        if self.colormap.has_key(name):
            del self.colormap[name]
        self.writecursor.execute("delete from color where name=?;", (name,))
        if commit:
            self.conn.commit()

    def knowstyle(self, name):
        self.readcursor.execute("select count(*) from style where name=?;", (name,))
        return self.readcursor.fetchone()[0] == 1

    def havestyle(self, style):
        return self.knowstyle(style.name)

    def mkstyle(self, name, fontface, fontsize, spacing,
                bg_inactive, bg_active, fg_inactive, fg_active, commit=defaultCommit):
        self.writecursor.execute("insert into style values (?, ?, ?, ?, ?, ?, ?, ?);",
                                 (name, fontface, fontsize, spacing, bg_inactive, bg_active,
                                  fg_inactive, fg_active))
        if commit:
            self.conn.commit()

    def mkstyles(self, styletups, commit=defaultCommit):
        self.mkmany("style", styletups, commit)

    def updstyle(self, name, fontface, fontsize, spacing,
                bg_inactive, bg_active, fg_inactive, fg_active, commit=defaultCommit):
        self.writecursor.execute("update style set fontface=?, fontsize=?, spacing=?, "
                                 "bg_inactive=?, bg_active=?, fg_inactive=?, fg_active=? "
                                 "where name=?;",
                                 (fontface, fontsize, spacing, bg_inactive, bg_active,
                                  fg_inactive, fg_active, name))
        if commit:
            self.conn.commit()

    def writestyle(self, name, fontface, fontsize, spacing,
                   bg_inactive, bg_active, fg_inactive, fg_active, commit=defaultCommit):
        if self.knowstyle(name):
            self.updstyle(name, fontface, fontsize, spacing, bg_inactive, bg_active,
                          fg_inactive, fg_active, commit)
        else:
            self.mkstyle(name, fontface, fontsize, spacing, bg_inactive, bg_active,
                         fg_inactive, fg_active, commit)

    def savestyle(self, style, commit=defaultCommit):
        self.writestyle(style.name, style.fontface, style.fontsize,
                        style.spacing, style.bg_inactive.name,
                        style.bg_active.name, style.fg_inactive.name,
                        style.fg_active.name, commit)

    def loadstyle(self, name):
        if not self.knowstyle(name):
            raise ValueError("No such style: %s" % name)
        self.readcursor.execute("select fontface, fontsize, spacing, "
                                "bg_inactive, bg_active, fg_inactive, "
                                "fg_active "
                                "from style where name=?;",
                                (name,))
        (ff, fs, s, bg_i, bg_a, fg_i, fg_a) = self.readcursor.fetchone()
        sty = Style(name, ff, fs, s, self.getcolor(bg_i),
                    self.getcolor(bg_a), self.getcolor(fg_i),
                    self.getcolor(fg_a))
        self.stylemap[name] = sty
        return sty

    def getstyle(self, name):
        if self.stylemap.has_key(name):
            return self.stylemap[name]
        else:
            return self.loadstyle(name)

    def delstyle(self, name):
        if self.stylemap.has_key(name):
            del self.stylemap[name]
        if self.knowstyle(name):
            self.writecursor.execute("delete from style where name=?;", (name,))

    def knowmenu(self, name):
        self.readcursor.execute("select count(*) from menu where name=?;", (name,))
        return self.readcursor.fetchone()[0] == 1

    def knowanymenu(self, tups):
        return self.knowany("menu", "(name)", tups)

    def knowallmenu(self, tups):
        return self.knowall("menu", "(name)", tups)

    def havemenu(self, menu):
        return self.knowmenu(menu.name)

    def mkmenu(self, name, x, y, w, h, sty, commit=defaultCommit):
        # mkplace et al. will insert multiple values for their contents
        # if they are supplied. To make this work similarly I should
        # take a style object for sty, rather than a string,
        # and insert all the colors before writing the menu w. style name.
        # But I kind of like this simpler way.
        self.writecursor.execute("insert into menu values (?, ?, ?, ?, ?, ?);",
                                 (name, x, y, w, h, sty))
        if commit:
            self.conn.commit()

    def mkmenus(self, menutups, commit=defaultCommit):
        self.mkmany("menu", menutups, commit)

    def updmenu(self, name, x, y, w, h, sty, commit=defaultCommit):
        self.writecursor.execute("update menu set x=?, y=?, width=?, height=?, style=? where name=?;",
                                 (x, y, w, h, sty, name))
        if commit:
            self.conn.commit()

    def writemenu(self, name, x, y, w, h, sty, commit=defaultCommit):
        if self.knowmenu(name):
            self.updmenu(name, x, y, w, h, sty, commit)
        else:
            self.mkmenu(name, x, y, w, h, sty, commit)

    def savemenu(self, menu, commit=defaultCommit):
        self.savestyle(menu.style)
        self.writemenu(menu.name, menu.getleft(), menu.getbot(),
                       menu.getwidth(), menu.getheight(), menu.style.name, commit)

    def loadmenu(self, name):
        if not self.knowmenu(name):
            raise ValueError("Menu does not exist: %s" % name)
        self.readcursor.execute("select x, y, width, height, style from menu where name=?;", (name,))
        (x, y, w, h, sty) = self.readcursor.fetchone()
        style = self.getstyle(sty)
        menu = Menu(x, y, w, h, style)
        menu.name = name
        self.menumap[name] = menu
        return menu
        
    def getmenu(self, name):
        if self.menumap.has_key(name):
            return self.menumap[name]
        elif window is not None:
            return self.loadmenu(name)
        else:
            raise Exception("Could not load the menu: " + name)

    def delmenu(self, name, commit=defaultCommit):
        if self.menumap.has_key(name):
            del self.menumap[name]
        if self.knowmenu(name):
            self.writecursor.execute("delete from menu where name=?;", (name,))
        if commit:
            self.conn.commit()


if testDB:
    import unittest
    from parms import DefaultParameters
    default = DefaultParameters()
    class DatabaseTestCase(unittest.TestCase):
        def testSomething(self, db, suf, clas, keytup, valtup, testname):
            # clas is the class of object to test.
            # keytup is a tuple of the primary key to use. valtup is a
            # tuple of the rest of the record to use. testSomething will
            # make the record for that key and those values and test that
            # stuff done with the record is correct. I've assumed that keytup concatenated with valtup
            mkargs = list(keytup)+list(valtup)
            print "mkargs = " + str(mkargs)
            knower = getattr(db, 'know'+suf)
            writer = getattr(db, 'write'+suf)
            saver = getattr(db, 'save'+suf)
            killer = getattr(db, 'del'+suf)
            loader = getattr(db, 'load'+suf)
            if testname == 'make':
                writer(*mkargs)
                self.assertTrue(knower(*keytup))
            elif testname == 'save':
                obj = loader(*keytup)
                killer(*keytup)
                saver(obj)
                self.assertTrue(knower(*keytup))
            elif testname == 'get':
                obj = loader(*keytup)
                getter = getattr(db, 'get'+suf)            
                writer(*mkargs)
                jbo = getter(*keytup)
                self.assertEqual(obj, jbo)
            elif testname == 'del':
                killer = getattr(db, 'del'+suf)
                writer(*mkargs)
                self.assertTrue(knower(*keytup))
                killer(*keytup)
                self.assertFalse(knower(*keytup))
        def runTest(self):
            testl = ['make', 'save', 'load', 'get', 'del', 'make']
            db = Database(":memory:")
            db.mkschema()
            tabkey = [ ('place', default.places, Place),
                       ('portal', default.portals, Portal),
                       ('thing', default.things, Thing),
                       ('color', default.colors, Color),
                       ('style', default.styles, Style),
                       ('menu', default.menus, Menu)]
            for pair in tabkey:
                suf = pair[0]
                for val in pair[1]:
                    for test in testl:
                        print "Testing %s%s" % (test, suf)
                        self.testSomething(db, suf, pair[2], val[0], val[1], test)
                          
    dtc = DatabaseTestCase()
    dtc.runTest()
realdb = Database(":memory:")
realdb.mkschema()
import parms
defaults = parms.DefaultParameters()
realdb.insert_defaults(defaults, True)