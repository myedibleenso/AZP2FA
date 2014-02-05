forced-alignment
================

Tools for forced alignment. Fork of [**p2fa**](http://www.ling.upenn.edu/phonetics/p2fa/). 

<br>
What's here
-----------
1. [`create_transcripts.py`](https://github.com/myedibleenso/forced-alignment/blob/master/transcripts/create_transcripts.py)
	
	An original script for automatic generation of **htk**-compatible transcripts from some set of source sentences

2. [`pronunciator.py`](https://github.com/myedibleenso/forced-alignment/blob/master/pronunciation/pronunciator.py)
	
	Pronunciation estimator for unknown utterances (requires a pronunciation dictionary). &nbsp;A copy of the [CMU pronouncing dictionary](http://www.speech.cs.cmu.edu/cgi-bin/cmudict) is provided [here](https://github.com/myedibleenso/forced-alignment/blob/master/pronunciation/cmudict).  This script is able to generate .csv and LaTeX-formatted table of compositional statistics for a specified transcript or set of sentences (i.e. average length, \# syllables, syllables per word, unique phones, etc).<p>

4. [`align.py`](https://github.com/myedibleenso/forced-alignment/blob/master/p2fa/align.py) 

	Minimally modified **p2fa** that resolves deprecated SoX call<p>

5. [`align_batch.py`](https://github.com/myedibleenso/forced-alignment/blob/master/p2fa/align_batch.py)
	
	Script to batch process multiple wav files with minimally modified **p2fa**.

6. [`align_new.py`](https://github.com/myedibleenso/forced-alignment/blob/master/p2fa/align_new.py)

	Revised **p2fa** with several new features

7. [`splice.praat`](https://github.com/myedibleenso/forced-alignment/blob/master/scripts/splice.praat)

	Praat script for TextGrid-based slicing of wav files.  &nbsp;Credit and thanks given to [Jessamyn Schertz](http://www.u.arizona.edu/~jschertz/index.shtml)<p>
<br>  

Setup
-----
Install [**htk 3.4**](http://htk.eng.cam.ac.uk/). Careful about this point as v3.4.1 *will not work*.  

Mac users experiencing problems should look [here](http://speechtechie.wordpress.com/2009/06/12/compiling-htk-3-4-on-mac-os-10-5/).

<br>
Other stuff
-----------

File naming convention: 

`<GENDER><GENDER-ID>_HS_<NATIVE or NON-NATIVE (N or NN)>_<SPEED (NORM or FAST)>_<LIST>-<SENTENCE NUM (1-10)>`

MORE RECORDINGS:
http://www.voiptroubleshooter.com/open_speech/american.html
