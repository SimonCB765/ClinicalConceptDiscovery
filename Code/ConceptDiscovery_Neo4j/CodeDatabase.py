"""Classes for creating and navigating a hierarchical code dictionary."""

# Python imports.
import logging
import os
import re

# 3rd party imports.
import neo4j.v1 as neo

# Globals.
LOGGER = logging.getLogger(__name__)


class CodeDatabase(object):
    """Class responsible for managing access to a clinical code hierarchy."""

    def __init__(self, databaseAddress, dbUser="neo4j", dbPass="root"):
        """Initialise the code database

        :param databaseAddress:     The address of the Neo4j database to use.
        :type databaseAddress:      str
        :param dbUser:              The username for the Neo4j database.
        :type dbUser:               str
        :param dbPass:              The password for the supplied username.
        :type dbPass:               str

        """
        self._databaseAddress = databaseAddress  # The address of the Neo4j database.
        self._dbUsername = dbUser  # The username to use when accessing the database.
        self._dbPassword = dbPass  # The password associated with the username.

    def instantiate_read_database(self, fileCodeMapping, dictType="readv2", delimiter='\t'):
        """Setup the Neo4j database from a Read code hierarchy.

        :param fileCodeMapping:     The location of the file containing the mapping of codes to their descriptions.
        :type fileCodeMapping:      str
        :param dictType:            The type of code dictionary to create.
        :type dictType:             str
        :param delimiter:           The delimiter between the code and its description in the file.
        :type delimiter:            str

        """

        # Compile the word splitting regular expression.
        wordFinder = re.compile("\s+")

        # Setup the temporary file needed to contain the processed code description input file.
        # One file will contain the codes, their descriptions and the individual words in their descriptions.
        # The other file will contain the hierarchy of parent/child relationships between codes.
        dirCodeMapping = os.path.dirname(fileCodeMapping)  # The directory containing the code to description mapping.
        fileCodesAndWords = os.path.join(dirCodeMapping, "{0:s}_codes".format(fileCodeMapping))
        fileHierarchy = os.path.join(dirCodeMapping, "{0:s}_hierarchy".format(fileCodeMapping))

        # Create the file of codes, descriptions and words in the descriptions.
        with open(fileCodeMapping, 'r') as fidCodeMapping, open(fileCodesAndWords, 'w') as fidCodesAndWords, \
                open(fileHierarchy, 'w') as fidHierarchy:
            # Create file headers.
            fidCodesAndWords.write("code\tlevel\tdescription\twords\n")
            fidHierarchy.write("parent\tchild\n")

            for line in fidCodeMapping:
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
                fidCodesAndWords.write("{0:s}\t{1:d}\t{2:s}\t{3:s}\n"
                                       .format(code, len(code), description, ';'.join(words)))
                if parent:
                    fidHierarchy.write("{0:s}\t{1:s}\n".format(parent, code))

        # Setup the database. Encryption is set False for local setups.
        driver = neo.GraphDatabase.driver(
            self._databaseAddress, auth=neo.basic_auth(self._dbUsername, self._dbPassword), encrypted=False)
        session = driver.session()

        # Create the codes, words and the relationships between codes and words.
        # Have to double brace {{ }} the node and edge parameters to account for the use of a formatted string.
        query = "LOAD CSV WITH HEADERS FROM 'file:/{0:s}' AS line FIELDTERMINATOR '\t' " \
                "WITH line, split(line.words, ';') AS words " \
                "LIMIT 10 " \
                "UNWIND words AS word " \
                "MERGE (c: Code {{code: line.code, description: line.description, level: toInt(line.level)}}) " \
                "MERGE (w: Word {{word: word}}) " \
                "MERGE (c) -[d: DescribedBy]-> (w) " \
                "RETURN line.code, word, c, w, d"\
            .format("{0:s}".format(fileCodesAndWords))
        res = session.run(query)
        for i in res:
            print(i)

        # Create the relationships between parent and child nodes.
        # Have to double brace {{ }} the node and edge parameters to account for the use of a formatted string.
        query = "LOAD CSV WITH HEADERS FROM 'file:/{0:s}' AS line FIELDTERMINATOR '\t' " \
                "LIMIT 10 " \
                "MERGE (c1: Code {{code: line.parent}}) -[p: Parent]-> (c2: Code {{code: line.child}}) " \
                "RETURN line.parent, line.child, c1, c2, p"\
            .format("{0:s}".format(fileHierarchy))
        query = "LOAD CSV WITH HEADERS FROM 'file:/{0:s}' AS line FIELDTERMINATOR '\t' " \
                "LIMIT 10 " \
                "MERGE (c1: Code {{code: line.parent}}) -[p: Parent]-> (c2: Code {{code: line.child}}) " \
                "RETURN line.parent, line.child, c1, c2, p"\
            .format("{0:s}".format(fileHierarchy))
        res = session.run(query)
        for i in res:
            print(i)

        session.close()

        # Remove the temporary files added.
        #os.remove(fileCodesAndWords)
        #os.remove(fileHierarchy)
