"""Code to initialise the concept discovery process."""

# Python imports.
import argparse
import datetime
import json
import logging
import os
import sys

# User imports.
if __package__ == "ConceptDiscovery":
    # If the package is ConceptDiscovery, then relative imports are needed.
    from . import CodeDictionary
    from . import ConceptDefinitions
else:
    # The code was not called from within the Code directory using 'python -m ConceptDiscovery'.
    # Therefore, we need to add the top level Code directory to the search path and use absolute imports.
    currentDir = os.path.dirname(os.path.join(os.getcwd(), __file__))  # Directory containing this file.
    codeDir = os.path.abspath(os.path.join(currentDir, os.pardir))
    sys.path.append(codeDir)
    from ConceptDiscovery import CodeDictionary
    from ConceptDiscovery import ConceptDefinitions
from Utilities import json_to_ascii

# Globals.
PYVERSION = sys.version_info[0]  # Determine major version number.
VALIDCONCEPTSRC = ["flatfile", "json"]  # The valid concept source file types.
VALIDDICTS = ["readv2", "snomed"]  # The valid code dictionary types accepted.


#------------------------#
# Create Argument Parser #
#------------------------#
parser = argparse.ArgumentParser(description="Extract codes corresponding to user-defined concept definitions.",
                                 epilog="For additional information on the parameters and the expected format and "
                                        "contents of the input and output files please see the README.")

# Mandatory arguments.
parser.add_argument("input", help="The location of the file containing the concept definitions.", type=str)

# Optional arguments.
parser.add_argument("-c", "--config",
                    help="The location of the configuration file to use. Default: default location.",
                    type=str)
parser.add_argument("-d", "--dictionary",
                    choices=VALIDDICTS,
                    default=VALIDDICTS[0],
                    help="The type of dictionary being used to construct the code hierarchy. Default: Read v2.",
                    type=str.lower)
parser.add_argument("-g", "--generalise",
                    action="store_true",
                    help="Whether generalised codes should be found. Default: do not generalise.")
parser.add_argument("-l", "--searchLevel",
                    default=1,
                    help="The level in the hierarchy where the generalisation search should stop. A smaller value "
                         "stops the search higher up the code hierarchy. Default: 1.",
                    type=int)
parser.add_argument("-o", "--output",
                    help="The location of the directory to write the output files to. Default: a timestamped "
                         "subdirectory in the Results directory.",
                    type=str)
parser.add_argument("-s", "--conceptSrc",
                    choices=VALIDCONCEPTSRC,
                    default=VALIDCONCEPTSRC[0],
                    help="The type of input file that contains the concept definitions. Default: flat file format.",
                    type=str.lower)
parser.add_argument("-t", "--childThreshold",
                    default=0.2,
                    help="The fraction of child codes that must be positive before a parent code is marked as "
                         "positive. Default: 0.2.",
                    type=float)
parser.add_argument("-w", "--overwrite",
                    action="store_true",
                    help="Whether the output directory should be overwritten if it exists. Default: do not overwrite.")

#------------------------------#
# Parse and Validate Arguments #
#------------------------------#
args = parser.parse_args()
dirTop = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)  # The directory containing all program files.
dirTop = os.path.abspath(dirTop)
errorsFound = []  # Container for any error messages generated during the validation.

# Validate the input file.
fileInput = args.input
if not os.path.isfile(fileInput):
    errorsFound.append("The input file location does not contain a file.")

# Validate the configuration file.
fileConfig = args.config
if fileConfig:
    # A configuration file was provided.
    if not os.path.isfile(fileConfig):
        errorsFound.append("The configuration file location does not contain a file.")
else:
    # Use the default configuration file.
    dirConfig = os.path.join(dirTop, "ConfigFiles")
    fileConfig = os.path.join(dirConfig, "ConceptDiscoveryConfig.json")

# Validate the output directory.
dirResults = os.path.join(dirTop, "Results")  # The default results directory.
dirDefaultOutput = os.path.join(dirResults,
                                "ConceptDiscovery_{0:s}".format(datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S")))
dirOutput = args.output if args.output else dirDefaultOutput
overwrite = args.overwrite
if overwrite:
    try:
        os.rmdir(dirOutput)
    except FileNotFoundError:
        # Can't remove the directory as it doesn't exist.
        pass
    except Exception as e:
        # Can't remove the directory for another reason.
        errorsFound.append("Could not overwrite the default output directory location - {0:s}".format(str(e)))
elif os.path.exists(dirOutput):
    errorsFound.append("The default output directory location already exists and overwriting is not enabled.")

# Display errors if any were found.
if errorsFound:
    print("\n\nThe following errors were encountered while parsing the input arguments:\n")
    print('\n'.join(errorsFound))
    sys.exit()

# Only create the output directory if there were no errors encountered.
try:
    os.makedirs(dirOutput, exist_ok=True)  # Attempt to make the output directory. Don't care if it already exists.
except Exception as e:
    print("\n\nThe following errors were encountered while parsing the input arguments:\n")
    print("The output directory could not be created - {0:s}".format(str(e)))
    sys.exit()

#------------------#
# Setup the Logger #
#------------------#
# Create the logger.
logger = logging.getLogger("ConceptDiscovery")
logger.setLevel(logging.DEBUG)

# Create the logger file handler.
fileLog = os.path.join(dirOutput, "ConceptDiscovery.log")
logFileHandler = logging.FileHandler(fileLog)
logFileHandler.setLevel(logging.DEBUG)

# Create a console handler for higher level logging.
logConsoleHandler = logging.StreamHandler()
logConsoleHandler.setLevel(logging.ERROR)

# Create formatter and add it to the handlers.
formatter = logging.Formatter("%(name)s\t%(levelname)s\t%(message)s")
logFileHandler.setFormatter(formatter)
logConsoleHandler.setFormatter(formatter)

# Add the handlers to the logger.
logger.addHandler(logFileHandler)
logger.addHandler(logConsoleHandler)

#---------------------------------------------#
# Parse and Validate Configuration Parameters #
#---------------------------------------------#
errorsFound = []

# Parse the JSON file of parameters.
readParams = open(fileConfig, 'r')
parsedArgs = json.load(readParams)
if PYVERSION == 2:
    parsedArgs = json_to_ascii.json_to_ascii(parsedArgs)  # Convert all unicode characters to ascii for Python < v3.
readParams.close()

# Check that the file containing the mapping from codes to descriptions is present.
fileCodeDescriptions = parsedArgs.get("CodeDescriptionFile", None)
if not fileCodeDescriptions:
    fileCodeDescriptions = os.path.join(dirTop, "Data", "Coding.tsv")
    if not os.path.isfile(fileCodeDescriptions):
        errorsFound.append("No config file was provided and the code description file is not in the default location "
                           "\"{0:s}\".".format(fileCodeDescriptions))
elif not os.path.isfile(fileCodeDescriptions):
    errorsFound.append("The file of code to description mappings in the configuration file does not exist.")

# Print error messages.
if errorsFound:
    print("\n\nThe following errors were encountered while parsing the input parameters:\n")
    print('\n'.join(errorsFound))
    sys.exit()

#-----------------------------#
# Perform the Code Extraction #
#-----------------------------#
logger.info("Creating the code dictionary.")
codeDictionary = CodeDictionary.CodeDictionary(fileCodeDescriptions, dictType=args.dictionary)

logger.info("Setting up the concept definitions.")
conceptDefinitions = ConceptDefinitions.ConceptDefinition(fileInput, conceptSource=args.conceptSrc)

if args.generalise:
    logger.info("Running generalised code identification.")
    if args.searchLevel < 1:
        logger.warning("The search level provided ({0:d}) is less than 1 and will be treated as if it was 1."
                       .format(args.searchLevel))
    if args.childThreshold < 0 or args.childThreshold > 1:
        message = "less than 0 and will be treated as if it was 0" if args.childThreshold < 0 else \
            "greater than 1 and will be treated as if it was 1"
        logger.warning("The child threshold provided ({0:.2f}) is {1:s}.".format(args.childThreshold, message))
    conceptDefinitions.identify_and_generalise_codes(codeDictionary, dirOutput, searchLevel=args.searchLevel,
                                                     childThreshold=args.childThreshold)
else:
    logger.info("Running code identification without generalisation.")
    conceptDefinitions.identify_codes(codeDictionary, dirOutput)
