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

    _codeHierarchy = None  # The representation of the code hierarchy.

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

    def get_children(self, codes, relationships=None, levelsToIgnore=0, levelsToExtract=1):
        """Extract the children of a list of codes.

        Restrictions can be placed on the extraction through the relationships, levels to ignore and levels to extract.
        Relationships - Each edge has a label on it that determines what type of relationship the edge indicates
                            (e.g. part of, is a, has a). The child extraction can be restricted to extracting only
                            children of the supplied codes that have one of the supplied relationships.
        Levels to ignore - This can be used to ignore a number of levels of children below the supplied codes. For
                               example, to ignore the immediate children and start extracting at the grandchild level,
                               set levels to ignore to 1.
        Levels to extract - This can be used to extract a set number of levels of children below the supplied codes. For
                                example, to select the children and grandchildren set the levels to extract to 2 (and
                                the levels to ignore to 0).

        :param codes:           The codes to extract the children for.
        :type codes:            list
        :param relationships:   The relationships that should be traversed when extracting children. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to children with only a certain set of edge labels,
                                    but want to also extract all children without an edge label, then include None in
                                    the list of relationships.
        :type relationships:    list
        :param levelsToIgnore:  The number of levels below the current codes to ignore before extracting children.
        :type levelsToIgnore:   int
        :param levelsToExtract: The number of levels of children to extract.
        :type levelsToExtract:  int
        :return:                The extracted child codes.
        :rtype:                 list

        """

        if levelsToIgnore < 0:
            # The levels to ignore must be at least 0.
            raise ValueError("The levels to ignore must be at least 0.")
        if levelsToExtract < 0:
            # The levels to extract must be at least 0.
            raise ValueError("The levels to extract must be at least 0.")

        extractedChildren = []  # The extracted child codes.
        currentCodes = codes  # The current set of codes having their children extracted.

        if relationships:
            # We have some restrictions on the edge labels that we can traverse.

            # Skip through the levels of children that we're supposed to ignore.
            while levelsToIgnore:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Children", [])
                                if j[1] in relationships]

                # Update the current codes and the number of levels that need ignoring.
                currentCodes = nextLvlCodes
                levelsToIgnore -= 1

            # Start extracting children as we've reached the correct level.
            while levelsToExtract:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Children", [])
                                if j[1] in relationships]

                # Update the current codes, the extracted codes and the number of levels that still need extracting.
                currentCodes = nextLvlCodes
                extractedChildren.extend(nextLvlCodes)  # Extract the child codes of the current codes.
                levelsToExtract -= 1
        else:
            # We have no restrictions on edge labels, and will extract all children regardless of the edge label.

            # Skip through the levels of children that we're supposed to ignore.
            while levelsToIgnore:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Children", [])]

                # Update the current codes and the number of levels that need ignoring.
                currentCodes = nextLvlCodes
                levelsToIgnore -= 1

            # Start extracting children as we've reached the correct level.
            while levelsToExtract:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Children", [])]

                # Update the current codes, the extracted codes and the number of levels that still need extracting.
                currentCodes = nextLvlCodes
                extractedChildren.extend(nextLvlCodes)  # Extract the child codes of the current codes.
                levelsToExtract -= 1

        return extractedChildren

    def get_descriptions(self, codes=None):
        """Get the descriptions of a list of codes or of all codes in the hierarchy.

        If codes is None, then all codes in the hierarchy will have their descriptions extracted, otherwise only
        the descriptions for the provided codes will be extracted.

        Any supplied code that is not in the hierarchy will be ignored.

        :param codes:   The codes to extract the descriptions for.
        :type codes:    list
        :return:        The descriptions of the input codes.
        :rtype:         list

        """

        if codes:
            # If codes are supplied return their descriptions.
            return [self._codeHierarchy[i]["Description"] for i in codes if i in self._codeHierarchy]
        else:
            # If no codes are supplied return the descriptions of all codes.
            return [self._codeHierarchy[i]["Description"] for i in self._codeHierarchy]

    def get_parents(self, codes, relationships=None, levelsToIgnore=0, levelsToExtract=1):
        """Extract the parents of a list of codes.

        Restrictions can be placed on the extraction through the relationships, levels to ignore and levels to extract.
        Relationships - Each edge has a label on it that determines what type of relationship the edge indicates
                            (e.g. part of, is a, has a). The parent extraction can be restricted to extracting only
                            parents of the supplied codes that have one of the supplied relationships.
        Levels to ignore - This can be used to ignore a number of levels of parents above the supplied codes. For
                               example, to ignore the immediate parents and start extracting at the grandparent level,
                               set levels to ignore to 1.
        Levels to extract - This can be used to extract a set number of levels of parents above the supplied codes. For
                                example, to select the parents and grandparents set the levels to extract to 2 (and
                                the levels to ignore to 0).

        :param codes:           The codes to extract the parents for.
        :type codes:            list
        :param relationships:   The relationships that should be traversed when extracting children. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to parents with only a certain set of edge labels,
                                    but want to also extract all parents without an edge label, then include None in
                                    the list of relationships.
        :type relationships:    list
        :param levelsToIgnore:  The number of levels below the current codes to ignore before extracting parents.
        :type levelsToIgnore:   int
        :param levelsToExtract: The number of levels of parents to extract.
        :type levelsToExtract:  int
        :return:                The extracted parent codes.
        :rtype:                 list

        """

        if levelsToIgnore < 0:
            # The levels to ignore must be at least 0.
            raise ValueError("The levels to ignore must be at least 0.")
        if levelsToExtract < 0:
            # The levels to extract must be at least 0.
            raise ValueError("The levels to extract must be at least 0.")

        extractedParents = []  # The extracted parent codes.
        currentCodes = codes  # The current set of codes having their parents extracted.

        if relationships:
            # We have some restrictions on the edge labels that we can traverse.

            # Skip through the levels of parents that we're supposed to ignore.
            while levelsToIgnore:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Parents", [])
                                if j[1] in relationships]

                # Update the current codes and the number of levels that need ignoring.
                currentCodes = nextLvlCodes
                levelsToIgnore -= 1

            # Start extracting parents as we've reached the correct level.
            while levelsToExtract:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Parents", [])
                                if j[1] in relationships]

                # Update the current codes, the extracted codes and the number of levels that still need extracting.
                currentCodes = nextLvlCodes
                extractedParents.extend(nextLvlCodes)  # Extract the parent codes of the current codes.
                levelsToExtract -= 1
        else:
            # We have no restrictions on edge labels, and will extract all children regardless of the edge label.

            # Skip through the levels of parents that we're supposed to ignore.
            while levelsToIgnore:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Parents", [])]

                # Update the current codes and the number of levels that need ignoring.
                currentCodes = nextLvlCodes
                levelsToIgnore -= 1

            # Start extracting parents as we've reached the correct level.
            while levelsToExtract:
                # Get the child codes of the codes at the current level.
                nextLvlCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get("Parents", [])]

                # Update the current codes, the extracted codes and the number of levels that still need extracting.
                currentCodes = nextLvlCodes
                extractedParents.extend(nextLvlCodes)  # Extract the parent codes of the current codes.
                levelsToExtract -= 1

        return extractedParents


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
        self._codeHierarchy = defaultdict(lambda: {"Parents": [], "Children": [], "Description": ""})

        if dictType == "readv2":
            # A Read v2 code hierarchy is being constructed.
            with open(fileCodeDescriptions, 'r') as fidCodeDescriptions:
                for line in fidCodeDescriptions:
                    line = line.strip()
                    chunks = line.split('\t')
                    code = chunks[0]
                    self._codeHierarchy[code]["Description"] = chunks[1]
                    if len(code) > 1:
                        # If the code consists of at least 2 characters, then the code has a parent and is therefore the
                        # child of that parent.
                        self._codeHierarchy[code]["Parents"] = [(code[:-1], None)]
                        self._codeHierarchy[code[:-1]]["Children"].append((code, None))


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
