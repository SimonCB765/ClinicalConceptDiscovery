"""Code to turn Read and SNOMED code-description mappings into ones suitable for Neo4j."""

# Python imports.
import re


def main(fileReadV2, fileCTV3=None, fileSNOMED=None, fileCodeDescriptions=None, fileHierarchy=None):
    """Convert mappings between codes and descriptions into the mappings needed to construct nodes and relationships.

    All parent codes will be related to their child codes using the relationship 'Parent' in addition to any more
    specific terms (e.g. has_a, is_a). All Read V2 codes are deemed to have an is_a relationship with their parent.

    :param fileReadV2:              A mapping from Read v2 codes to their descriptions. Each line should be formatted
                                        to contain two values separated by a tab. The first value should be the code,
                                        and the second the code's description (which may not contain tabs).
    :type fileReadV2:               str
    :param fileCTV3:
    :type fileCTV3:                 str
    :param fileSNOMED:
    :type fileSNOMED:               str
    :param fileCodeDescriptions:    The location of the tsv file where the descriptions of the codes will be saved.
    :type fileCodeDescriptions:     str
    :param fileHierarchy:           The location of the tsv file where the code hierarchy will be saved.
    :type fileHierarchy:            str

    """

    delimiter = '\t'  # Record the delimiter to use.

    # Compile the word splitting regular expression.
    wordFinder = re.compile("\s+")

    # Create the files needed by Neo4j.
    #with open(fileReadV2, 'r') as fidReadV2, open(fileCTV3, 'r') as fidCTV3, open(fileSNOMED, 'r') as fidSNOMED, \
    with open(fileReadV2, 'r') as fidReadV2, \
            open(fileCodeDescriptions, 'w') as fidCodeDescriptions, open(fileHierarchy, 'w') as fidHierarchy:
        # Create file headers.
        fidCodeDescriptions.write("code\tformat\tlevel\tdescription\twords\n")
        fidHierarchy.write("child\tparent\trelationships\n")

        # Add the Read v2 codes to the output files.
        for line in fidReadV2:
            code, description = (line.strip()).split(delimiter)
            description = description.lower()

            parent = ''
            if len(code) > 1:
                # If the code consists of at least 2 characters, then the code has a parent.
                parent = code[:-1]

            # Some descriptions start with something like [V]XXX. In order to match XXX as a real word, a space
            # must be inserted between [V] and XXX.
            description = re.sub("^\[[a-zA-Z]+\]", "\g<0> ", description)

            # Split the description into words.
            words = wordFinder.split(description)

            # Write out the information about the code.
            fidCodeDescriptions.write("{0:s}\tReadV2\t{1:d}\t{2:s}\t{3:s}\n"
                                      .format(code, len(code), description, ';'.join(words)))
            if parent:
                # All Read V2 codes are deemed to have an is_a relationship with their parent.
                fidHierarchy.write("{0:s}\t{1:s}\tis_a\n".format(code, parent))
