import subprocess as sp
import os
import sys
import shlex


"""
called by process.php
"""

log_file = os.path.expanduser("~/websites/poop/uploads/debug2_log")

def logger(message, log_file=log_file):
	"""
	logger
	"""
	with open(log_file, 'a') as lg:
		lg.write("{0}\n".format(message))

def add_noise(f_name):
	"""
	Add noise tags
	"""
	lines = open(f_name, 'r').readlines()
	processed_lines = ["{line} {{NS}}\n".format(line=l.strip().upper()) for l in lines]
	logger("Adding noise tags to transcript...")
	logger("New transcript:\n {0}".format("".join(processed_lines)))
	with open(f_name, 'w') as ns:
		for l in processed_lines:
			ns.write(l)


if __name__ == '__main__':
	realpath = os.path.realpath(__file__)
	dname = os.path.dirname(realpath)
	align_script = os.path.join(dname, "align_new.py")
	#align_script = os.path.expanduser("~/github/forced-alignment/AZP2FA/p2fa/align_new.py")
	
	#args: wav txt processing_option lang
	open(log_file, 'w').close() #empty log
	logger("align script: {0}".format(align_script))
	if len(sys.argv) != 6:
		logger("wrong number of arguments provided.  Exiting...")
		sys.exit()

	wav_file_src = sys.argv[1]
	transcript_src = sys.argv[2]
	textgrid_dst = sys.argv[3]
	processing_option = sys.argv[4]
	language = sys.argv[5]

	#test if preprocessing is necessary...
	logger("Processing transcript with option \"{0}\"".format(processing_option))
	if processing_option == "noise":
		add_noise(transcript_src)

	#send to aligner...
	align_command = "python {align_script} {wav_file} {transcript_file} {textgrid_dst}".format(align_script=align_script, wav_file=wav_file_src, transcript_file=transcript_src, textgrid_dst=textgrid_dst)
	logger("calling align script: \"{0}\"".format(align_command))
	align_command = shlex.split(align_command)
	align_process = sp.Popen(align_command, stdout=sp.PIPE, stderr=sp.PIPE)
	o, e = align_process.communicate()
	if o:
		logger("output: {0}".format(o))
	if e:
		logger("error: {0}".format(e))
	#textgrid_dst = textgrid_dst.split("poop")[-1]
	#handle deletion here: $rm_output = shell_exec("rm $audio_dst; rm $transcript_dst");
	print textgrid_dst


