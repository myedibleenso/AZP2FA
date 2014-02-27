import subprocess as sp
import os
import sys
import shlex


"""
called by process.php
"""

align_script = "/Users/gus/github/forced-alignment/forced-alignment/p2fa/align.py"
log_file = os.path.join(os.path.expanduser("~"), "aligner_log")

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print "Wrong number of arguments provided.  Exiting..."
		sys.exit()

	wav_file_src = sys.argv[1]
	transcript_src = sys.argv[2]
	textgrid_dst = sys.argv[3]
	
	with open(log_file, 'a') as f:
		f.write("wav file: {0}\n".format(wav_file_src))
		f.write("transcript: {0}\n".format(transcript_src))
		f.write("textgrid: {0}\n".format(textgrid_dst))
	#print "\naligning \'{0}\'...({1} out of {2})".format(f, completed, total)
	align_command = "python {align_script} {wav_file} {transcript_file} {textgrid_dst}".format(align_script=align_script, wav_file=wav_file_src, transcript_file=transcript_src, textgrid_dst=textgrid_dst)
	align_command = shlex.split(align_command)
	align_process = sp.Popen(align_command, stdout=sp.PIPE, stderr=sp.PIPE)
	o, e = align_process.communicate()

	with open(log_file, 'a') as f:
		f.write("Output:\n {0}\n".format(o))
		f.write("Error:\n {0}\n\n\n".format(e))
	print textgrid_dst


