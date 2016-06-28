"""Classes for storing and navigating a hierarchical code dictionary."""

# Python imports.
from collections import defaultdict
import re


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
    _wordDict = None  # The dictionary that maps a word to the codes where the word appears in the description.

    def __new__(cls, fileCodeDescriptions, dictType="readv2", delimiter='\t'):
        """Create a code dictionary.

        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str
        :param dictType:                The type of code dictionary to create.
        :type dictType:                 str
        :param delimiter:               The delimiter between the code and its description in the file.
        :type delimiter:                str
        :return:                        A CodeDictionary subclass determined by the dictType parameter.
        :rtype:                         CodeDictionary subclass

        """

        if cls is CodeDictionary:
            # An attempt is being made to create a CodeDictionary, so determine which subclass to generate.
            if dictType.lower() == "readv2":
                # Generate a _ReadDictionary.
                return super(CodeDictionary, cls).__new__(_ReadDictionary)
            elif dictType.lower() == "snomed":
                # Generate a _SNOMEDDictionary.
                return super(CodeDictionary, cls).__new__(_SNOMEDDictionary)
        else:
            # An attempt is being made to create a CodeDictionary subclass, so create the subclass.
            return super(CodeDictionary, cls).__new__(cls, fileCodeDescriptions, dictType, delimiter)

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

        return self._get_relatives(codes, "Children", relationships, levelsToIgnore, levelsToExtract)

    def get_codes_from_words(self, words):
        """Get the codes that have a description containing all the supplied words.

        :param words:   The words to find the codes for. Each word is assumed to be a string.
        :type words:    set
        :return:        The codes with descriptions that contain all the words.
        :rtype:         set

        """

        codes = set()
        for i in words:
            codes &= self._wordDict.get(i, None)
        return codes

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

        return self._get_relatives(codes, "Parents", relationships, levelsToIgnore, levelsToExtract)

    def _get_relatives(self, codes, direction, relationships=None, levelsToIgnore=0, levelsToExtract=1):
        """Extract the relatives of a list of codes.

        Restrictions can be placed on the extraction through the relationships, levels to ignore and levels to extract.
        Relationships - Each edge has a label on it that determines what type of relationship the edge indicates
                            (e.g. part of, is a, has a). The extraction can be restricted to extracting only
                            relatives of the supplied codes that have one of the supplied relationships.
        Levels to ignore - This can be used to ignore a number of levels of relatives above/below the supplied codes.
                               For example, to ignore immediate relatives (parents/children) and start extracting at
                               the second generation of relatives (grandparent/grandchild), set levels to ignore to 1.
        Levels to extract - This can be used to extract a set number of levels of relatives above/below the supplied
                                codes. For example, to select the immediate relatives (parents/children) and the next
                                generation of relatives (grandparents/grandchildren), set the levels to extract to 2
                                (and the levels to ignore to 0).

        :param codes:           The codes to extract the relatives for.
        :type codes:            list
        :param direction:       Whether children or parents should be extracted. Must be one of "Children" or "Parents".
        :type direction:        str
        :param relationships:   The relationships that should be traversed when extracting relatives. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to relatives with only a certain set of edge
                                    labels, but want to also extract all relatives without an edge label, then include
                                    None in the list of relationships.
        :type relationships:    list
        :param levelsToIgnore:  The number of levels above/below the codes to ignore before extracting relatives.
        :type levelsToIgnore:   int
        :param levelsToExtract: The number of levels of relatives to extract.
        :type levelsToExtract:  int
        :return:                The extracted relatives' codes.
        :rtype:                 list

        """

        if direction not in ["Parents", "Children"]:
            # The direction must be one of "Parents" or "Children".
            raise ValueError("The direction must be one of \"Parents\" or \"Children\".")
        if levelsToIgnore < 0:
            # The levels to ignore must be at least 0.
            raise ValueError("The levels to ignore must be at least 0.")
        if levelsToExtract < 0:
            # The levels to extract must be at least 0.
            raise ValueError("The levels to extract must be at least 0.")

        extractedRelatives = []  # The extracted relatives' codes.
        currentCodes = codes  # The current set of codes having their relatives extracted.

        while levelsToIgnore or levelsToExtract:
            # Get the codes for the relatives of the codes at the current level (respecting potential edge
            # label restrictions).
            relativeCodes = [j[0] for i in currentCodes for j in self._codeHierarchy.get(i, {}).get(direction, [])
                             if (not relationships) or (j[1] in relationships)]

            # The relatives' codes are the codes that need checking next.
            currentCodes = relativeCodes

            if levelsToIgnore:
                # There are still levels of codes that need ignoring, therefore don't extract the relatives' codes.
                levelsToIgnore -= 1
            else:
                # There are not levels of codes that need ignoring, therefore extract the relatives' codes.
                extractedRelatives.extend(relativeCodes)
                levelsToExtract -= 1

        return extractedRelatives


class _ReadDictionary(CodeDictionary):
    """Create a Read code dictionary."""

    def __init__(self, fileCodeDescriptions, dictType, delimiter='\t'):
        """Initialise the Read code dictionary.

        The file containing the code descriptions is assumed to contain one code and description per line, with the
        code coming first, followed by the delimiter and then the description.

        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str
        :param dictType:                The type of code dictionary to create.
        :type dictType:                 str
        :param delimiter:               The delimiter between the code and its description in the file.
        :type delimiter:                str

        """

        # Initialise the code hierarchy.
        self._codeHierarchy = defaultdict(lambda: {"Parents": [], "Children": [], "Description": "", "Searchable": ""})

        # Initialise the word dictionary.
        self._wordDict = defaultdict(set)

        # Compile the word splitting regular expression.
        wordFinder = re.compile("\s+")

        if dictType == "readv2":
            # A Read v2 code hierarchy is being constructed.
            with open(fileCodeDescriptions, 'r') as fidCodeDescriptions:
                for line in fidCodeDescriptions:
                    line = line.strip()
                    chunks = line.split(delimiter)
                    code = chunks[0]
                    self._codeHierarchy[code]["Description"] = chunks[1]
                    self._codeHierarchy[code]["Searchable"] = chunks[1].lower()
                    if len(code) > 1:
                        # If the code consists of at least 2 characters, then the code has a parent and is therefore the
                        # child of that parent.
                        self._codeHierarchy[code]["Parents"] = [(code[:-1], None)]
                        self._codeHierarchy[code[:-1]]["Children"].append((code, None))

                    # Split the description into words.
                    words = wordFinder.split(chunks[1])

                    # Update the word dictionary.
                    for i in words:
                        self._wordDict[i].add(code)


class _SNOMEDDictionary(CodeDictionary):
    """Create a SNOMED code dictionary."""

    def __init__(self, fileCodeDescriptions, dictType, delimiter='\t'):
        """Initialise the SNOMED code dictionary.

        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str
        :param dictType:                The type of code dictionary to create.
        :type dictType:                 str
        :param delimiter:               The delimiter between the code and its description in the file.
        :type delimiter:                str

        """

        pass
