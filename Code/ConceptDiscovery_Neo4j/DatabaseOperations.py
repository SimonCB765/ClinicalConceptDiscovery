"""Class for managing access to a Neo4j database of clinical codes."""

# Python imports.
import logging

# 3rd party imports.
import neo4j.v1 as neo

# Globals.
LOGGER = logging.getLogger(__name__)


class DatabaseOperations(object):
    """Class responsible for managing access to a Neo4j database containing the relationships between clinical codes."""

    def __init__(self, databaseAddress, dbUser="neo4j", dbPass="root"):
        """Initialise the database access parameters.

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

    def get_descriptions(self, codes, codeFormat=None):
        """Get the descriptions of a list of codes.

        Any supplied code that is not in the hierarchy will be ignored.

        :param codes:       The codes to extract the descriptions for.
        :type codes:        list
        :param codeFormat:  The code format to look through when extracting descriptions
        :type codeFormat:   str
        :return:            The descriptions of the input codes.
        :rtype:             list

        """

        # Setup the database. Encryption is set to False for local setups.
        driver = neo.GraphDatabase.driver(self._databaseAddress,
                                          auth=neo.basic_auth(self._dbUsername, self._dbPassword),
                                          encrypted=False)
        session = driver.session()

        # Get the descriptions.
        result = session.run("MATCH (c:{0:s}) "
                             "WHERE c.code IN ['{1:s}'] "
                             "RETURN c.code AS code, c.description AS description"
                             .format(codeFormat if codeFormat else "Code", "', '".join(codes)))

        # Close the session.
        session.close()

        # Generate the return values.
        descriptions = {i["code"]: i["description"] for i in result}
        return [descriptions[i] for i in codes]

    def update_database(self, fileCodeDescriptions, fileHierarchy, delimiter='\t'):
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
        # The only constraint needed is that words must be unique. Codes don't have to be unique as there may be some
        # overlap between code names in different hierarchies.
        # Indices need to be created on :Code.code and :Code.description as these are searched on frequently. And index
        # does not need to be created on :Word.word as this is created automatically by the addition of the unique
        # constraint.
        # The code format property is also indexed, however format properties are transient and this index will have
        # minimal impact outside of node creation.
        dbExists = sum([i[0] for i in session.run("MATCH (:DBExists) RETURN 1")])
        if not dbExists:
            session.run("CREATE (:DBExists)")  # Add the dummy node indicating that the database has been created.
            session.run("CREATE CONSTRAINT ON (word:Word) ASSERT word.word IS UNIQUE")  # Each word must be unique.
            session.run("CREATE INDEX ON :Code(code)")  # Index code names.
            session.run("CREATE INDEX ON :Code(description)")  # Index code descriptions.
            session.run("CREATE INDEX ON :Code(format)")  # Index the code formats.

        # Create the codes, words and the relationships between codes and words.
        # Have to double brace {{ }} the node and edge parameters to account for the use of a formatted string.
        # The Code.format property is set outside the MERGE in order to ensure that the merge does not try and match it.
        # This would fail as the format gets removed later, and therefore the merge would create a duplicate node.
        query = ("USING PERIODIC COMMIT 500 "
                 "LOAD CSV WITH HEADERS FROM 'file:/{0:s}' AS line FIELDTERMINATOR '\t' "
                 "WITH line, split(line.words, ';') AS words "
                 "LIMIT 25 "
                 "UNWIND words AS word "
                 "MERGE (c:Code {{code: line.code, description: line.description, level: toInt(line.level)}}) "
                 "ON CREATE SET c.format = line.format "
                 "MERGE (w:Word {{word: word}}) "
                 "MERGE (c) -[d:DescribedBy]-> (w)"
                 ).format(fileCodeDescriptions)
        session.run(query)

        # Update the format labels on the newly added codes. As the format property is removed once the labels are
        # updated, this will only match those codes that are newly added.
        session.run("MATCH (c:Code {format: 'ReadV2'}) "
                    "SET c:ReadV2 "
                    "REMOVE c.format")
        session.run("MATCH (c:Code {format: 'CTV3'}) "
                    "SET c:CTV3 "
                    "REMOVE c.format")
        session.run("MATCH (c:Code {format: 'SNOMED'}) "
                    "SET c:SNOMED "
                    "REMOVE c.format")

        # Create the relationships between parent and child nodes.
        # Have to double brace {{ }} the node and edge parameters to account for the use of a formatted string.
        query = ("USING PERIODIC COMMIT 500 "
                 "LOAD CSV WITH HEADERS FROM 'file:/{0:s}' AS line FIELDTERMINATOR '\t' "
                 "WITH line, split(line.relationships, ';') AS relationships "
                 "LIMIT 25 "
                 "MATCH (child:Code {{code: line.child }}) "
                 "MATCH (parent:Code {{code: line.parent }}) "
                 "CREATE (child) -[p:Parent {{relationships: relationships}}]-> (parent)"
                 ).format(fileHierarchy)
        session.run(query)

        # Close the session.
        session.close()
