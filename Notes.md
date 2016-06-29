If a concept has some definition like
# RENAL
## POSITIVE
"chronic kidney disease"
renal
kidney
"glomerular filtration rate"
## NEGATIVE
"type 1" diabetes "type 2" diabs

then you can combine the quoted phrases that have no non-quoted words on their line (e.g. CKD and GFR here)
    (chronic kidney disease|glomerular filtration rate)
for a term with multiple quoted phrases you can combine its phrases to ensure all are in the description like:
    ^(?=.*type 1)(.*type 2)



constrain returned codes based on a code regex (so biomed measurements only come from chapter 4....)
    Could constrain negatively and positively based on the code hierarchy


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