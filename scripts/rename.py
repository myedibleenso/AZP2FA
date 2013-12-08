import os

files = [f for f in os.listdir('.') if os.path.isfile(f)]
old = raw_input("REPLACE: ")
new = raw_input("WITH: ")

for f in files:
	os.rename(f, f.replace(old, new))