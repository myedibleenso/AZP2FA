from nltk.metrics.distance import edit_distance as ld #for edit distance...I'm lazy...
from itertools import product
from math import ceil
import cPickle as pickle
import collections
import csv
import re
import sys


class Pronunciation(object):

	def __init__(self, verbose=False):

		#pronunciation dictionary
		self.pro_dict = self.make_pronunciation_dict()
		self.known_words = set(self.pro_dict.keys())
		self.verbose = verbose


	def make_pronunciation_dict(self):
		"""
		Convert cmudict into a python dictionary

		Supports serialization
		"""
		try:
			cmu_dict = pickle.load(open('cmu_dict.p', 'rb'))
			return cmu_dict
		except:
			print "No pickle dump found..."
			entries = [line.rstrip('\n') for line in open('cmudict','r')]
			pro_pair = [(line.split()[0], tuple(line.split()[1:])) for line in entries]

			pro_dict = dict()

			for word, pronunciation in pro_pair:
				if word in pro_dict:
					pro_dict[word].append(pronunciation)
				else:
					pro_dict[word] = [pronunciation]

			pickle.dump(pro_dict, open('cmu_dict.p', 'wb'))
			return pro_dict


	def find_substrings(self, word):
		"""
		finds longest composite substrings
		"""
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


	def most_similar(self, word, threshold=5):
		"""
		finds closest matches based on edit distance
		"""

		word = word.upper()
		closest = [(ld(word, w), w) for w in self.known_words]
		#filter stuff
		closest = sorted([(score, w) for (score, w) in closest if score <= threshold])
		
		return closest[:int(len(closest)*.001)]


	def find_phones(self, strings):
		"""
		finds corresponding phones for list of strings
		"""

		phones = []
		for s in strings:
			s = s.upper()
			#does this work?
			phones.append(self.pro_dict[s])
		return phones

	def _guess_all(self, words):
		"""
		guess pronunciation for multi-word sequence
		"""

		words = words.split()
		possible = [self.guess_pronunciation(word) for word in words]
		possible = [list(p) for p in product(*possible)]
		return possible

	def guess_pronunciation(self, word, use_stress=False):
		"""
		guess the pronunciation
		"""
		
		word = re.sub("[,.!?\n]", '', word)
		if ' ' in word:
			return self._guess_all(word)
		
		matches = self.find_substrings(word)
		phones = self.find_phones(matches)
		
		if use_stress:
			possible_stress = sorted(list(set(seq[0][0] for match in phones for seq in match)))
			
			stress_constraints = [phones[0][i] for i in range(len(phones[0]))]
			#stress_constraints = [seq for match[0] in phones for seq in match]
			if self.verbose:
				print "Stress constraints:\t{0}".format(stress_constraints)
				print "Possible stress patterns:\t{0}".format(possible_stress)

			#get cartesian product of what's possible...
			possible_pronunciations = product(*phones)
			new_pronunciations = []
			for possible_sequences in possible_pronunciations:
				new_seq = [phone for seq in possible_sequences for phone in seq if not re.match('\d', phone)]
				new_pronunciations.append(new_seq)

			# marry cartesian product with stress
			possible_pronunciations = product(possible_stress, new_pronunciations)
			new_pronunciations = []
			for stress, phone_seq in possible_pronunciations:
				new_seq = tuple([stress]+phone_seq)
				#filter candidates by stress constraints
				if any(new_seq[:len(constraint)] == constraint for constraint in stress_constraints):
					new_pronunciations.append(new_seq)

			possible_pronunciations = new_pronunciations

			if self.verbose:
				print "possible pronunciations:"
				for i in range(len(possible_pronunciations)):
					print "{0}:\t{1}".format(str(i+1), possible_pronunciations[i])
			
			return possible_pronunciations

		#if we don't care about stress...
		else:
			#get cartesian product of what's possible...
			possible_pronunciations = product(*phones)
			new_pronunciations = []
			for possible_sequences in possible_pronunciations:
				new_seq = tuple(phone for seq in possible_sequences for phone in seq if not re.match('\d+', phone))
				new_pronunciations.append(new_seq)

			#eliminate duplicates
			possible_pronunciations = sorted(list(set(new_pronunciations)))

			if self.verbose:
				print "possible pronunciations:"
				for i in range(len(possible_pronunciations)):
					print "{0}:\t{1}".format(str(i+1), possible_pronunciations[i])
			
			return possible_pronunciations

	def _round_up(self, number, decimal_places=1):
		"""
		rounds a value to the specified 
		number of decimal places
		"""
		return ceil(number * 10**decimal_places) / 10.0**decimal_places

	def _flatten(self, deep_list):
		"""
		flatten a list of an arbitrary depth

		credit to Cristian at http://stackoverflow.com/questions/2158395/flatten-an-irregular-list-of-lists-in-python
		"""
		for el in deep_list:
			if isinstance(el, collections.Iterable) and not isinstance(el, basestring):
				for sub in self._flatten(el):
					yield sub
			else:
				yield el

	def report_stats(self, text, verbose=True):
		"""
		get info on text
		"""

		text = self.guess_pronunciation(text)

		#ave_words = len(text[0]) if type(text[0]) is list else len(text)
		if type(text[0]) is list:
			num_words = float(len(text[0]))
			#get sum of length of syllables for each possible combo, then divide by # of combos...
			num_syllables = float("{0:.2f}".format(float(sum([sum(len(p) for p in possible) for possible in text])) / len(text)))
			num_syllables_per_word = float("{0:.2f}".format(num_syllables / len(text[0])))

		else:
			num_words = float(len(text))
			num_syllables = float("{0:.2f}".format(float(sum([len(t) for t in text]))))
			num_syllables_per_word = float("{0:.2f}".format(num_syllables / len(text)))
		
		stats = {"words":num_words, 
				 "syllables":num_syllables, 
				 "syllables per word":num_syllables_per_word}
		
		if verbose:
			for entry in stats:
				print "{0}:\t{1}".format(entry, stats[entry])

		return stats

	def file_stats(self, filename, latex_file=True, csv_file=True):
		"""
		get info on a file
		"""

		text = open(filename, 'rb').readlines()
		text = [re.sub("[\n,.'!?]",'',t) for t in text if len(t)>0 and t != '\n']
		stats = []
		pronunciations = []
		for line in text:
			stats.append(self.report_stats(line, verbose=False))
			pronunciations.append(self.guess_pronunciation(line))

		ave_words = self._round_up(sum([d["words"] for d in stats]) / len(stats))
		ave_syllables = self._round_up(sum([d["syllables"] for d in stats]) / len(stats))
		ave_syllables_per_word = self._round_up(sum([d["syllables per word"] for d in stats]) / len(stats))
		
		unique_syllables = set(self._flatten(pronunciations))
		if self.verbose:
			print "Unique syllables:\t{0}".format(unique_syllables)

		overall_stats = collections.OrderedDict([("total sentences",len(stats)),
												 ("unique phonemes", len(unique_syllables)),
												 ("words per sentence", ave_words),
												 ("syllables per sentence", ave_syllables),
												 ("syllables per word", ave_syllables_per_word)])

		for entry in overall_stats:
			print "{0}:\t{1}".format(entry, overall_stats[entry])

		#write a latex table to a .txt file
		if latex_file:
			title = "stats_for_{0}_sentences.txt".format(overall_stats['total sentences'])
			latex_f = open(title,'wb')
			latex_f.write("\\begin{tabular}{|r|l|}\n")
			latex_f.write("\t\\hline\n")
			for key, value in overall_stats.items():
				#print "{0}:\t{1}".format(key, value)
				latex_f.write("\t\\textbf{{{0}}} & {1} \\\\\n".format(key, value))
				latex_f.write("\t\\hline\n")
			latex_f.write("\\end{tabular}\n")
			latex_f.close()

		#write a csv file
		if csv_file:
			title = "stats_for_{0}_sentences.csv".format(overall_stats['total sentences'])
			writer = csv.writer(open(title, 'wb'))
			for key, value in overall_stats.items():
				writer.writerow([key, value])


if __name__ == "__main__":
	print "Initializing dictionary..."
	poo = Pronunciation()
	print "Examining file...\n"
	filename = None
	try:
		filename = sys.argv[1]
	except:
		if not filename:
			filename = 'harvard_sentences_sets_1-3.txt'
			poo.file_stats(filename)



#import difflib as dl
#dl.get_close_matches('STANKY',poo.known_words)		
"""
alphabet = 'abcdefghijklmnopqrstuvwxyz'

def edits1(word):
   splits     = [(word[:i], word[i:]) for i in range(len(word) + 1)]
   deletes    = [a + b[1:] for a, b in splits if b]
   transposes = [a + b[1] + b[0] + b[2:] for a, b in splits if len(b)>1]
   replaces   = [a + c + b[1:] for a, b in splits for c in alphabet if b]
   inserts    = [a + c + b     for a, b in splits for c in alphabet]
   return set(deletes + transposes + replaces + inserts)

def known_edits2(word):
	return set(e2 for e1 in edits1(word) for e2 in edits1(e1) if e2 in NWORDS)

def known(words): return set(w for w in words if w in NWORDS)

def correct(word):
	candidates = known([word]) or known(edits1(word)) or known_edits2(word) or [word]
	return max(candidates, key=NWORDS.get)
"""