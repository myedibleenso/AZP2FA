import os
import sys

"""
python align_batch.py "some/directory"

python align_batch.py "some/directory/with/subdirectories" -r

-r to check subfolders for .wav files...
"""
#python align.py ./test/BREY00538.wav ./test/BREY00538.txt ./test/BREY00538.TextGrid

#test_dir = '/Users/gus/Dropbox/Projects/Forced_Alignment/TEST_DATA/spliced'
#python align.py "/Users/gus/Dropbox/Projects/Forced_Alignment/TEST_DATA/spliced/MALE1/MALE1_HS_N_FAST_1-1.wav" "/Users/gus/Dropbox/Projects/Forced_Alignment/TEST_DATA/spliced/MALE1/MALE1_HS_N_FAST_1-1.txt" "/Users/gus/Dropbox/Projects/Forced_Alignment/TEST_DATA/spliced/MALE1/MALE1_HS_N_FAST_1-1.TextGrid"
#align_script = '/Users/gus/Dropbox/Projects/Forced_Alignment/p2fa/align.py'

test_dir = sys.argv[1]

if not os.path.isdir(test_dir):
	"Bad directory!  Exiting..."
	sys.exit()

if len([f for f in os.listdir(test_dir) if f[-3:] == 'wav']) == 0:
	"No .wav files in specified directory!  Exiting..."
	sys.exit()


if sys.argv[-1] == '-r':
	#only do this if recursive...
	dirs = [test_dir+'/'+f for f in os.listdir(test_dir) if os.path.isdir(test_dir+'/'+f)]
	files = sorted(list(set([directory+'/'+f[:f.find('.')] for directory in dirs for f in os.listdir(directory) if f[-3:] == 'wav'])))

else:
	files = sorted(list(set([test_dir+'/'+f[:f.find('.')] for f in os.listdir(test_dir) if f[-3:] == 'wav'])))

completed = 0
total = len(files)
for f in files:
	completed += 1
	print "\naligning \'{0}\'...({1} out of {2})".format(f, completed, total)
	align_command = "python align.py {0} {1} {2}".format(f+'.wav', f+'.txt', f+'.TextGrid')
	os.system(align_command)



