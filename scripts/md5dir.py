"""
Modified from http://snipplr.com/view/4023/

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

-i/--ignore=X
  Specifies the YAML file with directories/files to be ignored.

--time
  Outputs the runtime of the program. Development purpose only.

--hashfile=X
  Specify the location of the md5sum. X can be a list if analyzing several
  directories.

-v/--verbose
  If set the program will output progress status.

"""

import md5
import os
import os.path as op
import re
import struct
import sys
import errno
import dictdiff
import yaml
import fnmatch
import timeit
import tempfile
import shutil
import subprocess
import argparse


hashfile = "md5sum"  # Default name for checksum file.
ignores = []         # By default don't ignore any files.
time = False         # By default don't compute the runtime
verbose = False
fileno = 0

# Regular expression for lines in GNU md5sum file
md5line = re.compile(r"^([0-9a-f]{32}) [\ \*](.*)$")


def comparemd5dict(d1, d2, root):
    """ Compares two md5sum files. """
    diff = dictdiff.DictDiffer(d2, d1)
    added = diff.added()
    deleted = diff.removed()
    changed = diff.changed()
    unchanged = diff.unchanged()
    outputfilelist("ADDED", added)
    outputfilelist("DELETED", deleted)
    outputfilelist("CHANGED", changed)
    log("LOCATION: %s" % root)
    log("STATUS: confirmed %d added %d deleted %d changed %d" % (
        len(unchanged), len(added), len(deleted), len(changed)))


def outputfilelist(name, filelist):
    for fname in filelist:
        if not toignore(fname):
            log("%s: %s" % (name, fname))


def log(msg):
    """ Writes given message to the relevant output."""
    if not suppress_changes:
        output.write(msg + "\n")


def getDictionary(filename):
    # If file doesn't exists we return an empty dictionary.
    if not op.isfile(filename):
        return
    with open(filename) as f:
        for line in f:
            match = md5line.match(line.rstrip(""))
            # Skip non-md5sum lines
            if not match:
                continue
            yield {"file": match.group(2),
                   "md5": match.group(1)}


def toignore(filename):
    if filter(lambda patt: fnmatch.fnmatch(filename, patt), ignores):
        return True
    return False


def master_list(start):
    # Collect all files under start (follow directory symbolic links).
    for root, dirs, files in os.walk(start, followlinks=True):
        if toignore(root):
            continue
        for fname in files:
            fname = op.join(root, fname)
            if toignore(fname):
                continue
            # Take care of symbolic links pointing to a file.
            try:
                if op.islink(fname):
                        # We are using this command to check whether the link
                        # is not broken.
                        os.stat(fname)
                        fname = os.readlink(fname)
                        # os.readlink() may or maynot return absolute path. If

                        if not op.isabs(fname):
                            fname = op.join(root, fname)
                yield op.relpath(fname, start)
            except OSError, e:
                if e.errno == errno.ENOENT:
                    log('BROKEN: %s' % fname)
                else:
                    raise e


def calculateUID(filepath):
    """Calculate MD5 for an MP3 excluding ID3v1 and ID3v2 tags if
    present. See www.id3.org for tag format specifications."""
    f = open(filepath, "rb")
    # Detect ID3v1 tag if present
    finish = os.stat(filepath).st_size
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
        footer = flags & (1 << 4)
        # Size of tag body synchsafe integer (6-9)
        bs = struct.unpack("BBBB", f.read(4))
        bodysize = (bs[0] << 21) + (bs[1] << 14) + (bs[2] << 7) + bs[3]
        # Seek to end of ID3v2 tag
        f.seek(bodysize, 1)
        if footer:
            f.seek(10, 1)
        # Start of rest of the file
        start = f.tell()
    # Calculate MD5 using stuff between tags
    f.seek(start)
    h = md5.new()
    h.update(f.read(finish - start))
    f.close()
    return h.hexdigest()


def calcsum(filepath, mp3mode):
    """Return md5 checksum for a file. Uses the tag-skipping algorithm
    for .mp3 files if in mp3mode."""
    if mp3mode and filepath.endswith(".mp3"):
        return calculateUID(filepath)
    h = md5.new()
    try:
        f = open(filepath, "rb")
        s = f.read(1048576)
        while s != "":
            h.update(s)
            s = f.read(1048576)
        f.close()
        return h.hexdigest()
    except IOError:
        log("BROKEN: %s" % filepath)
        return -1


def writesums(root, checksums):
    """Given a list of (filename,md5) in checksums, write them to
    filepath in md5sum format sorted by filename, with a #md5dir
    header"""
    pathname = hashfile if op.isabs(hashfile) else op.join(root, hashfile)
    f = open(pathname, "w")
    f.write("#md5dir %s\n" % root)
    for fname, md5 in sorted(checksums, key=lambda x: x[0]):
        f.write("%s  %s\n" % (md5, fname))
    f.close()


def makesums(root):
    """Creates an md5sum file in the location specified by the global
    variable hashfile."""
    progress("Creating md5sum file.")
    fileno = 0
    pathname = hashfile if op.isabs(hashfile) else op.join(root, hashfile)
    with open(pathname, "w") as fp:
        for fname in master_list(root):
            if fileno % 1000 == 0:
                progress("Computing md5, %d files analyzed." % fileno)
            newhash = calcsum(op.join(root, fname), mp3mode)
            if newhash != -1:
                fp.write("%s  %s\n" % (newhash, fname))
                fileno += 1
    progress("Sorting the md5sum file.")
    subprocess.call(["sort", "-k", "2", "-o", pathname, pathname])
    progress("Finished sorting the md5sum file.")


def getignores(filepath):
    with open(filepath, 'r') as f:
        doc = yaml.load(f)
    return doc["ignore"]


def compare(path1, path2, dir):
    """Compares two md5sum files and writes the differences to the
    relevant output."""

    # Helper functions for iterating, which returns -1 if there
    # are no elements left.
    def neckst(item):
        return next(item, -1)

    progress("Comparing the md5sum files.")
    confirmed = 0
    changed = 0
    added = 0
    deleted = 0
    old = getDictionary(path1)
    new = getDictionary(path2)
    dictold = neckst(old)
    dictnew = neckst(new)
    while True:
        if dictold == -1 or dictnew == -1:
            break
        # Match. Both proceed to next element.
        pathold = dictold["file"]
        pathnew = dictnew["file"]
        if toignore(pathold):
            dictold = neckst(old)
            continue
        if toignore(pathnew):
            dictnew = neckst(new)
            continue
        if pathold == pathnew:
            if dictold["md5"] != dictnew["md5"]:
                log("CHANGED: %s" % pathold)
                changed += 1
            else:
                confirmed += 1
            dictold = neckst(old)
            dictnew = neckst(new)
        # File got deleted. Old proceed to next element.
        elif pathold < pathnew:
            log("DELETED: %s" % pathold)
            deleted += 1
            dictold = neckst(old)
        # File got added. New proceed to next element.
        else:
            log("ADDED: %s" % pathnew)
            added += 1
            dictnew = neckst(new)

    if dictold == -1:
        dictnew = neckst(new)
        while dictnew != -1:
            log("ADDED: %s" % dictnew["file"])
            added += 1
            dictnew = neckst(new)
    elif dictnew == -1:
        dictold = neckst(old)
        while dictold != -1:
            log("ADDED: %s" % dictold["file"])
            added += 1
            dictold = neckst(old)
    log("STATUS: confirmed %d added %d deleted %d changed %d" % (
        confirmed, added, deleted, changed))


def progress(message):
    if verbose:
        print "PROGRESS: %s" % message


if __name__ == "__main__":
    global output
    global mp3mode
    global suppress_changes
    dirs = []

    # Parse command-line options
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--comparefiles", nargs=2)
    parser.add_argument("-3", "--mp3", action="store_true")
    #TODO: check for help before it was print __doc__ sys.exit(0)
    parser.add_argument("-o", "--output", type=argparse.FileType("w"),
                        default=sys.stdout)
    parser.add_argument("-t", "--twodir", action="store_true")
    parser.add_argument("--suppress_changes", action="store_true")
    # TODO: timeit.default_timer()
    parser.add_argument("--time", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("dirs", nargs="*")

    # TODO the variable is called ignores, function getignores
    parser.add_argument("-i", "--ignore")

    args = parser.parse_args()
    
    output = args.output
    mp3mode = args.mp3
    suppress_changes = args.suppress_changes

    # Compare two md5sum files.
    if args.comparefiles:
        file1 = args.comparefiles[0]
        file2 = args.comparefiles[1]
        if not op.isfile(file1) or not op.isfile(file2):
            print "Exiting because the arguments are not files."
            sys.exit(0)
        compare(file1, file2, op.abspath(op.dirname(file1)))
    # All other options use the dirs command line argument.
    else:
        for item in args.dirs:
            pair = item.split(":")
            directory = {"directory": pair[0]}
            directory["file"] = pair[1] if len(pair) == 2 else None
            dirs.append(directory)

        # Compare two directories
        if args.twodir:
            if len(dirs) != 2:
                print "Two arguments expected."
                sys.exit(0)
            arg1 = dirs[0]
            arg2 = dirs[1]
            if not op.isdir(arg1["directory"]) or not op.isdir(arg2["directory"]):
                print "Exiting because arguments are not directory pathnames."
                sys.exit()
            file1 = arg1["file"] or tempfile.NamedTemporaryFile(delete=False).name
            file2 = arg2["file"] or tempfile.NamedTemporaryFile(delete=False).name
            hashfile = op.abspath(file1)
            makesums(arg1["directory"])
            hashfile = op.abspath(file2)
            makesums(arg2["directory"])
            compare(file1, file2, op.abspath(arg1["directory"]))

        # Analyze the given directories.
        else:
            # Treat each argument separately
            for arg in dirs:
                start = arg["directory"]
                if not op.isdir(start):
                    print "Argument %s is not a directory" % start
                    continue
                if arg["file"]:
                    hashfile = op.abspath(arg["file"])
                else:
                    op.join(op.abspath(start), hashfile)

                # Copy the content of md5sum into a temporary file.
                file1 = tempfile.NamedTemporaryFile(delete=False)
                if op.isfile(hashfile):
                    with open(hashfile, "r") as fp:
                        shutil.copyfileobj(fp, file1)
                file1.close()
                # Update the hashfile.
                makesums(start)
                # Compare the files.
                compare(file1.name, hashfile, op.abspath(start))
                os.unlink(file1.name)

    if time:
        total = timeit.default_timer() - beginning
        print "%.5f" % total
