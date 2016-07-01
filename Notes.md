constrain returned codes based on a code regex (so biomed measurements only come from chapter 4....)
    Could constrain negatively and positively based on the code hierarchy


python 3 is necessary due to the exists_ok keyword in the os.makedirs


python ../ConceptDiscovery inputFile
    can be used to call the code from anywhere

if the same concept is defined multiple times the terms will just keep being added to the record of the concept

positive and negative terms
	bag of words
	exact phrases

all will have to have whitespace around them for now

each line is ORed together

difficulty with using regexps in the terms is that some of the code descriptions have regexp characters in them
    maybe could put regexps in the terms between back slashes (e.g. \.*\)
    
    
Flat File
    If you have a term before positive or negative is declared for the concept, then the term is assumed ot be positive, e.g.
    # CONCPET
    term1
    term2
    ## POSITIVE
    term3
    ## NEGATIVE
    term4
    
   terms 1, 2 and 3 are positive and term 4 negative




bag of words should treat phrases in the correct order more highly than those where the words are jumbled...

if you search with stop words, then give preference to similar thength terms e.g.
query - view from the window
gives preference to view and window being separated by two words

http://www.googleguide.com/interpreting_queries.html




Currently no stemming, stop word removal, punctuation removal, etc.


Strip Punctuation
http://stackoverflow.com/questions/265960/best-way-to-strip-punctuation-from-a-string-in-python
{';', '-', "'", ',', '<', ']', '"', '+', '!', '?', '.', ')', '%', '^', '=', '_', '*', '>', '(', '[', '&', '/', '#', ':'}


stop words
I 
a 
about 
an 
are 
as 
at 
be 
by 
for 
from
how
in 
is 
it 
of 
on 
or 
that
the 
this
to 
was 
what 
when
where
who 
will 
with
the