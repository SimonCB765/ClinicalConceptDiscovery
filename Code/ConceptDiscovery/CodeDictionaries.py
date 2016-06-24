"""Classes for storing and navigating a hierarchical code dictionary."""

# Python imports.
from collections import defaultdict


class CodeDictionary(object):
    """Class responsible for managing access to a clinical code hierarchy.

    The code hierarchy is represented as a directed acyclic graph, with each node recording its parents and children.
    For some hierarchies edges may have labels (e.g. is_a, has_a, part_of) that can be used when traversing the graph.
    Hierarchies with and without labels are treated the same, with a default label with no meaning being used in the
    case of hierarchies without labels.

    The code hierarchy is represented as a dictionary. An example (Read v2) hierarchy is:
    {
        "C":        {"Parents": [],               "Children": [("C1", None)],                   "Description": "..."},
        "C1":       {"Parents": [("C", None)],    "Children": [("C10", None)],                  "Description": "..."},
        "C10":      {"Parents": [("C1", None)],   "Children": [("C10E", None), ("C10F", None)], "Description": "..."},
        "C10E":     {"Parents": [("C10", None)],  "Children": [("C10E4", None)],                "Description": "..."},
        "C10E4":    {"Parents": [("C10E", None)], "Children": [],                               "Description": "..."},
        "C10F":     {"Parents": [("C10", None)],  "Children": [("C10F8", None)],                "Description": "..."},
        "C10F8":    {"Parents": [("C10F", None)], "Children": [],                               "Description": "..."}
    }

    Here, None is the default label for the edge.

    """

    def __new__(cls, fileCodeDescriptions, dictType="Readv2"):
        """Create a code dictionary.

        :param dictType:                The type of code dictionary to create.
        :type dictType:                 str
        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str
        :return:                        A CodeDictionary subclass determined by the dictType parameter.
        :rtype:                         CodeDictionary subclass

        """

        if cls is CodeDictionary:
            # An attempt is being made to create a CodeDictionary, so determine which subclass to generate.
            if dictType.lower() == "readv2":
                # Generate a ReadDictionary.
                return super(CodeDictionary, cls).__new__(ReadDictionary)
            elif dictType.lower() == "snomed":
                # Generate a SNOMEDDictionary.
                return super(CodeDictionary, cls).__new__(SNOMEDDictionary)
        else:
            # An attempt is being made to create a CodeDictionary subclass, so create the subclass.
            return super(CodeDictionary, cls).__new__(cls, fileCodeDescriptions, dictType)

    def get_children(self, levelsToCheck=1):
        pass

    def get_descriptions(self):
        pass

    def get_parents(self, levelsToCheck=1):
        pass


class ReadDictionary(CodeDictionary):
    """Create a Read code dictionary."""

    def __init__(self, fileCodeDescriptions, dictType):
        """Initialise the Read code dictionary.

        :param dictType:                The type of code dictionary to create.
        :type dictType:                 str
        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str

        """

        # Initialise the code hierarchy.
        self.mapCodeToDescription = defaultdict(lambda: {"Parents": [], "Children": [], "Description": ""})

        if dictType == "readv2":
            # A Read v2 code hierarchy is being constructed.
            with open(fileCodeDescriptions, 'r') as fidCodeDescriptions:
                for line in fidCodeDescriptions:
                    line = line.strip()
                    chunks = line.split('\t')
                    code = chunks[0]
                    self.mapCodeToDescription[code]["Description"] = chunks[1]
                    if len(code) > 1:
                        # If the code consists of at least 2 characters, then the code has a parent and is therefore the
                        # child of that parent.
                        self.mapCodeToDescription[code]["Parents"] = [(code[:-1], None)]
                        self.mapCodeToDescription[code[:-1]]["Children"].append((code, None))


class SNOMEDDictionary(CodeDictionary):
    """Create a SNOMED code dictionary."""

    def __init__(self, fileCodeDescriptions, dictType):
        """Initialise the SNOMED code dictionary.

        :param dictType:                The type of code dictionary to create.
        :type dictType:                 str
        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str

        """

        pass
