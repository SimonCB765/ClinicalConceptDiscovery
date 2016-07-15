"""Class for running concept related queries on a Neo4j database of clinical codes."""

# Python imports.
import logging

# Globals.
LOGGER = logging.getLogger(__name__)


class DatabaseOperations(object):
    """Class defining high level queries to run on a Neo4j database of clinical code."""

    def __init__(self, databaseController):
        """Initialise an object.

        :param databaseController:  The object controlling access to the Neo4j database.
        :type databaseController:   DatabaseManager object

        """

        self._databaseController = databaseController

    def get_codes_from_phrases(self, phrases, codeFormat=None):
        """Get the codes that have a description where all the supplied quoted phrases match.

        Each entry in quoted should contain a set of phrase strings, all of which must be found in a given
        code's description before the code will be returned for that entry.

        The search is case insensitive.

        :param phrases:     Sets of phrases. Each entry should contain a set of phrases, all of which must be found in
                                a code's description before the code is deemed a match.
        :type phrases:      list of sets
        :param codeFormat:  The code format to look through when extracting descriptions
        :type codeFormat:   str
        :return:            Sets of codes. Element i of the return value will contain the codes that have descriptions
                                containing all phrases in quoted[i].
        :rtype:             list of sets

        """

        # Get access to the database
        session = self._databaseController.generate_session()

        # Go through each set of hrases and select only the codes that contain all phrases in their description.
        returnValue = []
        for i in phrases:
            # Find all codes that have a relationship with every word in the bag of words.
            uniquePhrases = set([j.lower() for j in i])  # Remove any duplicate phrases and make them all lowercase.
            result = session.run("MATCH (c:{0:s}) "
                                 "WHERE ALL(regexp IN ['{1:s}'] WHERE c.description CONTAINS regexp) "
                                 "RETURN c.code AS code"
                                 .format(codeFormat if codeFormat else "Code",
                                         "', '".join(uniquePhrases), len(uniquePhrases)))

            # Record the codes with a description that contains all the phrases.
            returnValue.append([j["code"] for j in result])

        # Close the session.
        session.close()

        return returnValue

    def get_codes_from_words(self, words, codeFormat=None):
        """Get codes based on bags of words.

        Each entry in words should contain a list of words, all of which must be present in a code's description
        before the code will be returned for that entry.

        :param words:       The words to find codes for. Each entry should contain a list of words, all of which must be
                                present in a code's description before the code is deemed to be a match. Each word is
                                assumed to be a string.
        :type words:        list of lists
        :param codeFormat:  The code format to look through when extracting descriptions
        :type codeFormat:   str
        :return:            Sets of codes. Element i of the return value will contain the codes that have descriptions
                                with all the words contained in words[i].
        :rtype:             list of sets

        """

        # Get access to the database
        session = self._databaseController.generate_session()

        # Go through each bag of words and select only the codes that contain all words in the bag in their description.
        returnValue = []
        for i in words:
            # Find all codes that have a relationship with every word in the bag of words. The method used here relies
            # on each word having a unique node.
            wordBag = set(i)  # Remove any duplicate words in the bag.
            result = session.run("MATCH (c:{0:s}) -[:DescribedBy]-> (w:Word) "
                                 "WHERE w.word IN ['{1:s}']"
                                 "WITH c.code AS code, COLLECT(w.word) AS words "
                                 "WHERE length(words) = {2:d} "
                                 "RETURN code, words"
                                 .format(codeFormat if codeFormat else "Code", "', '".join(wordBag), len(wordBag)))

            # Record the codes with a description that contains all the words in the current bag of words.
            returnValue.append([j["code"] for j in result])

        # Close the session.
        session.close()

        return returnValue

    def get_descriptions(self, codes, codeFormats):
        """Get the descriptions of a list of codes.

        :param codes:       The codes to extract the descriptions for.
        :type codes:        list
        :param codeFormats: The code formats to look through when extracting descriptions.
        :type codeFormats:  list
        :return:            The descriptions of the input codes. Each input code is treated as a key in the returned
                                dictionary. The value associated with a code is a dictionary mapping the codeFormats
                                to the description of the code in that format. For example:
                                codes = ["A", "B", "C"]
                                codeFormats = ["ReadV2", "CTV3"]
                                return = {
                                            "A": {"ReadV2": "XXX"},
                                            "B": {"CTV3": "YYY"},
                                            "C": {"ReadV2": "ZZZ-0", "CTV3": "ZZZ-00"}
                                         }
                                Code A was only present in the Read v2 hierarchy, B in the CTV3 hierarchy and C in both.
        :rtype:             dict

        """

        # Get access to the database
        session = self._databaseController.generate_session()

        # Get the descriptions.
        descriptions = {i: {} for i in codes}
        for i in codeFormats:
            result = session.run("MATCH (c:{0:s}) "
                                 "WHERE c.code IN ['{1:s}'] "
                                 "RETURN c.code AS code, c.description AS description"
                                 .format(i, "', '".join(codes)))
            for j in result:
                descriptions[j["code"]][i] = j["description"]

        # Close the session.
        session.close()

        # Generate the return values.
        return descriptions
