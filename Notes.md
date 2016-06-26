positive and negative terms
	bag of words
	exact phrases

all will have to have whitespace around them for now

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