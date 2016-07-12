"""Classes for creating and navigating a hierarchical code dictionary."""

# Python imports.
import logging

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
