"""
Script creates transcripts in subject-specific subfolders
"""
import os
import re

no_punct = re.compile("[,.!?]")
subject_id = re.compile("(FE)?MALE\d+")

#look at subject folders
subject_folders = ['./spliced/{0}'.format(f) for f in os.listdir('./spliced/') if os.path.isdir('./spliced/{0}'.format(f))]

sentences = open('harvard_sentences_sets_1-3.txt','r').readlines()
sentences = [re.sub(no_punct, '', s.rstrip()).upper() for s in sentences]

hs_set1 = sentences[:10]
hs_set2 =sentences[11:21]
hs_set3 =sentences[22:]

h_sentences = [hs_set1, hs_set2, hs_set3]

speakers = ['MALE1_HS_N_NORM', 'MALE1_HS_N_FAST', 'FEMALE1_HS_N_NORM', 'FEMALE1_HS_N_FAST', 'FEMALE2_HS_NN_NORM', 'FEMALE2_HS_NN_FAST']

#sets 1 - 3
sets = range(1,4)
#sentences 1 - 10
sentence_num = range(1, 11)

#directory = re.search(subject_id, filename)
for set_num in sets:
	for sentence in sentence_num:
		#construct transcript
		output = '\n'.join(h_sentences[set_num-1][sentence-1].split())
		for speaker in speakers:
			#find speaker id
			speaker_id = speaker[:speaker.find('_')]
			#create filename for transcript
			filename = '{0}_{1}-{2}.txt'.format(speaker, set_num, sentence)
			#assemble path+filename
			f_dest = [subj_f for subj_f in subject_folders if subj_f[subj_f.rfind('/')+1:] == speaker_id][0] + '/' + filename
			#write transcript to appropriate file
			open(f_dest, 'w').write(output)
			print f_dest