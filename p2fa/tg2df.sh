# tg2df
# Export TextGrid to data frame, i.e. to table in plaintext file, for further statistical analysis
# TextGrid object is produced by p2fa forced aligner
# tier 1 is phone
# tier 2 is word
# for each phone, create a row containing
# phone start time, phone end time, label, phone interval nr, word start time, word end time, word label, word interval nr
# 
# HQ 20110202, h.quene@uu.nl
#
# make sure that just one TextGrid object is selected
# and that it has 2 tiers (tier 1 named "phone" and tier 2 named "word")
# This script requires that a single TextGrid object is
# selected when the script is called. 
if ( numberOfSelected("TextGrid") != 1 ) 
	exit Exactly one TextGrid object must be selected.
	else
		# get name of selected TextGrid
		tg$ = selected$("TextGrid")
		nrtiers = Get number of tiers
		if ( nrtiers != 2 )
			exit TextGrid 'tg$' must have 2 tiers. 
		endif
		# names of tiers are not checked
endif

# get name of output directory
mydir$ = "~/Zandbak/"
fn$ = mydir$+tg$+".df.txt"
# !! delete file if it exists !! without warning
filedelete 'fn$'

# write column names
fileappend "'fn$'" textgrid nrph btph etph durph labph nrwd btwd etwd durwd labwd'newline$'

# get number of phones
nphones = Get number of intervals... 1
for i from 1 to nphones
	btph = Get start point... 1 'i'
	etph = Get end point... 1 'i'
	labph$ = Get label of interval... 1 'i'
	durph = etph-btph
	# if a phone straddles 2 words, take the word label at phone onset
	j = Get interval at time... 2 'btph'
	btwd = Get start point... 2 'j'
	etwd = Get end point... 2 'j'
	labwd$ = Get label of interval... 2 'j'
	durwd = etwd-btwd
	# write everything onto single line
	# printline 'tg$' 'i' 'btph:4' 'etph:4' 'durph:4' 'labph$' 'j' 'btwd:4' 'etwd:4' 'durwd:4' 'labwd$'
	fileappend "'fn$'" 'tg$' 'i' 'btph:4' 'etph:4' 'durph:4' 'labph$' 'j' 'btwd:4' 'etwd:4' 'durwd:4' 'labwd$''newline$'
endfor

printline Exported 'tg$' to 'fn$'