from attrcheck import AttrCheck


class Thing:
    table_schema = ("CREATE TABLE thing "
                    "(dimension, name text, "
                    "foreign key(dimension, name) "
                    "references item(dimension, name));")

    def __init__(self, dimension, name, location, contents=[]):
        self.dimension = dimension
        self.name = name
        self.location = location
        self.contents = contents
        self.permissions = []
        self.forbiddions = []
        self.permit_inspections = []
        self.forbid_inspections = []

    def __str__(self):
        return "(%s, %s)" % (self.dimension, self.name)

    def __iter__(self):
        return (self.dimension, self.name)

    def __repr__(self):
        if self.location is None:
            loc = "nowhere"
        else:
            loc = str(self.location)
        return self.name + "@" + loc

    def add_item(self, it):
        if it in self.cont:
            return False
        elif self.permitted(it):
            self.cont.append(it)
            return True
        elif self.forbidden(it):
            return False
        elif self.can_contain(it):
            self.cont.append(it)
            return True
        else:
            return False

    def permit_item(self, it):
        self.forbiddions.remove(it)
        self.permissions.append(it)

    def forbid_item(self, it):
        self.permissions.remove(it)
        self.forbiddions.append(it)

    def add_inspection(self, attrn, vals, lower, upper, permit):
        spect = AttrCheck(attrn, vals, lower, upper)
        if permit:
            self.permit_inspections.append(spect)
        else:
            self.forbid_inspections.append(spect)

    def attrcheck_permit(self, attrn, vals, lower, upper):
        """When I receive an instruction to add an item, if the item is
        in neither permissions nor forbiddions, I will see if its
        attribute by the name of attrn passes the given test. The test
        is in three parts. Firstly, if the value of attrn is in the
        list vals, the item is permitted--don't bother with the rest
        of the checks, just add it to contents. Second, check that the
        attribute falls between the given lower and upper bounds, and
        if so, add it to contents. Finally, proceed to the next
        inspection."""
        self.add_inspection(attrn, vals, lower, upper, True)

    def attrcheck_forbid(self, attrn, vals, lower, upper):
        self.add_inspection(attrn, vals, lower, upper, False)

# TODO: methods of Thing to get instances of those classes and inspect
# items who want to enter to make sure they pass.
#
# TODO: subclasses of thing to differentiate between things and other things

classes = [Thing]
table_schemata = [clas.table_schema for clas in classes]
