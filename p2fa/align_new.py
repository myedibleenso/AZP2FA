#!/usr/bin/env python

""" Command-line usage:
	  python align.py [options] wave_file transcript_file output_file
	  where options may include:
		-r sampling_rate -- override which sample rate model to use, one of 8000, 11025, and 16000
		-s start_time    -- start of portion of wavfile to align (in seconds, default 0)
		-e end_time      -- end of portion of wavfile to align (in seconds; defaults to end)
			
	You can also import this file as a module and use the functions directly.
"""

from itertools import product
import os
import sys
import getopt
import wave
import re

import cPickle as pickle


class Align(object):
	"""
	A humble aligner

	DEPENDENCIES:
		htk 3.4
		sox (> v3)
	"""

	def __init__(self, pro_dict=None, verbose=True):
		if not pro_dict:
			self.pro_dict = self.make_pronunciation_dictionary()
			#self.pro_dict = pickle.load('~/Desktop/cmu_dict.p')

		#list of known words (from provided dict file)...
		self.known_words = set(self.pro_dict.keys())
		
		#transcript stuff...
		self.transcript_dict = None
		self.transcript = None
		self.pause_char = 'sp'

		#file stuff...
		self.sound_file = None
		
		self.input_mlf = './tmp/tmp.mlf'
		self.aligned_mlf = './tmp/aligned.mlf'
		self.textgrid_file = None

		#these work...
		self.sr_models = [8000, 11025, 16000]

		self.verbose = True

		self.rate = None
		self.optimum_sr = 11025


	def make_pronunciation_dictionary(self, pronunciation_dict=None):
		"""
		Convert pronunciation dictionary into a python dictionary

		Supports serialization
		"""

		default_pro_dict = './model/new_dict'
		
		if not pronunciation_dict:
			entries = [line.rstrip('\n') for line in open(default_pro_dict, 'r')]
			pro_pair = [(line.split()[0], tuple(line.split()[1:])) for line in entries]

		else:
			entries = [line.rstrip('\n') for line in open(pronunciation_dict, 'r')]
			#pairs of (word, pronunciation)
			pro_pair = [(line.split()[0], tuple(line.split()[1:])) for line in entries]

		pro_dict = dict()
		for word, pronunciation in pro_pair:
			if word in pro_dict:
				pro_dict[word].append(pronunciation)
			else:
				pro_dict[word] = [pronunciation]

		return pro_dict


	def find_substrings(self, word):
		word = word.upper()
		segments = []
		if word not in self.known_words:
			word_length = len(word)
			for i in range(1, word_length):
				if word in self.known_words:
					segments.append(word)
					break
				substring_length = word_length - i
				substring = word[:substring_length]
				if substring in self.known_words:
					segments.append(substring)
					word = word[substring_length:]
					print 'Substring:\t {0}'.format(substring)
					print "Remaining:\t {0}".format(word)
		else:
			segments.append(word)
		return segments

	
	def find_phones(self, strings):
		"""
		finds corresponding phones for list of strings
		"""
		phones = []
		for s in strings:
			s = s.upper()
			#does this work?
			phones+=self.pro_dict[s]
		return phones


	def guess_pronunciation(self, word):
		"""
		guess the pronunciation

		htk doesn't support stress, so dict has been sterilized accordingly...
		"""
		matches = self.find_substrings(word)
		phones = self.find_phones(matches)

		#get cartesian product of what's possible...
		possible_pronunciations = product(*phones)
		new_pronunciations = []
		for possible_sequences in possible_pronunciations:
			new_seq = tuple(phone for seq in possible_sequences for phone in seq)
			new_pronunciations.append(new_seq)

		#eliminate duplicates
		possible_pronunciations = sorted(list(set(new_pronunciations)))

		if self.verbose:
			print "possible pronunciations:"
			for i in range(len(possible_pronunciations)):
				print "{0}:\t{1}".format(str(i+1), possible_pronunciations[i])
		
		return possible_pronunciations


	def check_dictionary(self, transcript):
		"""
		checks words in transcript for membership in pronunciation dictionary

		(executed for side effects)
		"""
		#find all known and unknown words..
		unknown_words = [w for w in open(transcript,'r').readlines() if w.upper() not in self.known_words]
		
		if unknown_words and self.verbose:
			print 'Unknown word \'{0}\'encountered! Guessing its pronunciation...'.format(unknown_word)


	def make_transcript_dictionary(self, transcript):
		"""
		Create transcript dictionary
		"""

		words = [w for w in open(transcript,'r').readlines()]
		#preprocess words (remove problematic stuff)...
		words = self.clean_words(words)
		
		#report on unknown words
		self.check_dictionary(words)

		#entries = [pair for word in words for pair in zip([word], self.guess_pronunciation(word))]
		entries = [(w, ' '.join(pronunciation)) for word in words for w, pronunciation in zip([word], self.guess_pronunciation(word))]

		#add the pause character
		entries.append(self.pause_char, self.pause_char)
		#save as attribute
		self.transcript_dict = entries


	def clean_words(self, words):
		"""
		preprocess words for transcript
		"""
		clean_words = []
		pauses = re.compile("[,.?]")
		for word in words:
			cleaned = word.upper()
			if re.match(pauses, cleaned):
				cleaned = re.sub(pauses, 'sp', cleaned) #replace punctuation denoting pauses
			if re.search(pauses, cleaned):
				cleaned = re.sub(pauses, '', cleaned) #replace punctuation denoting pauses
			if '-' in cleaned:
				cleaned = word.split('-')
				clean_words += cleaned
			else:
				clean_words.append(cleaned)
		
		self.make_transcript(cleaned_words)

		return clean_words


	def make_transcript(self, words):
		"""
		Make transcript by interspersing a pause symbol 
		between adjacent list elements
		"""

		transcript = []
		for w in words:
			transcript += [self.pause_char, w]
		#transcript.append(self.pause_char)

		#save as attribute
		self.transcript = transcript


	def align(self, sound_file, transcript=None, textgrid=None):
		"""
		align an audio file
		"""		
		base_file = re.sub('\.wav', '', sound_file)
		if not re.search('\.wav', sound_file, flags=re.IGNORECASE):
			sound_file = sound_file + '.wav'
		
		if not transcript:
			transcript = base_file + '.txt'

		if not textgrid:
			textgrid = base_file + 'TextGrid'

		#prepare audio
		self.resample(sound_file)

		#store textgrid destination
		self.textgrid_file = textgrid

		#build the transcript dictionary	
		self.make_transcript_dictionary(transcript)
	
	#not finished


	def align_all(self, directory=None):
		"""
		align all audio files in a specified directory
		"""
		if directory:
			directory = os.listdir(directory)
		else:
			directory = os.listdir('.')
		extension = re.compile('\.[a-z]+', re.IGNORECASE)
		files = set([re.sub(extension, '', f) for f in directory])

		for f in files:
			#run align() on each file...
			self.align(sound_file=f)


	def resample(self, sound_file, optimize=True):
		"""
		resample audio

		(method with side effects)
		"""
		bad_sr = False
		temp_file = "./tmp/sound.wav"

		f = wave.open(sound_file, 'r')
		SR = f.getframerate()
		f.close()
		
		#attribute of Align
		rate = self.rate

		if SR not in self.sr_models:
			bad_sr = True		
		
		if rate in self.sr_models:
			if self.verbose:
				print "Resampling to {0} HZ...".format(rate)
			#use specified rate
			resample_command = "sox {0} -r {1} {2}".format(sound_file, str(rate), temp_file)

		if optimize or bad_sr:
			#update rate
			self.rate = self.optimum_sr
			if self.verbose:
				print "Optimizing sample rate ({0} HZ)...".format(self.optimum_sr)
			self.optimize(sound_file)
			resample_command = "sox {0} -r {1} {2}".format(sound_file, str(self.optimum_sr), temp_file)

		#resample
		os.system(resample_command)

		#note location of resampled sound file...
		self.sound_file = temp_file


	def write_mlf(self):
		"""
		write mlf file for htk
		"""
		fw = open(self.input_mlf, 'w')
		fw.write('#!MLF!#\n')
		fw.write('"*/tmp.lab"\n')
		#write transcript to file
		fw.writelines([w+'\n' for w in self.transcript])
		fw.close()
		self.


	def read_aligned_mlf(self):
		"""
		Reads an MLF alignment (output) file
		returns a list of type words, each word is a list containing...
		[["word label", ["phone_first", start, end], ..., ["phone_last", start, end]]
		
		NOTE: times are in seconds.
		"""

		f = open(self.aligned_mlf, 'r')
		lines = [l.rstrip() for l in f.readlines()]
		f.close()
		
		#if only headers and '.' lines, something went wrong...
		if len(lines) < 3:
			raise ValueError("Alignment did not complete succesfully.")

		#["word label", ["phone_first", start, end], ..., ["phone_last", start, end]]
		wordlist = []
		#NOTE: if this is confusing, look at aligned.mlf to see an example
		for i in range(2, len(lines)):
			line = lines[i].split()
			
			#htk uses a '.' to mark the end of the aligned ml file
			if line[0] == '.':
				break
			
			else:
				# Is this the start of a word; do we have a word label?
				if (len(line) == 5):
					# Make a new word list in ret and put the word label at the beginning
					word = line[-1]
					word_list.append([word])
				
				#store current phone
				phone = line[2]

				#0.0125 is ...?
				start = float(line[0])/10000000.0 + 0.0125
				end = float(line[1])/10000000.0 + 0.0125   
				
				if (self.rate == 11025):
					adjustment = (11000.0/11025.0)
					start *= adjustment
					end *= adjustment
				
				if start < end:
					#Append this phone to the latest word (sub-)list w/ start & end times
					word_list[-1].append([phone, start+wave_start, end+wave_start])
				
		return wordlist


#to be fixed...
	def writeTextGrid(self, textgrid_out=None):
		"""
		Create textGrid from aligned MLF output
		"""

		word_alignments = self.read_aligned_mlf()

		if not textgrid_out:
			textgrid_out = self.textgrid_file
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
			# word label, first phone start time, last phone end time
			wrds.append([wrd[0], wrd[1][1], wrd[-1][2]])
		
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

	def prep_working_directory(self):
		os.system("rm -r -f ./tmp")
		os.system("mkdir ./tmp")

	def prep_scp(self, wavfile):
		fw = open('./tmp/codetr.scp', 'w')
		fw.write(wavfile + ' ./tmp/tmp.plp\n')
		fw.close()
		fw = open('./tmp/test.scp', 'w')
		fw.write('./tmp/tmp.plp\n')
		fw.close()
		
	def create_plp(self, hcopy_config):
		os.system('HCopy -T 1 -C ' + hcopy_config + ' -S ./tmp/codetr.scp')
		
	def viterbi(self, input_mlf, word_dictionary, output_mlf, phoneset, hmmdir):
		os.system('HVite -T 1 -a -m -I ' + input_mlf + ' -H ' + hmmdir + '/macros -H ' + hmmdir + '/hmmdefs  -S ./tmp/test.scp -i ' + output_mlf + ' -p 0.0 -s 5.0 ' + word_dictionary + ' ' + phoneset + ' > ./tmp/aligned.results')




def prep_mlf(trsfile, mlffile, word_dictionary, surround, between):
	# Read in the dictionary to ensure all of the words
	# we put in the MLF file are in the dictionary. Words
	# that are not are skipped with a warning.
	
	writeInputMLF(mlffile, words)
	

def writeInputMLF(mlffile, words) :
	fw = open(mlffile, 'w')
	fw.write('#!MLF!#\n')
	fw.write('"*/tmp.lab"\n')
	for wrd in words:
		fw.write(wrd + '\n')
	fw.write('.\n')
	fw.close()


def readAlignedMLF(mlffile, SR, wave_start):
	# This reads a MLFalignment output  file with phone and word
	# alignments and returns a list of words, each word is a list containing
	# the word label followed by the phones, each phone is a tuple
	# (phone, start_time, end_time) with times in seconds.
	
	f = open(mlffile, 'r')
	lines = [l.rstrip() for l in f.readlines()]
	f.close()
	
	if len(lines) < 3 :
		raise ValueError("Alignment did not complete succesfully.")
			
	j = 2
	ret = []
	while (lines[j] != '.'):
		if (len(lines[j].split()) == 5): # Is this the start of a word; do we have a word label?
			# Make a new word list in ret and put the word label at the beginning
			wrd = lines[j].split()[4]
			ret.append([wrd])
		
		# Append this phone to the latest word (sub-)list
		ph = lines[j].split()[2]
		if (SR == 11025):
			start = (float(lines[j].split()[0])/10000000.0 + 0.0125)*(11000.0/11025.0)
			end = (float(lines[j].split()[1])/10000000.0 + 0.0125)*(11000.0/11025.0)
		else:
			start = float(lines[j].split()[0])/10000000.0 + 0.0125
			end = float(lines[j].split()[1])/10000000.0 + 0.0125   
		if start < end:
			ret[-1].append([ph, start+wave_start, end+wave_start])
		
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

def prep_scp(wavfile) :
	fw = open('./tmp/codetr.scp', 'w')
	fw.write(wavfile + ' ./tmp/tmp.plp\n')
	fw.close()
	fw = open('./tmp/test.scp', 'w')
	fw.write('./tmp/tmp.plp\n')
	fw.close()
	
def create_plp(hcopy_config) :
	os.system('HCopy -T 1 -C ' + hcopy_config + ' -S ./tmp/codetr.scp')
	
def viterbi(input_mlf, word_dictionary, output_mlf, phoneset, hmmdir) :
	os.system('HVite -T 1 -a -m -I ' + input_mlf + ' -H ' + hmmdir + '/macros -H ' + hmmdir + '/hmmdefs  -S ./tmp/test.scp -i ' + output_mlf + ' -p 0.0 -s 5.0 ' + word_dictionary + ' ' + phoneset + ' > ./tmp/aligned.results')
	
def getopt2(name, opts, default = None) :
	value = [v for n,v in opts if n==name]
	if len(value) == 0 :
		return default
	return value[0]

if __name__ == '__main__':
	
	try:
		opts, args = getopt.getopt(sys.argv[1:], "r:s:e:", ["model="])
		
		# get the three mandatory arguments
		if len(args) != 3 :
			raise ValueError("Specify wavefile, a transcript file, and an output file!")
			
		wavfile, trsfile, outfile = args
		
		sr_override = getopt2("-r", opts, None)
		wave_start = getopt2("-s", opts, "0.0")
		wave_end = getopt2("-e", opts, None)
		surround_token = "sp" #getopt2("-p", opts, 'sp')
		between_token = "sp" #getopt2("-b", opts, 'sp')
		
		if surround_token.strip() == "":
			surround_token = None
		if between_token.strip() == "":
			between_token = None
		
		mypath = getopt2("--model", opts, None)
	except :
		print __doc__
		(type, value, traceback) = sys.exc_info()
		print value
		sys.exit(0)
	
	# If no model directory was said explicitly, get directory containing this script.
	hmmsubdir = ""
		
	word_dictionary = "./tmp/dict"
	input_mlf = './tmp/tmp.mlf'
	output_mlf = './tmp/aligned.mlf'
	
	current_path = os.path.abspath('.')
	model_directory = current_path+"/model"

	# create working directory
	prep_working_directory()
	
	# create ./tmp/dict by concatening our dict with a local one
	if os.path.exists("dict.local"):
		os.system("cat " + mypath + "/dict dict.local > " + word_dictionary)
	else:
		os.system("cat " + mypath + "/new_dict > " + word_dictionary)
	
	"/Users/gus/Dropbox/Projects/Forced_Alignment/p2fa/model"
	os.path.exists()	
	if hmmsubdir == "FROM-SR" :
		hmmsubdir = "/" + str(self.rate)
	
	#prepare mlfile
	prep_mlf(trsfile, input_mlf, word_dictionary, surround_token, between_token)
 
	#prepare scp files
	prep_scp(tmpwav)
	
	# generate the plp file using a given configuration file for HCopy
	create_plp(mypath + hmmsubdir + '/config')
	
	# run Verterbi decoding
	#print "Running HVite..."
	mpfile = mypath + '/monophones'
	if not os.path.exists(mpfile) :
		mpfile = mypath + '/hmmnames'
	viterbi(input_mlf, word_dictionary, output_mlf, mpfile, mypath + hmmsubdir)

	# output the alignment as a Praat TextGrid
	writeTextGrid(outfile, readAlignedMLF(output_mlf, SR, float(wave_start)))




#sterilize text
clean words = []
pauses = re.compile("[,.?]")
for word in words:
	word.upper()
	cleaned = word
	if '-' in cleaned:
		cleaned = word.split('-')
	if re.match(pauses, cleaned)


re.compile(r"(([A-Z]+)(-([A-Z]+))+)", re.IGNORECASE)
