"""
Usage: md5dir [options] [directories]

Without options it writes an 'md5sum' file in each of the specified directories
and compares it with its previous state. It writes the differences to standard
output.

-3/--mp3
  Enable MP3 mode: for files ending in .mp3, calculate a checksum
  which skips ID3v1 and ID3v2 tags.  This checksum differs from the
  normal one which is compatible with GNU md5sum.  The md5sum file is
  tagged so that md5dir will in future always use MP3 mode for the
  directory.  Consider using mp3md5.py instead, which keeps this
  tag-skipping checksum in the ID3v2 tag as a Unique File ID.

-h/--help
  Output this message then exit.

-o/--output=X
  Write the changes to the file specified as X

-c/--comparefiles
  Compares the two md5sum files specified as arguments.

-t/--twodir
  Creates md5sum files in the two directories specified and compares them.

-q/--quiet
  Does not output the changes. Suitable for initialising a directory.
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
comparefiles = False
twodir = False
quiet = False

# Regular expression for lines in GNU md5sum file
md5line = re.compile(r"^([0-9a-f]{32}) [\ \*](.*)$")


def comparemd5dict(d1, d2):
    """ Compares two md5sum files. """
    diff = dictdiff.DictDiffer(d2, d1)
    added = diff.added()
    deleted = diff.removed()
    changed = diff.changed()
    unchanged = diff.unchanged()
    for fname in added:
        log("ADDED %s" % op.abspath(fname))
    for fname in deleted:
        log("DELETED %s" % op.abspath(fname))
    for fname in changed:
        log("CHANGED %s" % op.abspath(fname))
    log("STATUS: confirmed %d added %d deleted %d changed %d" % (
        len(unchanged), len(added), len(deleted), len(changed)))

def log(msg):
    """ Writes given message to the relevant output.""" 
    if not quiet:
        if output:
            output.write(msg + "\n")
        else:
            print msg

def getDictionary(file):
    """ Converts the md5sum file into a dictionary of filename -> md5sum """
    d = {}
    if not op.isfile(file):
        return d
    with open(file) as f:
        for line in f:
            match = md5line.match(line.rstrip(""))
            # Skip non-md5sum lines
            if not match:
                continue
            d[match.group(2)] = match.group(1)
    return d

def master_list(start):
    """Return a list of files relative to start directory, and remove
    all hashfiles except the one directly under start. """
    flist = []
    oldcwd = os.getcwd()
    os.chdir(start)
    # Collect all files under start (follow directory symbolic links).
    for root, dirs, files in os.walk(".", followlinks=True):
        for fname in files:
            fname = op.join(root[2:], fname)
            # Take care of symbolic links pointing to a file.
            try:
                if op.islink(fname):
                        # We are using this command to check whether the link
                        # is not broken.
                        os.stat(fname)
                        fname = os.readlink(fname)
                        if not op.isabs(fname):
                            fname = op.join(root[2:], fname)
                with magic.Magic(flags=magic.MAGIC_MIME_TYPE) as m:
                    fileType = m.id_filename(fname)
                # Ignore sockets.
                if fileType != "inode/socket":
                    flist.append(fname)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    print 'BROKEN: %s' % fname
                else:
                    raise e
    os.chdir(oldcwd)
    return flist

### WARNING: ORIGINAL FUNCTION IS IN MP3MD5.PY - MODIFY THERE
def calculateUID(filepath):
    """Calculate MD5 for an MP3 excluding ID3v1 and ID3v2 tags if
    present. See www.id3.org for tag format specifications."""
    f = open(filepath, "rb")
    # Detect ID3v1 tag if present
    finish = os.stat(filepath).st_size;
    f.seek(-128, 2)
    if f.read(3) == "TAG":
        finish -= 128
    # ID3 at the start marks ID3v2 tag (0-2)
    f.seek(0)
    start = f.tell()
    if f.read(3) == "ID3":
        # Bytes w major/minor version (3-4)
        # Flags byte (5)
        flags = struct.unpack("B", f.read(1))[0]
        # Flat bit 4 means footer is present (10 bytes)
        footer = flags & (1<<4)
        # Size of tag body synchsafe integer (6-9)
        bs = struct.unpack("BBBB", f.read(4))
        bodysize = (bs[0]<<21) + (bs[1]<<14) + (bs[2]<<7) + bs[3]
        # Seek to end of ID3v2 tag
        f.seek(bodysize, 1)
        if footer:
            f.seek(10, 1)
        # Start of rest of the file
        start = f.tell()
    # Calculate MD5 using stuff between tags
    f.seek(start)
    h = md5.new()
    h.update(f.read(finish-start))
    f.close()
    return h.hexdigest()

def calcsum(filepath, mp3mode):
    """Return md5 checksum for a file. Uses the tag-skipping algorithm
    for .mp3 files if in mp3mode."""
    if mp3mode and filepath.endswith(".mp3"):
        return calculateUID(filepath)
    h = md5.new()
    f = open(filepath, "rb")
    s = f.read(1048576)
    while s != "":
        h.update(s)
        s = f.read(1048576)
    f.close()
    return h.hexdigest()

def writesums(root, checksums):
    """Given a list of (filename,md5) in checksums, write them to
    filepath in md5sum format sorted by filename, with a #md5dir
    header"""
    f = open(op.join(root, hashfile), "w")
    f.write("#md5dir %s\n" % root)
    for fname, md5 in sorted(checksums, key=lambda x:x[0]):
        f.write("%s  %s\n" % (md5, fname))
    f.close()

def makesums(root):
    """Creates an md5sum file for the given directory and returns the
    dictionary."""
    checksums = {}
    for fname in master_list(root):
        newhash = calcsum(op.join(root,fname), mp3mode)
        checksums[fname] = newhash
    writesums(root, checksums.iteritems())
    return checksums

if __name__ == "__main__":
    # Parse command-line options
    optlist, args = getopt(
        sys.argv[1:], "3cf:hlmnqru",
        ["mp3", "output=", "comparefiles", "twodir", "help"])
    for opt, value in optlist:
        if opt in ["-3", "--mp3"]:
            mp3mode = True
        elif opt in ["-o", "--output"]:
            output = open(value, "w+")
        elif opt in ["-h","--help"]:
            print __doc__
            sys.exit(0)
        elif opt in ["-c", "--comparefiles"]:
            comparefiles = True
        elif opt in ["-t", "--twodir"]:
            twodir = True
        elif opt in ["-q", "--quiet"]:
            quiet = True
    if len(args) == 0:
        print "Exiting because no directories given (use -h for help)"
        sys.exit(0)


    # Compare two md5sum files.
    if comparefiles:
        if len(args) != 2 or not op.isfile(args[0]) or not op.isfile(args[1]):
            print "Exiting because two file pathnames expected."
            sys.exit(0)
        else:
            comparemd5dict(getDictionary(args[0]), getDictionary(args[1]))
    # Compare two directories
    elif twodir:
        if len(args) != 2 or not op.isdir(args[0]) or not op.isdir(args[1]):
            print "Exiting because two directory pathnames expected."
        else:
            sums1 = makesums(args[0])
            sums2 = makesums(args[1])
            comparemd5dict(sums1, sums2)

    # Analyze the given directories.
    else:
        # Treat each argument separately
        for index, start in enumerate(args):
            if not op.isdir(start):
                print "Argument %s is not a directory" % start
                continue
            sums1 = getDictionary(op.join(start, hashfile))
            comparemd5dict(sums1, makesums(start))

    if output:
        output.close()