"""
What options do i really want and how do I want this to work?
* standard option with no flags:
    - list of directories
    - action:
        create a dictionary for current files
        if md5sum exists output the diff to standard output + replace md5sum file
    - call md5sum for each dir
* --output=x
    - specifies where to save the changes (list)
    - same as above but output to specified files
    - just set the flag this will change the log function
* --comparefiles
    - takes two md5sum files and compares them
    - standard output if no --output flag
    - call compare function
* --twodir
    - takes two directories and compares them to each other, creating md5sum files
      in each one
* -3/--mp3
  Enable MP3 mode: for files ending in .mp3, calculate a checksum
  which skips ID3v1 and ID3v2 tags.  This checksum differs from the
  normal one which is compatible with GNU md5sum.  The md5sum file is
  tagged so that md5dir will in future always use MP3 mode for the
  directory.  Consider using mp3md5.py instead, which keeps this
  tag-skipping checksum in the ID3v2 tag as a Unique File ID.
* -h/--help
  Output this message then exit.

What functions do I need? :
a) take two dictionaries and output diff
b) create dictionary for given directory
c) main with
    - two direcories which creates new md5sum for both + compares
    - one directory, creates new md5sum and compares with old
d) return dictionary from file
e) log either to stdout or file

"""



from getopt import getopt
import md5
import os
import os.path as op
import re
import struct
import sys
import magic
import errno
import dictdiff

hashfile = "md5sum" # Default name for checksum file
output = None
mp3mode = False     # Whether to use tag-skipping checksum for MP3s

# Regular expression for lines in GNU md5sum file
md5line = re.compile(r"^([0-9a-f]{32}) [\ \*](.*)$")


def comparemd5files(file1, file2):
    """ Compares two md5sum files. """
    d1 = getDictionary(file1)
    d2 = getDictionary(file2)
    diff = dictdiff.DictDiffer(d2, d1)
    added = diff.added()
    deleted = diff.removed()
    changed = diff.changed()
    unchanged = diff.unchanged()
    for fname in added:
        log("ADDED " + op.abspath(fname))
    for fname in deleted:
        log("DELETED " + op.abspath(fname))
    for fname in changed:
            log("CHANGED " + op.abspath(fname))
    # log("LOCATION", root)
    log("STATUS: confirmed %d added %d deleted %d changed %d" % (
        len(unchanged), len(added), len(deleted), len(changed)))

def log(msg):
    """ Writes given message to the relevant output.""" 
    if output:
        output.write(msg)
    else:
        print msg

def getDictionary(file):
    """ Converts the md5sum file into a dictionary of filename -> md5sum """
    d = {}
    with open(file) as f:
        for line in f:
            match = md5line.match(line.rstrip(""))
            # Skip non-md5sum lines
            if not match:
                continue
            d[match.group(2)] = match.group(1)
    return d


if __name__ == "__main__":
    # Parse command-line options
    optlist, args = getopt(
        sys.argv[1:], "3cf:hlmnqru",
        ["mp3", "output=", "comparefiles", "twodir", "help"])
    for opt, value in optlist:
        if opt in ["-3", "--mp3"]:
            mp3mode = True
        elif opt in ["-o", "--output"]:
            output = open(value)
        elif opt in ["-h","--help"]:
            print __doc__
            sys.exit(0)
        elif opt in ["-c", "--comparefiles"]:
            comparefiles = True
        elif opt in ["-t", "--twodir"]:
            twodir = True
    if len(args) == 0:
        print "Exiting because no directories given (use -h for help)"
        sys.exit(0)


    # Compare two md5sum files.
    if comparefiles:
        if len(args) != 2 or not op.isfile(args[0]) or not op.isfile(args[1]):
            print "Exiting because expected two directory pathnames."
            sys.exit(0)
        else:
            comparemd5files(args[0], args[1])
    # Compare two directories
    elif twodir:
        print "Two dir"
    # Analyze the given directories.
    else:
        # Treat each argument separately
        for index, start in enumerate(args):
            if not op.isdir(start):
                print "Argument %s is not a directory" % start
                continue

    if output:
        output.close()