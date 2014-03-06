#!/usr/bin/env python

""" Command-line usage:
	  python align.py [options] wave_file transcript_file output_file
	  where options may include:
		-r sampling_rate -- override which sample rate model to use, one of 8000, 11025, and 16000
		-s start_time    -- start of portion of wavfile to align (in seconds, default 0)
		-e end_time      -- end of portion of wavfile to align (in seconds, defaul to end)
			
	You can also import this file as a module and use the functions directly.
"""
from random import randint
import subprocess as sp
import shlex
import os
import sys
import getopt
import wave
import re
import tempfile
import subprocess as sp
import shutil

rand_prefix = str(randint(1,10000))
tmp_dir = os.path.join(os.getcwd(), rand_prefix+'tmp')

tmpwav = os.path.join(tmp_dir, "sound.wav")
codetr_scp = os.path.join(tmp_dir, "codetr.scp")
tmp_plp = os.path.join(tmp_dir, "tmp.plp")
test_scp = os.path.join(tmp_dir, "test.scp")
results = os.path.join(tmp_dir, "aligned.results")

mpfile = os.path.join(os.getcwd(), "model", "monophones")
word_dictionary = os.path.join(tmp_dir, "dict")	
input_mlf = os.path.join(tmp_dir, "tmp.mlf")
output_mlf = os.path.join(tmp_dir, "aligned.mlf")

#define hmmdir
hmmdir = os.path.join(os.getcwd(), "model", str(11025))
hmm_macros = os.path.join(hmmdir, "macros")
hmm_defs = os.path.join(hmmdir, "hmmdefs")

#better to pass this in?
log_file = os.path.expanduser("~/websites/poop/uploads/debug2_log")

def logger(message, log_file=log_file):
	"""
	logger
	"""
	with open(log_file, 'a') as lg:
		lg.write("{0}\n".format(message))

def prep_wav(orig_wav, out_wav, sr_override, wave_start, wave_end):
	global sr_models
	
	if os.path.exists(out_wav) and False :
		f = wave.open(out_wav, 'r')
		SR = f.getframerate()
		f.close()
		print "Already re-sampled the wav file to " + str(SR)
		return SR

	f = wave.open(orig_wav, 'r')
	SR = f.getframerate()
	f.close()
	
	soxopts = ""
	if float(wave_start) != 0.0 or wave_end != None :
		soxopts += " trim " + wave_start
		if wave_end != None :
			soxopts += " " + str(float(wave_end)-float(wave_start))

	if (sr_models != None and SR not in sr_models) or (sr_override != None and SR != sr_override) or soxopts != "":
		new_sr = 11025
		if sr_override != None :
			new_sr = sr_override
		
		sox_msg = "Resampling wav file from " + str(SR) + " to " + str(new_sr) + soxopts + "..."
		logger(sox_msg)
		SR = new_sr
		sox_command = shlex.split("sox {orig_wav} -r {SR} {out_wav} {options}".format(orig_wav=orig_wav, SR=SR, out_wav=out_wav, options=soxopts))
		logger("SoX command: {cmd}".format(cmd=' '.join(sox_command)))
		o, e = sp.Popen(sox_command, stdout=sp.PIPE, stderr=sp.PIPE).communicate()
		if o:
			logger("SoX out: {output}".format(output=o))
		if e:
			logger("SoX error: {error}".format(error=e))

		#os.system("sox " + orig_wav + " -r " + str(SR) + " " + out_wav + soxopts)
	else:
		#print "Using wav file, already at sampling rate " + str(SR) + "."
		os.system("cp -f " + orig_wav + " " + out_wav)

	return SR


def prep_mlf(trsfile, mlffile, word_dictionary, surround, between):
	# Read in the dictionary to ensure all of the words
	# we put in the MLF file are in the dictionary. Words
	# that are not are skipped with a warning.
	f = open(word_dictionary, 'r')
	dict = { } # build hash table
	for line in f.readlines():
		if line != "\n" and line != "" :
			dict[line.split()[0]] = True
	f.close()
	
	f = open(trsfile, 'r')
	lines = f.readlines()
	f.close()

	words = []

	if surround != None:
		words += surround.split(',')

	i = 0

	# this pattern matches hyphenated words, such as TWENTY-TWO; however, it doesn't work with longer things like SOMETHING-OR-OTHER
	hyphenPat = re.compile(r'([A-Z]+)-([A-Z]+)')

	while (i < len(lines)):
		txt = lines[i].replace('\n', '')
		txt = txt.replace('{breath}', '{BR}').replace('&lt;noise&gt;', '{NS}')
		txt = txt.replace('{laugh}', '{LG}').replace('{laughter}', '{LG}')
		txt = txt.replace('{cough}', '{CG}').replace('{lipsmack}', '{LS}')

		for pun in [',', '.', ':', ';', '!', '?', '"', '%', '(', ')', '--', '---']:
			txt = txt.replace(pun,  '')

		txt = txt.upper()

		# break up any hyphenated words into two separate words
		txt = re.sub(hyphenPat, r'\1 \2', txt)

		txt = txt.split()

		for wrd in txt:
			if (wrd in dict):
				words.append(wrd)
				if between != None:
					words.append(between)
			else:
				skip_msg = "SKIPPING WORD: {0}".format(wrd)
				logger(skip_msg)

		i += 1

	# remove the last 'between' token from the end
	if between != None:
		words.pop()

	if surround != None:
		words += surround.split(',')
	
	writeInputMLF(mlffile, words)
	
def writeInputMLF(mlffile, words) :
	fw = open(mlffile, 'w')
	fw.write('#!MLF!#\n')
	lab_loc = '"*/tmp.lab"\n' #quotes are important and the absolute path simply does not work here (go figure)
	logger("mlf line about .lab file: {0}".format(lab_loc))
	fw.write(lab_loc)
	#fw.write('"*/tmp.lab"\n')
	for wrd in words:
		fw.write(wrd + '\n')
	fw.write('.\n')
	fw.close()


def readAlignedMLF(mlffile, SR, wave_start):
	# This reads a MLFalignment output  file with phone and word
	# alignments and returns a list of words, each word is a list containing
	# the word label followed by the phones, each phone is a tuple
	# (phone, start_time, end_time) with times in seconds.
	logger("Reading {0}...".format(mlffile))
	f = open(mlffile, 'r')
	lines = [l.rstrip() for l in f.readlines()]
	f.close()
	
	if len(lines) < 3:
		error_msg = "Alignment did not complete succesfully."
		logger(error_msg)
		raise ValueError(error_msg)
			
	j = 2
	ret = []
	while (lines[j] <> '.'):
		if (len(lines[j].split()) == 5): # Is this the start of a word; do we have a word label?
			# Make a new word list in ret and put the word label at the beginning
			wrd = lines[j].split()[4]
			ret.append([wrd])
		
		# Append this phone to the latest word (sub-)list
		ph = lines[j].split()[2]
		if (SR == 11025):
			st = (float(lines[j].split()[0])/10000000.0 + 0.0125)*(11000.0/11025.0)
			en = (float(lines[j].split()[1])/10000000.0 + 0.0125)*(11000.0/11025.0)
		else:
			st = float(lines[j].split()[0])/10000000.0 + 0.0125
			en = float(lines[j].split()[1])/10000000.0 + 0.0125   
		if st < en:
			ret[-1].append([ph, st+wave_start, en+wave_start])
		
		j += 1
		
	return ret

def writeTextGrid(outfile, word_alignments) :
	# make the list of just phone alignments
	phons = []
	for wrd in word_alignments :
		phons.extend(wrd[1:]) # skip the word label
		
	# make the list of just word alignments
	# we're getting elements of the form:
	#   ["word label", ["phone1", start, end], ["phone2", start, end], ...]
	wrds = []
	for wrd in word_alignments :
		# If no phones make up this word, then it was an optional word
		# like a pause that wasn't actually realized.
		if len(wrd) == 1 :
			continue
		wrds.append([wrd[0], wrd[1][1], wrd[-1][2]]) # word label, first phone start time, last phone end time
	
	#write the phone interval tier
	fw = open(outfile, 'w')
	fw.write('File type = "ooTextFile short"\n')
	fw.write('"TextGrid"\n')
	fw.write('\n')
	fw.write(str(phons[0][1]) + '\n')
	fw.write(str(phons[-1][2]) + '\n')
	fw.write('<exists>\n')
	fw.write('2\n')
	fw.write('"IntervalTier"\n')
	fw.write('"phone"\n')
	fw.write(str(phons[0][1]) + '\n')
	fw.write(str(phons[-1][-1]) + '\n')
	fw.write(str(len(phons)) + '\n')
	for k in range(len(phons)):
		fw.write(str(phons[k][1]) + '\n')
		fw.write(str(phons[k][2]) + '\n')
		fw.write('"' + phons[k][0] + '"' + '\n')
	
	#write the word interval tier
	fw.write('"IntervalTier"\n')
	fw.write('"word"\n')
	fw.write(str(phons[0][1]) + '\n')
	fw.write(str(phons[-1][-1]) + '\n')
	fw.write(str(len(wrds)) + '\n')
	for k in range(len(wrds) - 1):
		fw.write(str(wrds[k][1]) + '\n')
		fw.write(str(wrds[k+1][1]) + '\n')
		fw.write('"' + wrds[k][0] + '"' + '\n')
	
	fw.write(str(wrds[-1][1]) + '\n')
	fw.write(str(phons[-1][2]) + '\n')
	fw.write('"' + wrds[-1][0] + '"' + '\n')               
	
	fw.close()

def prep_working_directory():
	#make a tmp directory with a unique identifier
	#use shutil
	#pass in dir?
	if os.path.exists(tmp_dir):
		shutil.rmtree(tmp_dir)
	os.makedirs(tmp_dir)
	if os.path.exists(tmp_dir):
		logger("Successfully created {0}\n".format(tmp_dir))
	else:
		logger("Failed to create {0}".format(tmp_dir))
		logger("Exiting...")
		shutil.rmtree(tmp_dir)
		sys.exit(0)


	#os.system("rm -r -f ./tmp")
	#os.system("mkdir ./tmp")

def delete_working_directory():
	#delete working directory
	#pass in dir?
	pass

def prep_scp(wavfile):
	#try changing these to save to working directory
	fw = open(codetr_scp, 'w')
	#fw = open('./tmp/codetr.scp', 'w')
	fw.write(wavfile + ' '+tmp_plp+"\n")
	#fw.write(wavfile + ' ./tmp/tmp.plp\n')
	fw.close()
	fw = open(test_scp, 'w')
	#fw = open('./tmp/test.scp', 'w')
	fw.write(tmp_plp+"\n")
	#fw.write('./tmp/tmp.plp\n')
	fw.close()

def create_plp(hcopy_config):
	#step 1: change to save to working directory
	#step 2: use sp.Popen instead
	logger("Creating plp file with HCopy...")
	hcopy_command = shlex.split('HCopy -T 1 -C {config} -S {codetr}'.format(config=hcopy_config, codetr=codetr_scp))
	logger("HCopy command: {0}".format(' '.join(hcopy_command)))
	o, e = sp.Popen(hcopy_command, stdout=sp.PIPE, stderr=sp.PIPE).communicate() 
	if o:
		logger("HCopy out: {output}".format(output=o))
	if e:
		logger("HCopy error: {error}".format(error=e))
	if os.path.exists(tmp_plp):
		logger("plp created!\n")
	else:
		logger("error creating plp file")

	#os.system('HCopy -T 1 -C ' + hcopy_config + ' -S ./tmp/codetr.scp')
	
def viterbi(input_mlf, word_dictionary, output_mlf, phoneset, hmmdir):
	#step 1: change to save to working directory
	#step 2: use sp.Popen instead 
	logger("Running HVite...")
	hvite_command = shlex.split("HVite -T 1 -a -m -I {input_mlf} -H {hmm_macros} -H {hmm_defs} -S {test} -i {output_mlf} -p 0.0 -s 5.0 {word_dict} {phoneset} > {results}".format(input_mlf=input_mlf, hmm_macros=hmm_macros, hmm_defs=hmm_defs, test=test_scp, output_mlf=output_mlf, word_dict=word_dictionary, phoneset=phoneset, results=results))
	logger("HVite command: {0}".format(' '.join(hvite_command)))
	os.system(' '.join(hvite_command))
	o, e = None, None
	#o, e = sp.Popen(hvite_command, stdout=sp.PIPE, stderr=sp.PIPE).communicate()
	if o:
		logger("HVite out: {output}".format(output=o))
	if e:
		logger("HVite error: {error}".format(error=e))
	#os.system('HVite -T 1 -a -m -I ' + input_mlf + ' -H ' + hmmdir + '/macros -H ' + hmmdir + '/hmmdefs  -S ./tmp/test.scp -i ' + output_mlf + ' -p 0.0 -s 5.0 ' + word_dictionary + ' ' + phoneset + ' > ./tmp/aligned.results')
	
def getopt2(name, opts, default = None) :
	value = [v for n,v in opts if n==name]
	if len(value) == 0 :
		return default
	return value[0]

if __name__ == '__main__':
	#ensure we run in script's directory
	#set system path
	os.environ["PATH"] = "/opt/local/bin:/opt/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/opt/X11/bin:/usr/texbin"
	logger("sytem path: {0}".format(os.environ.get('PATH')))
	abspath = os.path.abspath(__file__)
	dname = os.path.dirname(abspath)
	os.chdir(dname)
	cwd_msg = "cwd: {0}".format(os.getcwd())
	logger(cwd_msg)
	
	tmp_dir = os.path.join(os.getcwd(), rand_prefix+'tmp')

	tmpwav = os.path.join(tmp_dir, "tmp.wav")
	codetr_scp = os.path.join(tmp_dir, "codetr.scp")
	tmp_plp = os.path.join(tmp_dir, "tmp.plp")
	test_scp = os.path.join(tmp_dir, "test.scp")
	results = os.path.join(tmp_dir, "aligned.results")

	mpfile = os.path.join(os.getcwd(), "model", "monophones")
	word_dictionary = os.path.join(tmp_dir, "dict")	
	input_mlf = os.path.join(tmp_dir, "tmp.mlf")
	output_mlf = os.path.join(tmp_dir, "aligned.mlf")

	#define hmmdir
	hmmdir = os.path.join(os.getcwd(), "model", str(11025))
	hmm_macros = os.path.join(hmmdir, "macros")
	hmm_defs = os.path.join(hmmdir, "hmmdefs")


	#create working directory with unique identifier
	#interface to temp dir?
	#import tempfile
	#dirpath = tempfile.mkdtemp()
	#finally clean up with shutil.rmtree
	#encase it all in main() function
	#def main():
	#try:
	#    execute_app()
	#finally:
	#    handle_cleanup()
	#
	#if __name__=='__main__':
	#    main()
	#
	try:
		opts, args = getopt.getopt(sys.argv[1:], "r:s:e:", ["model="])
		
		# get the three mandatory arguments
		if len(args) != 3 :
			raise ValueError("Specify wavefile, a transcript file, and an output file!")
			
		wavfile, trsfile, outfile = args
		
		logger("wav file: {0}".format(wavfile))
		logger("transcript file: {0}".format(trsfile))
		logger("textgrid file: {0}".format(outfile))

		sr_override = getopt2("-r", opts, None)
		wave_start = getopt2("-s", opts, "0.0")
		wave_end = getopt2("-e", opts, None)
		#add boolean flag for these?
		surround_token = "sp" #getopt2("-p", opts, 'sp')
		between_token = "sp" #getopt2("-b", opts, 'sp')
		
		if surround_token.strip() == "":
			surround_token = None
		if between_token.strip() == "":
			between_token = None
		
		mypath = getopt2("--model", opts, None)
	except:
		print __doc__
		(type, value, traceback) = sys.exc_info()
		print value
		sys.exit(0)
	
	# If no model directory was said explicitly, get directory containing this script.
	hmmsubdir = ""
	sr_models = None
	if mypath == None:
		#change to os.path.join()
		mypath = os.path.dirname(os.path.abspath(sys.argv[0])) + "/model"
		hmmsubdir = "FROM-SR"
		# sample rates for which there are acoustic models set up, otherwise
		# the signal must be resampled to one of these rates.
		sr_models = [8000, 11025, 16000]
	
	if sr_override != None and sr_models != None and not sr_override in sr_models:
		raise ValueError, "invalid sample rate: not an acoustic model available"
	
	#word_dictionary = "./tmp/dict"
	#input_mlf = './tmp/tmp.mlf'
	#output_mlf = './tmp/aligned.mlf'
	
	# create working directory
	prep_working_directory()
	
	#change these to Popen?
	if os.path.exists("dict.local"):
		#copy file to word_dictionary with shutil
		os.system("cat " + mypath + "/dict dict.local > " + word_dictionary)
	else:
		#copy file to word_dictionary with shutil
		os.system("cat " + mypath + "/dict > " + word_dictionary)
	
	#prepare wavefile: do a resampling if necessary
	#tmpwav = "./tmp/sound.wav"
	SR = prep_wav(wavfile, tmpwav, sr_override, wave_start, wave_end)
	
	if hmmsubdir == "FROM-SR":
		hmmsubdir = "/" + str(SR)
	
	#prepare mlfile
	prep_mlf(trsfile, input_mlf, word_dictionary, surround_token, between_token)
 
	#prepare scp files
	prep_scp(tmpwav)
	
	# generate the plp file using a given configuration file for HCopy
	#create_plp(mypath + hmmsubdir + '/config')
	create_plp(os.path.join(hmmdir,'config'))
	
	# run Verterbi decoding
	if not os.path.exists(mpfile) :
		mpfile = mypath + '/hmmnames'
	viterbi(input_mlf, word_dictionary, output_mlf, mpfile, mypath + hmmsubdir)

	# output the alignment as a Praat TextGrid
	writeTextGrid(outfile, readAlignedMLF(output_mlf, SR, float(wave_start)))
	#clean up...
	logger("deleting working directory...")
	shutil.rmtree(tmp_dir)

