import subprocess as sp
import os
import sys
import shlex


"""
called by process.php
"""

align_script = os.path.expanduser("~/github/forced-alignment/forced-alignment/p2fa/align.py")

if __name__ == '__main__':
	if len(sys.argv) != 4:
		print "wrong number of arguments provided.  Exiting..."
		sys.exit()

	wav_file_src = sys.argv[1]
	transcript_src = sys.argv[2]
	textgrid_dst = sys.argv[3]
	
	#print "\naligning \'{0}\'...({1} out of {2})".format(f, completed, total)
	align_command = "python {align_script} {wav_file} {transcript_file} {textgrid_dst}".format(align_script=align_script, wav_file=wav_file_src, transcript_file=transcript_src, textgrid_dst=textgrid_dst)
	align_command = shlex.split(align_command)
	align_process = sp.Popen(align_command, stdout=sp.PIPE, stderr=sp.PIPE)
	o, e = align_process.communicate()
	print textgrid_dst


