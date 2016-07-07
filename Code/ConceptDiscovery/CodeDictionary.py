"""Classes for storing and navigating a hierarchical code dictionary."""

# Python imports.
from collections import defaultdict
import heapq
import re


class CodeDictionary(object):
    """Class responsible for managing access to a clinical code hierarchy.

    The code hierarchy is represented as a directed acyclic graph, with each node recording its parents and children.
    For some hierarchies edges may have labels (e.g. is_a, has_a, part_of) that can be used when traversing the graph.
    Hierarchies with and without labels are treated the same, with a default label with no meaning being used in the
    case of hierarchies without labels.

    The code hierarchy is represented as a dictionary. An example (Read v2) hierarchy is:
    {
        "C":        {"Level": 1,    "Parents": [],               "Children": [("C1", None)],     "Description": "..."},
        "C1":       {"Level": 2,    "Parents": [("C", None)],    "Children": [("C10", None)],    "Description": "..."},
        "C10":      {"Level": 3,    "Parents": [("C1", None)],   "Children": [("C10E", None),    "Description": "..."},
                                                                              ("C10F", None)],
        "C10E":     {"Level": 4,    "Parents": [("C10", None)],  "Children": [("C10E4", None)],  "Description": "..."},
        "C10E4":    {"Level": 5,    "Parents": [("C10E", None)], "Children": [],                 "Description": "..."},
        "C10F":     {"Level": 4,    "Parents": [("C10", None)],  "Children": [("C10F8", None)],  "Description": "..."},
        "C10F8":    {"Level": 5,    "Parents": [("C10F", None)], "Children": [],                 "Description": "..."}
    }

    Here, None is the default label for the edge.

    """

    _codeHierarchy = None  # The representation of the code hierarchy.
    _wordDict = None  # The dictionary that maps a word to the codes where the word appears in the description.

    def __new__(cls, fileCodeDescriptions, dictType="readv2", delimiter='\t'):
        """Create a code dictionary.

        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str
        :param dictType:                The type of code dictionary to create. Allowed values are (case insensitive):
                                            readv2  - for Read v2 code hierarchies
                                            snomed  - for SNOMED hierarchies
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
                # Didn't get one of the permissible
                raise ValueError("{0:s} is not a permissible value for dictType".format(str(dictType)))
        else:
            # An attempt is being made to create a CodeDictionary subclass, so create the subclass.
            return super(CodeDictionary, cls).__new__(cls, fileCodeDescriptions, dictType, delimiter)

    def generalise_codes(self, initialCodes, searchLevel=1, childThreshold=0.2):
        """Generalise a set of codes by identifying more general codes that are similar to those in the initial set.

        For each code that is evaluated, each of its parent codes are examined in turn to determine the level of
        support they have from their children. A code's level of support is calculated as the fraction of its
        children that are either in the initial input code list or had enough support to be included in the generalised
        list of codes.

        Given the initial set of codes, the search proceeds by examining codes lowest in the hierarchy fist. This
        ensures that no code is examined before all of its children have been, and therefore that when a code is
        examined all information about the support it gets from its children is in place.

        Once all ancestor codes of the initial codes with sufficient support have been identified, all descendants
        of those ancestors are identified.

        :param initialCodes:    The set of codes to generalise from.
        :type initialCodes:     set
        :param searchLevel:     The level in the hierarchy where the search should stop. The search begins from the
                                    bottom/leaves of the hierarchy, and therefore a searchLevel of X means that only
                                    codes that occur at or below level X (i.e. their level is >= X) in the hierarchy
                                    can be added.
        :type searchLevel:      int
        :param childThreshold:  The fraction of child codes that must be positive before a parent code is added
                                    to the list of generalised codes.
        :type childThreshold:   float
        :return:                The generalised codes discovered during the search and their descendants.
                                    This consists of the ancestral codes of the initial codes that have been
                                    generalised to from the initial codes by going up the hierarchy and all
                                    descendant codes of these codes. This may or may not contain all the initial codes.
        :rtype:                 set

        """

        # Setup variables to record the different sets of codes needed.
        initAndGeneralCodes = set(initialCodes)  # All codes found (both initial and generalised).
        generalisedCodes = set()  # The generalised codes that have been found by examining their children.

        # Create a heap to store the codes that still need searching through. Python heaps are min heaps, and therefore
        # the smallest item is at the top/front of the heap. The levels are therefore stored as negatives in order to
        # ensure that the codes deeper in the hierarchy (closer to the leaves) are searched first.
        codesToSearch = [(-self._codeHierarchy[i]["Level"], i) for i in initAndGeneralCodes]
        heapq.heapify(codesToSearch)

        # Search through all codes (both initial and generalised) that need their children examining.
        # By searching through the hierarchy in a bottom up order there is no risk that a code will be evaluated for
        # generalisation before all its children have been. All information about the support a code gets from its
        # children is therefore in place before a code is examined.
        while codesToSearch:
            # Get the code at the top/front of the heap.
            level, code = heapq.heappop(codesToSearch)
            level *= -1  # Get the level back into the space of positive integers.

            # Determine whether any of the code's parents should be included based on the support of their child codes.
            # A parent should only be included if they have enough support from their child codes (i.e. enough of their
            # child codes are in the initial set or have been found through generalisation).
            # Only look at parents that were not in the initial list of codes and have not already been identified as
            # new codes to add. This ensures that each parent is only checked once.
            parents = set([i[0] for i in self._codeHierarchy[code]["Parents"]]) - initAndGeneralCodes
            for i in parents:
                # The only children that can provide support are those that are in the initial set of codes or have been
                # found through generalisation.
                children = set(j[0] for j in self._codeHierarchy[i]["Children"])
                supportingChildren = children & initAndGeneralCodes

                if children and (len(supportingChildren) / len(children)) > childThreshold:
                    # If the support is sufficient, then the parent should be added.
                    initAndGeneralCodes.add(i)
                    generalisedCodes.add(i)
                    parentLevel = level - 1  # Parent is one level up the hierarchy.
                    if parentLevel > searchLevel:
                        # If the parent's level is greater than the max search level (and therefore further down the
                        # hierarchy as level 1 is the root), then we need to search the parent.
                        heapq.heappush(codesToSearch, (-self._codeHierarchy[i]["Level"], i))

        # Identify the descendant codes of the codes that have been found through generalisation.
        generalDescendants = self.get_all_descendants(generalisedCodes)

        # Return the union of the codes found by generalising up and down the hierarchy.
        return generalisedCodes | generalDescendants

    def _get_relatives(self, codes, direction, relationships=None, levelsToIgnore=0, levelsToExtract=1):
        """Extract the relatives of a list of codes.

        Restrictions can be placed on the extraction through the relationships, levels to ignore and levels to extract.
        Relationships - Each edge has a label on it that determines what type of relationship the edge indicates
                            (e.g. part of, is a, has a). The extraction can be restricted to extracting only
                            relatives of the supplied codes that are reachable by traversing edges having one of the
                            supplied relationships.
        Levels to ignore - This can be used to ignore a number of levels of relatives above/below the supplied codes.
                               For example, to ignore immediate relatives (parents/children) and start extracting at
                               the second generation of relatives (grandparent/grandchild), set levels to ignore to 1.
        Levels to extract - This can be used to extract a set number of levels of relatives above/below the supplied
                                codes. For example, to select the immediate relatives (parents/children) and the next
                                generation of relatives (grandparents/grandchildren), set the levels to extract to 2
                                (and the levels to ignore to 0).

        :param codes:           The codes to extract the relatives for.
        :type codes:            list
        :param direction:       Whether descendants or ancestors should be extracted. Must be one of "Children" or
                                    "Parents".
        :type direction:        str
        :param relationships:   The relationships that should be traversed when extracting relatives. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to relatives reachable by traversing only a certain
                                    set of edge labels, but want to also extract all relatives reachable by an edge
                                    without an edge label, then include None in the list of relationships.
        :type relationships:    list
        :param levelsToIgnore:  The number of levels above/below the codes to ignore before extracting relatives.
        :type levelsToIgnore:   int
        :param levelsToExtract: The number of levels of relatives to extract.
        :type levelsToExtract:  int
        :return:                The extracted relatives' codes.
        :rtype:                 set

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

        return set(extractedRelatives)

    def get_all_ancestors(self, codes):
        """Get all the ancestors of a set of codes.

        If the input codes come from different levels in the code hierarchy, then the ancestor codes may contain
        some of the input codes. For example, with a Read v2 hierarchy if you give as input codes ["C10", "C10E"], then
        C10 will be in the set of ancestors (as it is an ancestor of C10E).

        :param codes:   The codes to get the ancestors of.
        :type codes:    iterable
        :return:        The ancestors of the given codes.
        :rtype:         set

        """

        codes = set(codes)  # Copy the set of input codes.
        ancestors = set()  # The ancestor codes.

        while codes:
            currentCode = codes.pop()
            parentCodes = {i[0] for i in self._codeHierarchy.get(currentCode, {}).get("Parents", [])}
            ancestors |= parentCodes
            codes |= parentCodes

        return ancestors

    def get_all_codes_at_level(self, level, relationships=None):
        """Get all codes of a given level in the code hierarchy.

        :param level:           The level of codes to return (e.g. 1 to return level 1 (top most level) codes).
        :type level:            int
        :param relationships:   The relationships that should be traversed when extracting codes. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to codes reachable by traversing only a certain
                                    set of edge labels, but want to also extract all codes reachable by an edge
                                    without an edge label, then include None in the list of relationships.
        :type relationships:    list
        :return:                All codes of the given level in the code hierarchy.
        :rtype:                 set

        """

        return self.get_reachable_codes_at_level([], level, relationships)

    def get_all_descendants(self, codes):
        """Get all the descendants of a set of codes.

        If the input codes come from different levels in the code hierarchy, then the descendant codes may contain
        some of the input codes. For example, with a Read v2 hierarchy if you give as input codes ["C10", "C10E"], then
        C10E will be in the set of descendants (as it is a descendant of C10).

        :param codes:   The codes to get the descendants of.
        :type codes:    iterable
        :return:        The descendants of the given codes.
        :rtype:         set

        """

        codes = set(codes)  # Copy the set of input codes.
        descendants = set()  # The descendant codes.

        while codes:
            currentCode = codes.pop()
            childCodes = {i[0] for i in self._codeHierarchy.get(currentCode, {}).get("Children", [])}
            descendants |= childCodes
            codes |= childCodes

        return descendants

    def get_ancestors(self, codes, relationships=None, levelsToIgnore=0, levelsToExtract=1):
        """Extract the ancestors of a list of codes.

        Restrictions can be placed on the extraction through the relationships, levels to ignore and levels to extract.
        Relationships - Each edge has a label on it that determines what type of relationship the edge indicates
                            (e.g. part of, is a, has a). The extraction can be restricted to extracting only
                            ancestors of the supplied codes that are reachable by traversing edges having one of the
                            supplied relationships.
        Levels to ignore - This can be used to ignore a number of levels of ancestors above the supplied codes. For
                               example, to ignore the immediate parents and start extracting at the grandparent level,
                               set levels to ignore to 1.
        Levels to extract - This can be used to extract a set number of levels of ancestors above the supplied codes. For
                                example, to select the parents and grandparents set the levels to extract to 2 (and
                                the levels to ignore to 0).

        :param codes:           The codes to extract the ancestors for.
        :type codes:            list
        :param relationships:   The relationships that should be traversed when extracting ancestors. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to ancestors reachable by traversing only a certain
                                    set of edge labels, but want to also extract all ancestors reachable by an edge
                                    without an edge label, then include None in the list of relationships.
        :type relationships:    list
        :param levelsToIgnore:  The number of levels below the current codes to ignore before extracting ancestors.
        :type levelsToIgnore:   int
        :param levelsToExtract: The number of levels of ancestors to extract.
        :type levelsToExtract:  int
        :return:                The extracted parent codes.
        :rtype:                 set

        """

        return self._get_relatives(codes, "Parents", relationships, levelsToIgnore, levelsToExtract)

    def get_descendants(self, codes, relationships=None, levelsToIgnore=0, levelsToExtract=1):
        """Extract the descendants of a list of codes.

        Restrictions can be placed on the extraction through the relationships, levels to ignore and levels to extract.
        Relationships - Each edge has a label on it that determines what type of relationship the edge indicates
                            (e.g. part of, is a, has a). The extraction can be restricted to extracting only
                            descendants of the supplied codes that are reachable by traversing edges having one of the
                            supplied relationships.
        Levels to ignore - This can be used to ignore a number of levels of descendants below the supplied codes. For
                               example, to ignore the immediate children and start extracting at the grandchild level,
                               set levels to ignore to 1.
        Levels to extract - This can be used to extract a set number of levels of descendants below the supplied codes. For
                                example, to select the children and grandchildren set the levels to extract to 2 (and
                                the levels to ignore to 0).

        :param codes:           The codes to extract the descendants for.
        :type codes:            list
        :param relationships:   The relationships that should be traversed when extracting descendants. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to descendants reachable by traversing only a certain
                                    set of edge labels, but want to also extract all descendants reachable by an edge
                                    without an edge label, then include None in the list of relationships.
        :type relationships:    list
        :param levelsToIgnore:  The number of levels below the current codes to ignore before extracting descendants.
        :type levelsToIgnore:   int
        :param levelsToExtract: The number of levels of descendants to extract.
        :type levelsToExtract:  int
        :return:                The extracted child codes.
        :rtype:                 set

        """

        return self._get_relatives(codes, "Children", relationships, levelsToIgnore, levelsToExtract)

    def get_reachable_codes_at_level(self, codes, level, relationships=None):
        """Get all codes of a given level that are reachable in the code hierarchy from the input codes.

        Example for Read v2 hierarchy - Given codes [1Z1, 1Z10, C10, C10E, C10E0]:
        level 1 - [1, C]
        level 2 - [1Z, C1]
        level 3 - [1Z1, C10]
        level 4 - [1Z1., C10.]
        level 5 - [1Z1.., C10..]
        Where . means any character that validly follows from the preceding character in the code hierarchy (e.g. C10F
        is valid but C10Z is not for Read v2).

        :param codes:           The codes that are to have their ancestors/descendants found. If this list is empty,
                                    will return all codes in the hierarchy at the given level.
        :type codes:            list
        :param level:           The level of codes to return (e.g. 1 to return level 1 (top most level) codes).
        :type level:            int
        :param relationships:   The relationships that should be traversed when extracting codes. To ignore
                                    edge labels when extracting, set this value to a falsey value (e.g. None).
                                    If you're restricting extraction to codes reachable by traversing only a certain
                                    set of edge labels, but want to also extract all codes reachable by an edge
                                    without an edge label, then include None in the list of relationships.
        :type relationships:    list
        :return:                The codes of the given level that can be reached by traversing the hierarchy starting
                                    at the given list of codes. Alternatively, all codes at the given level if no
                                    codes were given as input.
        :rtype:                 set

        """

        reachableCodes = set()  # The codes of the given level reachable from the input codes.

        if codes:
            # Go through each code and find the codes in the hierarchy of the given level reachable from it.
            for i in codes:
                codeLevel = self._codeHierarchy[i]["Level"]
                if codeLevel == level:
                    # This code is already of the correct level, so just add it to the set of codes to return.
                    reachableCodes.add(i)
                else:
                    # Find the codes of the given level reachable from this code. We need to find descendants if the
                    # current code is at a lower level than the desired level (i.e. if this code is level 1 and the
                    # desired level is level 3), and ancestors otherwise. We also need to skip levels in the hierarchy
                    # if the given level is more than one away from the current code's level (i.e. the current code is
                    # level 1 and the given level is 3).
                    findAncestorsOrDescendants = "Children" if codeLevel < level else "Parents"
                    levelsToSkip = abs(self._codeHierarchy[i]["Level"] - level) - 1
                    reachableCodes |= set(self._get_relatives(
                        [i], findAncestorsOrDescendants, relationships=relationships, levelsToIgnore=levelsToSkip,
                        levelsToExtract=1))
        else:
            # Extract all codes at the given level if no input codes were given.
            reachableCodes = set([i for i in self._codeHierarchy if self._codeHierarchy[i]["Level"] == level])

        return reachableCodes

    def get_codes_from_words(self, words):
        """Get codes based on bags of words.

        Each entry in words should contain a list of words, all of which must be present in a code's description
        before the code will be returned for that entry.

        :param words:   The words to find codes for. Each entry should contain a list of words, all of which must be
                            present in a code's description before the code is deemed to be a match. Each word is
                            assumed to be a string.
        :type words:    tuple of lists
        :return:        Sets of codes. Element i of the return value will contain the codes that have descriptions
                            with all the words contained in words[i].
        :rtype:         list of sets

        """

        # Go through each bag of words and select only the codes that contain all words in the bag in their description.
        returnValue = []
        for i in words:
            # If the bag of words i is empty, then just return an empty set for it. If the bag contains words, then
            # make a copy of the codes with the first word and iterate through the remaining words.
            codes = set(self._wordDict.get(i[0], set())) if i else set()
            for j in i[1:]:
                # For each word, restrict the set of codes returned to those containing that word in their description.
                codes &= self._wordDict.get(j, set())
            returnValue.append(codes)
        return returnValue

    def get_codes_from_regexp(self, regexps):
        """Get the codes that have a description where all the supplied regular expressions match.

        Each entry in regexps should contain a set of regular expression strings, all of which must be found in a given
        code's description before the code will be returned for that entry. Each string will be padded so that it
        matches with an additional whitespace/start of line character before it, and an additional whitespace/end of
        line character after it. The search is case insensitive.

        :param regexps: Sets of regular expressions. Each entry should contain a set of regular expressions, all of
                            which must be found in a code's description before the code is deemed a match. Each regular
                            expression is assumed to be a string.
        :type regexps:  list of sets
        :return:        Sets of codes. Element i of the return value will contain the codes that have descriptions
                            containing all regular expressions in regexps[i].
        :rtype:         list of sets

        """

        # Compile all regular expressions.
        regexps = [{re.compile("(\s|^){0:s}(\s|$)".format(j), re.IGNORECASE) for j in i} for i in regexps]

        # Iterate through all the codes in the hierarchy, checking the description of each one against the sets
        # of regular expressions.
        returnValue = [set() for i in regexps]
        for i in self._codeHierarchy:
            codeDescription = self._codeHierarchy[i]["Description"]  # The description of the code.
            for index, j in enumerate(regexps):
                # Iterate through the sets of regular expressions and check whether all of them in a given set can be
                # found in the code's description.
                if j and all([k.search(codeDescription) for k in j]):
                    returnValue[index].add(i)
        return returnValue

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


class _ReadDictionary(CodeDictionary):
    """Create a Read code dictionary."""

    def __init__(self, fileCodeDescriptions, dictType, delimiter='\t'):
        """Initialise the Read code dictionary.

        The file containing the code descriptions is assumed to contain one code and description per line, with the
        code coming first, followed by the delimiter and then the description. Codes in the file are assumed to have
        no additional characters (e.g. trailing full stops or percentage signs).

        :param fileCodeDescriptions:    The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeDescriptions:     str
        :param dictType:                The type of code dictionary to create.
        :type dictType:                 str
        :param delimiter:               The delimiter between the code and its description in the file.
        :type delimiter:                str

        """

        # Initialise the code hierarchy.
        self._codeHierarchy = defaultdict(lambda: {"Level": None, "Parents": [], "Children": [], "Description": ""})

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
                    self._codeHierarchy[code]["Level"] = len(code)
                    if len(code) > 1:
                        # If the code consists of at least 2 characters, then the code has a parent and is therefore the
                        # child of that parent.
                        self._codeHierarchy[code]["Parents"] = [(code[:-1], None)]
                        self._codeHierarchy[code[:-1]]["Children"].append((code, None))

                    # Some descriptions start with something like [V]XXX. In order to match XXX as a real word, a space
                    # must be inserted between [V] and XXX.
                    chunks[1] = re.sub("^\[[a-zA-Z]+\]", "\g<0> ", chunks[1])

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
