"""Classes for storing, accessing and using concept defintions."""

# Python imports.
from collections import defaultdict
import logging
import os
import re

# Globals.
LOGGER = logging.getLogger(__name__)


class ConceptDefinition(object):
    """Class responsible for managing the concept definitions provided by the user.

    The concept definitions are represented in a dictionary with the following format:
    {
        "Concept1":
        {
            "Negative":
            {
                "Raw": ['"family history"', '"type 1"'],
                "Processed": [{"Quoted": {'(family history|type 1)'}, "BOW": set()}]
            }
            "Positive":
            {
                "Raw": ['blood pressure', '"type 2" diabetes'],
                "Processed": [
                              {"Quoted": set(), "BOW": {'blood', 'pressure'}},
                              {"Quoted": {'type 2'}, "BOW": {'diabetes'}}
                             ]
            }
        }
        ...
    }

    """

    _concepts = None  # The concepts recorded in the order that they appear in the concept definition file.
    _conceptDefinitions = None  # The dictionary of concepts.

    def __new__(cls, fileConceptDefinitions, conceptSource="FlatFile", delimiter='\t'):
        """Create a set of concept definitions.

        :param fileConceptDefinitions:  The location of the file containing the concept definitions.
        :type fileConceptDefinitions:   str
        :param conceptSource:           The type of concept definition source file. Valid values are (case insensitive):
                                            flatfile    - for the flat file input format
                                            json        - for the JSON input format
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
                # Didn't get one of the permissible
                raise ValueError("{0:s} is not a permissible value for conceptSource".format(str(conceptSource)))
        else:
            # An attempt is being made to create a ConceptDefinition subclass, so create the subclass.
            return super(ConceptDefinition, cls).__new__(cls, fileConceptDefinitions, conceptSource, delimiter)

    def _identify_codes(self, codeDictionary):
        """Extract the codes for the given concepts based on the terms used to define them.

        :param codeDictionary:  The code dictionary to use when searching for codes.
        :type codeDictionary:   CodeDictionary
        :return:                The positive and negative codes for each concept. Each key in the return value
                                    is the name of a user defined concept. Each key's corresponding value ia
                                    a dictionary of the form {"Positive": set(), "Negative": set()}, where the value
                                    for the "Positive" key is a set containing the positive codes for the concept, and
                                    the value for the "Negative" key is a set of the negative codes.
        :rtype:                 dict

        """

        conceptCodes = defaultdict(lambda: {"Positive": set(), "Negative": set()})
        for i in self._conceptDefinitions:
            # Go through each concept.
            for j in self._conceptDefinitions[i]:
                # Go through the negative and positive terms for the concept.
                processedTerms = self._conceptDefinitions[i][j]["Processed"]
                if processedTerms:
                    # There are terms of this type so get the negative/positive words and quoted terms for the concept.
                    words, quoted = zip(*[(list(k["BOW"]), k["Quoted"]) for k in processedTerms])

                    # For each term, get the codes with descriptions that contain all the unquoted words.
                    codesBOW = codeDictionary.get_codes_from_words(words)

                    # For each term, get the codes with descriptions that contain all the quoted phrases.
                    codesQuoted = codeDictionary.get_codes_from_regexp(quoted)

                    # For each term, find codes returned by the bag of words and quoted phrase search.
                    codes = set()
                    for k in range(len(words)):
                        if not words[k]:
                            # There are no bag of words entries for this concept, so the codes for the concept
                            # will be those found using the quoted phrases.
                            codes |= codesQuoted[k]
                        elif not quoted[k]:
                            # There are no quoted phrase entries for this concept, but there are bag of word entries, so
                            # the codes for the concept will be those found using the bag of words.
                            codes |= codesBOW[k]
                        else:
                            # There are both bag of words and quoted phrase for this concept, so the codes for the
                            # concept will be those codes found using both the bag of words and quoted phrases.
                            codes |= (codesBOW[k] & codesQuoted[k])
                    conceptCodes[i][j] = codes
                else:
                    # If there are no processed terms for this term type, then the concept has no term's of this type
                    # (likely negative terms).
                    conceptCodes[i][j] = set()

        return conceptCodes

    def identify_codes(self, codeDictionary, dirResults):
        """Extract the codes for the given concepts based on the terms used to define them.

        :param codeDictionary:  The code dictionary to use when searching for codes.
        :type codeDictionary:   CodeDictionary
        :param dirResults:      Location where the results of the code extraction should be saved.
        :type dirResults:       str

        """

        # Determine the negative and positive codes for the concepts.
        conceptCodes = self._identify_codes(codeDictionary)

        # Write out the concept codes and their descriptions.
        fileAllCodes = os.path.join(dirResults, "AllConceptCodes.txt")
        filePositiveCodes = os.path.join(dirResults, "PositiveConceptCodes.txt")
        with open(fileAllCodes, 'w') as fidAllCodes, open(filePositiveCodes, 'w') as fidPositiveCodes:
            for i in self._concepts:
                # Go through the concepts in the order they appear in the concept definition file.

                # Get the positive and negative codes (along with their descriptions) for this concept.
                posCodes = sorted(conceptCodes[i]["Positive"])
                posDescriptions = codeDictionary.get_descriptions(posCodes)
                negCodes = sorted(conceptCodes[i]["Negative"])
                negDescriptions = codeDictionary.get_descriptions(negCodes)

                # Write out the positive and negative codes for the concept.
                fidAllCodes.write("# {0:s}\n".format(i))
                fidAllCodes.write("## POSITIVE\n")
                fidAllCodes.write(''.join(
                    ["{0:s}\t{1:s}\n".format(posCodes[i], posDescriptions[i]) for i in range(len(posCodes))]))
                fidAllCodes.write("## NEGATIVE\n")
                fidAllCodes.write(''.join(
                    ["{0:s}\t{1:s}\n".format(negCodes[i], negDescriptions[i]) for i in range(len(negCodes))]))

                # Determine the final code list, positive minus negative.
                finalCodeList = [(j, k) for j, k in zip(posCodes, posDescriptions) if j not in negCodes]
                fidPositiveCodes.write("# {0:s}\n".format(i))
                for j in finalCodeList:
                    fidPositiveCodes.write("{0:s}\t{1:s}\n".format(j[0], j[1]))

    def identify_and_generalise_codes(self, codeDictionary, dirResults, searchLevel=1, childThreshold=0.2):
        """Extract generalised codes for the given concepts based on the terms used to define them.

        Codes returned for a concept by this method muse meet at least one of the following criteria:
            1) A term defining the concept must match the code's description.
            2) The code must be similar to a code where a term matches the description. Similar here means that a
                certain fraction of the code's children must meet one of these two criteria, or the code must be
                a descendant of a code meeting criterion 2.

        Generalised codes include both the codes where the concept term definitions match the code's description and
        those codes that can be generalised to from the descrip

        :param codeDictionary:  The code dictionary to use when searching for codes.
        :type codeDictionary:   CodeDictionary
        :param dirResults:      Location where the results of the code extraction should be saved.
        :type dirResults:       str
        :param searchLevel:     The level in the hierarchy where the search should stop. The search begins from the
                                    bottom/leaves of the hierarchy, and therefore a searchLevel of X means that only
                                    codes that occur at or below level X (i.e. their level is >= X) in the hierarchy
                                    can be added.
        :type searchLevel:      int
        :param childThreshold:  The fraction of child codes that must be positive before a parent code is marked as
                                    positive.
        :type childThreshold:   float

        """

        # Determine the negative and positive codes for the concepts.
        conceptCodes = self._identify_codes(codeDictionary)

        # Determine the newly found positive codes.
        generalisedCodes = {}
        for key, values in conceptCodes.items():
            # The initial set of codes to generalise from should be the non-negative codes for the concept.
            generalisedCodes[key] = codeDictionary.generalise_codes(values["Positive"] - values["Negative"],
                                                                    searchLevel, childThreshold)

        # Write out the concept codes and their descriptions.
        fileAllCodes = os.path.join(dirResults, "AllConceptCodes.txt")
        filePositiveCodes = os.path.join(dirResults, "PositiveConceptCodes.txt")
        fileGenAllCodes = os.path.join(dirResults, "AllConceptCodes_General.txt")
        fileGenPositiveCodes = os.path.join(dirResults, "PositiveConceptCodes_General.txt")
        with open(fileAllCodes, 'w') as fidAllCodes, open(filePositiveCodes, 'w') as fidPositiveCodes, \
                open(fileGenAllCodes, 'w') as fidGenAllCodes, open(fileGenPositiveCodes, 'w') as fidGenPositiveCodes:
            for i in self._concepts:
                # Go through the concepts in the order they appear in the concept definition file.

                # Get the positive and negative codes (along with their descriptions) for this concept.
                posCodes = sorted(conceptCodes[i]["Positive"])
                posDescriptions = codeDictionary.get_descriptions(posCodes)
                generalCodes = sorted(generalisedCodes[i] | conceptCodes[i]["Positive"])
                generalDescriptions = codeDictionary.get_descriptions(generalCodes)
                negCodes = sorted(conceptCodes[i]["Negative"])
                negDescriptions = codeDictionary.get_descriptions(negCodes)

                # Write out the positive and negative codes for the concept.
                fidAllCodes.write("# {0:s}\n".format(i))
                fidAllCodes.write("## POSITIVE\n")
                fidAllCodes.write(''.join(
                    ["{0:s}\t{1:s}\n".format(posCodes[i], posDescriptions[i]) for i in range(len(posCodes))]))
                fidAllCodes.write("## NEGATIVE\n")
                fidAllCodes.write(''.join(
                    ["{0:s}\t{1:s}\n".format(negCodes[i], negDescriptions[i]) for i in range(len(negCodes))]))

                # Determine the final code list, positive minus negative.
                finalCodeList = [(j, k) for j, k in zip(posCodes, posDescriptions) if j not in negCodes]
                fidPositiveCodes.write("# {0:s}\n".format(i))
                for j in finalCodeList:
                    fidPositiveCodes.write("{0:s}\t{1:s}\n".format(j[0], j[1]))

                # Write out the generalised positive codes and the negative codes for the concept.
                fidGenAllCodes.write("# {0:s}\n".format(i))
                fidGenAllCodes.write("## POSITIVE\n")
                for ind, j in enumerate(generalCodes):
                    if j in posCodes:
                        fidGenAllCodes.write("\t{0:s}\t{1:s}\n".format(j, generalDescriptions[ind]))
                    else:
                        fidGenAllCodes.write("*\t{0:s}\t{1:s}\n".format(j, generalDescriptions[ind]))
                fidGenAllCodes.write("## NEGATIVE\n")
                fidGenAllCodes.write(''.join(
                    ["\t{0:s}\t{1:s}\n".format(negCodes[i], negDescriptions[i]) for i in range(len(negCodes))]))

                # Determine the final code list, general positive codes minus negative codes.
                finalGenCodeList = [(j, k) for j, k in zip(generalCodes, generalDescriptions) if j not in negCodes]
                fidGenPositiveCodes.write("# {0:s}\n".format(i))
                for j in finalGenCodeList:
                    fidGenPositiveCodes.write("{0:s}\t{1:s}\n".format(j[0], j[1]))


class _FlatFileDefinitions(ConceptDefinition):
    """Create a set of concept definitions from a flat file input source."""

    def __init__(self, fileConceptDefinitions, conceptSource=None, delimiter=None):
        """Initialise the set of concept definitions from a flat file input source.

        Terms for a concept can be specified as negative or positive terms. If there is no header for a set of terms
        (i.e. it is not specified whether they are negative or positive), then the terms are assumed to be positive.

        The post processing will combine any terms that consist of solely quoted phrases (e.g. "type 1",
        "chronic kidney disease", "blood pressure") into one regular expression
        (e.g. (type 1|chronic kidney disease|blood pressure)). This will match any code description that contains
        one or more of these words.

        :param fileConceptDefinitions:  The location of the file containing the concept definitions.
        :type fileConceptDefinitions:   str
        :param conceptSource:           unused
        :type conceptSource:            N/A
        :param delimiter:               unused
        :type delimiter:                N/A

        """

        self._concepts = []  # The concepts recorded in the order that they appear in the concept definition file.

        # Define the dictionary to hold the processed concept definitions.
        self._conceptDefinitions = defaultdict(lambda: {"Positive": {"Raw": [], "Processed": []},
                                                        "Negative": {"Raw": [], "Processed": []}})

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
                    if currentConcept not in self._concepts:
                        # If the current concept is not in the list of concepts, then add it.
                        self._concepts.append(currentConcept)
                    currentTermType = "Positive"  # Reset the default term type back to positive.
                elif line.strip() == '':
                    # The line has no content on it.
                    pass
                else:
                    # Found a concept defining term.
                    rawTerm = line.strip()
                    rawTerm = re.sub("\s+", ' ', rawTerm)  # Turn consecutive whitespace into a single space.
                    quotedTerms = re.findall('".*?"', rawTerm)  # Find all quoted terms on the line.
                    quotedTerms = [i[1:-1] for i in quotedTerms]  # Strip the quotation marks off.
                    nonQuotedWords = re.sub('".*?"', '', rawTerm)  # Remove all quoted terms.
                    nonQuotedWords = nonQuotedWords.strip()  # Remove any whitespace that may be left over at the ends.
                    bagOfWordsTerms = []  # Initialise the bag of words to empty.
                    if nonQuotedWords:
                        # Only put anything in the bag of words list if the remainder of the line is non-empty.
                        bagOfWordsTerms = re.split("\s+", nonQuotedWords.strip())
                    termDefinition = {"Quoted": set(quotedTerms), "BOW": set(bagOfWordsTerms)}

                    self._conceptDefinitions[currentConcept][currentTermType]["Raw"].append(rawTerm)
                    self._conceptDefinitions[currentConcept][currentTermType]["Processed"].append(termDefinition)

        # Post process the concept definitions to simplify cases where there are terms that are only a single
        # quoted phrase.
        for i in self._conceptDefinitions:
            for j in self._conceptDefinitions[i]:
                # Determine whether there are any terms consisting of only a single quoted term.
                combinationTerms = []  # Terms involving unquoted words or multiple separate quoted phrases.
                singleQuotedTerms = set()  # Terms containing only a single quoted phrase and nothing else.
                for k in self._conceptDefinitions[i][j]["Processed"]:
                    if not k["BOW"]:
                        # Term only contains a single quoted phrase.
                        singleQuotedTerms |= (k["Quoted"])
                    else:
                        # Term contains some combination of unquoted words and/or multiple quoted phrases.
                        combinationTerms.append(k)

                if singleQuotedTerms:
                    # Combine all single quoted terms into one regular expression. For example, if the concept has
                    # terms like: "type 1", "chronic kidney disease" and "blood pressure", then these will be combined
                    # into the regular expression (type 1|chronic kidney disease|blood pressure). This works as a code
                    # belongs to the concept if the description contains any of these phrases.
                    singleQuotedTerms = "({0:s})".format("|".join(singleQuotedTerms))
                    combinationTerms.append({"Quoted": {singleQuotedTerms}, "BOW": set()})  # No bag of words needed.

                # Update the record of the terms for this concept.
                self._conceptDefinitions[i][j]["Processed"] = combinationTerms


class _JSONDefinitions(ConceptDefinition):
    pass