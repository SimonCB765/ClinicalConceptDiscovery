"""Setup the Neo4j database."""

# 3rd party imports.
import neo4j.v1 as neo


def main(databaseAddress, fileCodeDescriptions, fileHierarchy, dbUsername="neo4j", dbPassword="root", delimiter='\t'):
    """Setup the Neo4j database from a Read code hierarchy.

    :param databaseAddress:         The address of the Neo4j database to use.
    :type databaseAddress:          str
    :param fileCodeDescriptions:    The location of the file containing the descriptions of the codes.
    :type fileCodeDescriptions:     str
    :param fileHierarchy:           The location of the file containing the code hierarchy.
    :type fileHierarchy:            str
    :param dbUsername:              The username for the Neo4j database.
    :type dbUsername:               str
    :param dbPassword:              The password for the supplied username.
    :type dbPassword:               str
    :param delimiter:               The delimiter used in the files.
    :type delimiter:                str

    """

    # Setup the database. Encryption is set to False for local setups.
    driver = neo.GraphDatabase.driver(databaseAddress, auth=neo.basic_auth(dbUsername, dbPassword), encrypted=False)
    session = driver.session()

    # Create constraints and indices if the database is being created.
    nodeNumber = sum([i[0] for i in session.run("MATCH () RETURN count(*)")])
    if not nodeNumber:
        # There are no nodes in the database, so assume it is being created.
        session.run("CREATE CONSTRAINT ON (word:Word) ASSERT word.word IS UNIQUE")  # Each word must be unique.
        session.run("CREATE INDEX ON :Word(word)")  # Index words to speed up looking up words.
        session.run("CREATE INDEX ON :Code(code)")  # Index codes to speed up looking up codes by name.

    #TODO Set label for the type of the code from the value in the file.
    #TODO http://stackoverflow.com/questions/24992977/neo4j-cypher-creating-nodes-and-setting-labels-with-load-csv
    #TODO http://stackoverflow.com/questions/29419634/set-label-based-on-data-within-load-csv?noredirect=1&lq=1

    # Create the codes, words and the relationships between codes and words.
    # Have to double brace {{ }} the node and edge parameters to account for the use of a formatted string.
    query = ("USING PERIODIC COMMIT 500 "
             "LOAD CSV WITH HEADERS FROM 'file:/{0:s}' AS line FIELDTERMINATOR '\t' "
             "WITH line, split(line.words, ';') AS words "
             "LIMIT 10 "
             "UNWIND words AS word "
             "MERGE (c:Code:line.format {{code: line.code, description: line.description, level: toInt(line.level)}}) "
             "MERGE (w:Word {{word: word}}) "
             "MERGE (c) -[d: DescribedBy]-> (w)"
             ).format(fileCodeDescriptions)
    session.run(query)

    #TODO There are now (potentially) multiple labels for reach relationship, alter it so this works

    # Create the relationships between parent and child nodes.
    # Have to double brace {{ }} the node and edge parameters to account for the use of a formatted string.
    query = ("USING PERIODIC COMMIT 500 "
             "LOAD CSV WITH HEADERS FROM 'file:/{0:s}' AS line FIELDTERMINATOR '\t' "
             "WITH line "
             "LIMIT 10 "
             "MERGE (:Code {{code: line.parent}}) -[:Parent]-> (:Code {{code: line.child}})"
             ).format(fileHierarchy)
    session.run(query)

    # Close the session.
    session.close()

    # Remove the temporary files added.
    #os.remove(fileCodesAndWords)
    #os.remove(fileHierarchy)


def instantiate_snomed_database():
    pass
