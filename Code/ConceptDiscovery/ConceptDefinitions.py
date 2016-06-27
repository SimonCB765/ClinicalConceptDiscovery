"""Classes for storing, accessing and using concept defintions."""

# Python imports.
from collections import defaultdict
import logging
import re

# Globals.
LOGGER = logging.getLogger(__name__)


class ConceptDefinition(object):
    """Class responsible for managing the concept definitions provided by the user.

    The concept definitions are represented in a dictionary with the following format:
    {
        "Concept1": "Negative": [{"Raw": '"family history"', "Quoted": {"family history"}, "BOW": set()}]
                    "Positive": [{"Raw": 'blood pressure', "Quoted": set(), "BOW": {'blood', 'pressure'}},
                                 {"Raw": '"type 2" diabetes', "Quoted": {'"type 2"'}, "BOW": {'diabetes'}}
                                ]
        "Concept2": "Negative": [{"Raw": 'kidney "in clinic"', "Quoted": {'"in clinic"', "BOW": {'kidney'}}]
                    "Positive": [{"Raw": '"chronic kidney"', "Quoted": {'"chronic kidney"'}, "BOW": set()},
                                 {"Raw": 'kidney', "Quoted": set(), "BOW": {'kidney'}}
                                ]
        ...
    }

    """

    _conceptDefinitions = None  # The dictionary of concepts.

    def __new__(cls, fileConceptDefinitions, conceptSource="FlatFile", delimiter='\t'):
        """Create a set of concept definitions.

        :param fileConceptDefinitions:  The location of the file containing the concept definitions.
        :type fileConceptDefinitions:   str
        :param conceptSource:           The type of concept definition source file.
        :type conceptSource:            str
        :param delimiter:               The delimiter used in the concept definition file.
        :type delimiter:                str
        :return:                        A ConceptDefinition subclass determined by the conceptSource parameter.
        :rtype:                         ConceptDefinition subclass

        """

        if cls is ConceptDefinition:
            # An attempt is being made to create a ConceptDefinition, so determine which subclass to generate.
            if conceptSource.lower() == "flatfile":
                # Generate a _FlatFileDefinitions.
                return super(ConceptDefinition, cls).__new__(_FlatFileDefinitions)
            elif conceptSource.lower() == "json":
                # Generate a _JSONDefinitions.
                return super(ConceptDefinition, cls).__new__(_JSONDefinitions)
        else:
            # An attempt is being made to create a ConceptDefinition subclass, so create the subclass.
            return super(ConceptDefinition, cls).__new__(cls, fileConceptDefinitions, conceptSource, delimiter)


class _FlatFileDefinitions(ConceptDefinition):
    """Create a set of concept definitions from a flat file input source."""

    def __init__(self, fileConceptDefinitions, conceptSource=None, delimiter=None):
        """Initialise the set of concept definitions from a flat file input source.

        Terms for a concept can be specified as negative or positive terms. If there is not header for a set of terms
        (i.e. it is not specified whether they are negative or positive), then the terms are assumed to be positive.

        :param fileConceptDefinitions:  The location of the file containing the concept definitions.
        :type fileConceptDefinitions:   str
        :param conceptSource:           unused
        :type conceptSource:            N/A
        :param delimiter:               unused
        :type delimiter:                N/A

        """

        self._conceptDefinitions = defaultdict(lambda: {"Positive": [], "Negative": []})

        currentConcept = None  # The current concept having its terms extracted.
        currentTermType = "Positive"  # Whether the current terms being extracted are positive or negative terms.
        with open(fileConceptDefinitions, 'r') as fidConceptDefinitions:
            for line in fidConceptDefinitions:
                if line[:2] == "##":
                    # Found a header for the terms, so update whether the next terms are positive or negative.
                    if line[2:].strip().lower() == "positive":
                        currentTermType = "Positive"
                    elif line[2:].strip().lower() == "negative":
                        currentTermType = "Negative"
                    else:
                        LOGGER.warning("The term type definition \"{0:s}\" for concept {1:s} is specified "
                                       "incorrectly. The terms will still be treated as {2:s}."
                                       .format(line.strip(), currentConcept, currentTermType))
                elif line[0] == '#':
                    # Found the start of a new term.
                    currentConcept = re.sub("\s+", '_', line[1:].strip())  # Update the current concept.
                    currentTermType = "Positive"  # Reset the default term type back to positive.
                elif line.strip() == '':
                    # The line has no content on it.
                    pass
                else:
                    # Found a concept defining term.
                    rawTerm = line.strip()
                    line = re.sub("\s+", ' ', rawTerm)  # Turn consecutive whitespace into a single space.
                    quotedTerms = re.findall('".*?"', line)  # Find all quoted terms on the line.
                    line = re.sub('".*?"', '', line)  # Remove all quoted terms.
                    bagOfWordsTerms = []  # Initialise the bag of words to empty.
                    if line:
                        # Only put anything in the bag of words list if the remainder of the line is non-empty.
                        bagOfWordsTerms = re.split("\s+", line.strip())
                    termDefinition = {"Raw": rawTerm, "Quoted": set(quotedTerms), "BOW": set(bagOfWordsTerms)}

                    self._conceptDefinitions[currentConcept][currentTermType].append(termDefinition)


class _JSONDefinitions(ConceptDefinition):
    pass