# ClinicalConceptDiscovery

## Usage

Python 3 is required to run the method described here. If on Windows and Python 3 is the default interpreter, then you can use the command `python` to run the code. If on Linux, then `python3` is likely to be the required command. In order to run the code to extract the patient data:

1. Acquire the code by cloning this repository into the directory `/path/to/ClinicalConceptDiscovery`.
2. Run the concept discovery. Run the command `python /path/to/ClinicalConceptDiscovery/Code/ConceptDiscovery /path/to/ConceptDefs`, where `/path/to/ConceptDefs` is the location of the file containing the concept definitions in the format described below.
    - This will generate results in the default location, which is a timestamped subdirectory in the `/path/to/ClinicalConceptDiscovery/Results` directory.

Further information on the command line arguments accepted by the `ConceptDiscovery` method can be found in its help information (using the `-h` or `--help` flags) and in the ConceptDiscovery section below.

## ConceptDiscovery

This is performed using the runnable package `ConceptDiscovery`. This takes a set of concept definitions and the clinical codes (along with their descriptions) that are to be searched and returns for each concepts a set of codes that should be used to define it. Concepts are defined by a set of terms, with each term containing a set of keywords. Terms are matched against the descriptions of clinical codes in order to determine which codes can be used to define a concept.

The file of concept definitions should contain one or more definitions. A single concept definitions can contain:

- The concept identifier.
- The term type. This is used to indicate whether terms should be used to include or exclude codes from defining the concept.
- The terms used to define the concept.

An example of a concept definition is:

    # CKD-Diagnosis
    ## positive
    chronic renal
    renal failure
    chronic kidney
    CKD
    ## negative
    "no evidence of"
    "family history"
    "no evidence of"
    FH: kidney
    kidney donation
    kidney recipient

The specification for each of the three elements is:

- Concepts identifiers
    - A line starting with a `#` character as the first character on the line.
    - If a concept identifier appears twice in the file, then the two definitions are combined.
- Term type
    - A line starting with `##` as the first two characters on the line.
    - Contains either `positive` or `negative` following the `##`.
    - If a concept definition contains no term type lines, then all terms are deemed to be positive.
- Terms
    - A term is a collection of all keywords appearing on a line within the concept definition (i.e. `chronic renal` and `FH: kidney` above).
    - Within a concept, a code need only satisfy one positive term to be included in the concept definition or one negative term to be excluded.
    - Two types of keywords are permitted within terms:
        - Quoted terms are treated as regular expressions. They are matched within a code's description using a regular expression engine, and can therefore include things such as wildcards (e.g. `"kidney.*injury"` will match any code where its description contains the word kidney followed at some point by the work injury).
        - Unquoted terms are treated as single words and matched in a bag of words fashion. Therefore, the term `chronic renal` above means that for a code to be deemed to define the concept according to the term, the code's description must contain both the words chronic and renal in any order.
    - The two types of keywords can be combined. For example, the term `"type 1" diabetes` will match any code where its description contains the word `diabetes` and the phrase `type 1` in any order.

In addition to the file of concept definitions, the concept discovery requires a description of the clinical code hierarchy that is to be searched. This file is formatted as a tsv file with two columns, with the code in the first and its description in the second. An example of a small section of this file is:

    K05	Chronic renal failure
    K050	End stage renal failure
    K051	Chronic kidney disease stage 1
    K052	Chronic kidney disease stage 2
    K053	Chronic kidney disease stage 3
    K054	Chronic kidney disease stage 4
    K055	Chronic kidney disease stage 5
    K06	Renal failure unspecified
    K060	Renal impairment
    K07	Renal sclerosis unspecified

This file is included with the repository as the `Coding.tsv` file in the `/path/to/ClinicalConceptDiscovery/Data` directory.