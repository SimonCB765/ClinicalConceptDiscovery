"""Class for managing access to a Neo4j database of clinical codes."""

# Python imports.
import logging

# 3rd party imports.
import neo4j.v1 as neo

# Globals.
LOGGER = logging.getLogger(__name__)


class DatabaseManager(object):
    """Class responsible for managing access to a Neo4j database containing the relationships between clinical codes."""

    def __init__(self, databaseAddress, dbUser="neo4j", dbPass="root", formatsSupported=("ReadV2")):
        """Initialise the database access parameters.

        :param databaseAddress:     The address of the Neo4j database to use.
        :type databaseAddress:      str
        :param dbUser:              The username for the Neo4j database.
        :type dbUser:               str
        :param dbPass:              The password for the supplied username.
        :type dbPass:               str
        :param formatsSupported:    The code formats supported by the database.
        :type formatsSupported:     list

        """
        self._databaseAddress = databaseAddress  # The address of the Neo4j database.
        self._dbUsername = dbUser  # The username to use when accessing the database.
        self._dbPassword = dbPass  # The password associated with the username.
        self._formatsSupported = formatsSupported  # The code formats supported.

    def generate_session(self):
        """Generate a session to access the database."""

        # Encryption is set to False for local setups.
        driver = neo.GraphDatabase.driver(self._databaseAddress,
                                          auth=neo.basic_auth(self._dbUsername, self._dbPassword),
                                          encrypted=False)
        return driver.session()

    def update(self, fileCodeDescriptions, fileHierarchy, delimiter='\t'):
        """Setup the Neo4j database from files of code definitions and relationships.

        :param fileCodeDescriptions:    The location of the file containing the descriptions of the codes.
        :type fileCodeDescriptions:     str
        :param fileHierarchy:           The location of the file containing the code hierarchy.
        :type fileHierarchy:            str
        :param delimiter:               The delimiter used in the files.
        :type delimiter:                str

        """

        # Setup the database. Encryption is set to False for local setups.
        driver = neo.GraphDatabase.driver(self._databaseAddress,
                                          auth=neo.basic_auth(self._dbUsername, self._dbPassword),
                                          encrypted=False)
        session = driver.session()

        # Create constraints and indices if the database is being created.
        dbExists = sum([i[0] for i in session.run("MATCH (:DBExists) RETURN 1")])
        if not dbExists:
            # Setup the constraints as a single transaction to ensure either all are setup or none are.
            transaction = session.begin_transaction()
            # Ensure each word is unique (and set up the index).
            transaction.run("CREATE CONSTRAINT ON (word:Word) ASSERT word.word IS UNIQUE")
            # Ensure each code is unique (within its given hierarchy) and index the descriptions as they're searched on
            # frequently. Codes are only guaranteed to be unique within a hierarchy, there may be overlap in code names
            # between hierarchies.
            for i in self._formatsSupported:
                transaction.run("CREATE CONSTRAINT ON (code:{0:s}) ASSERT code.code IS UNIQUE".format(i))
                transaction.run("CREATE INDEX ON :{0:s}(description)".format(i))
            # Add an index on the property indicating that a graph element is stale (i.e. not newly added or updated).
            transaction.run("CREATE INDEX ON :Code(stale)")
            transaction.run("CREATE INDEX ON :Word(stale)")
            transaction.run("CREATE INDEX ON :DescribedBy(stale)")
            transaction.run("CREATE INDEX ON :Parent(stale)")
            transaction.commit()

            # Add the dummy node indicating that the database has been created.
            session.run("CREATE (:DBExists)")

        # Create the codes, words and the relationships between codes and words.
        transactionSize = 500  # Number of lines to read before committing a transaction.
        linesAdded = 0  # Record of the number of lines used to construct this transaction.
        with open(fileCodeDescriptions, 'r') as fidCodeDescriptions:
            _ = fidCodeDescriptions.readline()  # Strip the header.
            transaction = session.begin_transaction()  # Start the first transaction.
            for line in fidCodeDescriptions:
                # Get the code and word information.
                code, codeFormat, level, description, words = (line.strip()).split(delimiter)

                if codeFormat in self._formatsSupported:
                    # Only add codes that are of the correct format.
                    # Properties have to be double braced {{ }} to account for the use of a formatted string.
                    transaction.run("MERGE (c:{0:s} {{code: \"{1:s}\"}}) "
                                    "SET c += {{stale: FALSE, descr_pretty: \"{2:s}\", descr_search: lower(\"{2:s}\"), "
                                        "level: toInt({3:s})}} "
                                    "WITH c "
                                    "UNWIND [\"{4:s}\"] as word "
                                    "MERGE (w:Word {{word: word}}) "
                                    "SET w.stale = FALSE "
                                    "CREATE UNIQUE (c) -[r:DescribedBy]-> (w) "
                                    "SET r.stale = FALSE"
                                    .format(codeFormat, code, description, level, '", "'.join(words.split(';'))))

                    linesAdded += 1
                    if linesAdded == transactionSize:
                        transaction.commit()
                        transaction = session.begin_transaction()  # Start the next transaction.

            transaction.commit()  # Commit the final transaction.

        # Remove all stale code and word nodes (along with their relationships).
        session.run("MATCH ()-[r:DescribedBy]->() WHERE r.stale DELETE r")
        for i in self._formatsSupported:
            session.run("MATCH (c:{0:s}) WHERE c.stale DELETE c".format(i))
        session.run("MATCH (w:Word) WHERE w.stale DELETE w")

        # Create the parent relationships between codes.
        transactionSize = 500  # Number of lines to read before committing a transaction.
        linesAdded = 0  # Record of the number of lines used to construct this transaction.
        with open(fileHierarchy, 'r') as fidHierarchy:
            _ = fidHierarchy.readline()  # Strip the header.
            transaction = session.begin_transaction()  # Start the first transaction.
            for line in fidHierarchy:
                # Get the code and word information.
                childCode, parentCode, codeFormat, relationship = (line.strip()).split(delimiter)

                # Create the statement to add this relationship.
                transaction.run("MATCH (child:{0:s} {{code: \"{1:s}\"}}) "
                                "MATCH (parent:{0:s} {{code: \"{2:s}\"}}) "
                                "CREATE UNIQUE (child) -[p:Parent {{relationship: \"{3:s}\"}}]-> (parent) "
                                "SET p.stale = FALSE"
                                .format(codeFormat, childCode, parentCode, relationship))

                linesAdded += 1
                if linesAdded == transactionSize:
                    transaction.commit()
                    transaction = session.begin_transaction()  # Start the next transaction.

            transaction.commit()  # Commit the final transaction.

        # Remove all stale parent relationships.
        session.run("MATCH ()-[r:Parent]->() WHERE r.stale DELETE r")

        # Mark all node and relationships remaining as stale.
        for i in self._formatsSupported:
            session.run("MATCH (c:{0:s}) SET c.stale = TRUE".format(i))
        session.run("MATCH (w:Word) SET w.stale = TRUE")
        session.run("MATCH ()-[r:DescribedBy]->() SET r.stale = TRUE")
        session.run("MATCH ()-[r:Parent]->() SET r.stale = TRUE")

        # Close the session.
        session.close()
