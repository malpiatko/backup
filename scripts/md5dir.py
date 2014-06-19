#!/usr/bin/python

"""md5dir -- Recursive MD5 checksums for files which move around

Usage: md5dir [options] [directories]

Without options it writes an 'md5sum' file in each subdirectory
containing MD5 checksums for that directories files.

A file which has been both changed and renamed since the last run
shows up as DELETED followed by ADDED.

The md5sum files are read and written in the format of the GNU md5sum
utility (http://www.gnu.org/software/textutils/textutils.html).

-3/--mp3
  Enable MP3 mode: for files ending in .mp3, calculate a checksum
  which skips ID3v1 and ID3v2 tags.  This checksum differs from the
  normal one which is compatible with GNU md5sum.  The md5sum file is
  tagged so that md5dir will in future always use MP3 mode for the
  directory.  Consider using mp3md5.py instead, which keeps this
  tag-skipping checksum in the ID3v2 tag as a Unique File ID.

-c/--confirm
  Additionally output CONFIRMED lines for unchanged files.

-f X/--file=X
  Use X as the name of the MD5 file instead of the default of md5sum
  (edit source to change the default).

-h/--help
  Output this message then exit.

-l/--license
  Output the license terms for md5dir then exit.

-m/--master
  Enable master mode which creates a 'master' md5sum file for the
  entire hierarchy under each argument (instead of each subdir having
  its own md5sum).  Note that per-directory md5sum files are removed
  in the process.  The md5sum file is tagged so md5dir will in future
  always use master mode for the directory.

-n/--nocheck
  Only look for RENAMED/ADDED/DELETED files.  Generally fast for
  subsequent runs since it does not check for changes to existing
  checksums (and ignores any --confirm/--update options).

-q/--quiet
  Do not produce any output (just update the md5sum files).

-r/--remove
  Ignore other options and remove any md5sum files found under the
  arguments (outputs REMOVING lines).

-u/--update
  Output UPDATED lines and update checksums for altered files (instead
  of outputting CHANGED lines). After updating, such files should be
  CONFIRMED on subsequent runs.

Copyright 2007 G raham P oulter
"""

__copyright__ = "2007 G raham P oulter"
__author__ = "G raham P oulter"
__license__ = """This program is free software: you can redistribute it and/or
modify it under the terms of the GNU General Public License as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>."""

from getopt import getopt
import md5
import os
import os.path as op
import re
import struct
import sys
import magic
import errno

hashfile = "md5sum" # Default name for checksum file 
check = True        # Whether to check for changes
confirm = False     # Whether to suppress CONFIRMED lines
master = False      # Whether to use master mode vs per-directory checksums
quiet = False       # Whether to suppress all output
remove = False      # Whether to work in 'REMOVING md5sum' mode
update = False      # Whether to update changed checksums
mp3mode = False     # Whether to use tag-skipping checksum for MP3s
changelog = "md5changes.txt" # Names of changed files

# Regular expression for lines in GNU md5sum file
md5line = re.compile(r"^([0-9a-f]{32}) [\ \*](.*)$")

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

def readsums(filepath):
    """Yield (md5, filename) pairs from a checksum file

    @param filepath: Name of file containing checksums
    """
    if not op.isfile(hashfile):
        return
    for line in open(filepath, "r").readlines():
        match = md5line.match(line.rstrip(""))
        # Skip non-md5sum lines
        if not match:
            continue
        yield match.group(1), match.group(2)

def writesums(filepath, checksums, master, mp3mode):
    """Given a list of (filename,md5) in checksums, write them to
    filepath in md5sum format sorted by filename, with a #md5dir
    header"""
    f = open(filepath, "w")
    f.write("#md5dir")
    if master:
        f.write(" master")
    if mp3mode:
        f.write(" mp3mode")
    f.write("\n")
    for fname, md5 in sorted(checksums, key=lambda x:x[0]):
        f.write("%s  %s\n" % (md5, fname))
    f.close()

def hashflags(dirpath):
    """If the directory holds a hashfile starting with #md5dir, return
    a list of the remaining words on that line (should be 'master' and
    'mp3mode' for now)"""
    hpath = op.join(dirpath, hashfile)
    if not op.isfile(hpath):
        return []
    f = open(hpath, "r")
    s = f.readline().split()
    if s[0] != "#md5dir":
        return []
    else:
        return s[1:]

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


def log(msg, filename):
    """Output a log message"""
    if not quiet:
        print "%-10s%s" % (msg, filename)

def md5dir(root, filenames, master):
    """Write an md5sum file in root for the list of filenames
    (specified relative to root).
    """
    # Decide whether to use mp3mode
    use_mp3mode = mp3mode
    if "mp3mode" in hashflags(root):
        use_mp3mode = True

    # Change directory
    oldcwd = os.getcwd()
    os.chdir(root)
    filenames.sort()

    # present is used to detect case changed files on Windows
    checksums = {} # Map fname->md5
    present = {}   # Map md5->fname for present files 
    deleted = {}   # Map md5->fname for deleted files

    changed = []   # Changed files
    added = []     # Added files
    confirmed = [] # Confirmed files
    renamed = []   # Renamed files as (old,new) pairs

    # Read checksums from hashfile
    for md5, fname in readsums(hashfile):
        if op.isfile(fname):
            checksums[fname] = md5
            present[md5] = fname
        else:
            deleted[md5] = fname

    # Read files from directory
    newhash = None
    for fname in filenames:
        if fname == hashfile:
            continue
        newhash = calcsum(fname, use_mp3mode)
        if fname not in checksums:
            checksums[fname] = newhash
            if newhash in deleted:
                renamed.append((deleted[newhash], fname))
                del deleted[newhash]
            elif newhash in present:
                # Identical files with case-differing names implies
                # a renaming on a case-insensitive filesystem
                oldname = present[newhash]
                if oldname.lower() == fname.lower():
                    renamed.append((oldname, fname))
                    del checksums[oldname]
                    checksums[fname] = newhash
            else:
                added.append(fname)
        elif check:
            if checksums[fname] == newhash:
                confirmed.append(fname)
            else:
                changed.append(fname)
                if update:
                    checksums[fname] = newhash
    # End the line of progress dots
    if newhash and not quiet:
        sys.stdout.write("\n")

    # Log all changes
    if confirm:
        for fname in confirmed:
            log("CONFIRMED", op.join(root,fname))
    for old, new in renamed:
        log("RENAMED", "%s: %s --> %s" % (root,old,new))
    for fname in added:
        log("ADDED", op.join(root,fname))
    for fname in sorted(deleted.itervalues()):
        log("DELETED", op.join(root,fname))
    for fname in changed:
        if update:
            log("UPDATED", op.join(root,fname))
        else:
            log("CHANGED", op.join(root,fname))
    log("LOCATION", root)
    log("STATUS", "confirmed %d renamed %d added %d deleted %d changed %d" % (
        len(confirmed), len(renamed), len(added), len(deleted), len(changed)))
    if not quiet:
        sys.stdout.write("\n")

    # Write list of changed files, removed on update
    if changed and not update:
        logfile = open(changelog, "a")
        try:
            for fname in changed:
                logfile.write(op.join(root, fname)+"\n")
        finally:
            logfile.close()
    if update and op.isfile(changelog):
        print changelog
        os.remove(changelog)
        
    # Write hashfile if necessary
    if renamed or added or deleted or changed:
        if checksums:
            try:
                writesums(hashfile, checksums.iteritems(), master, use_mp3mode)
            except IOError:
                log("WARNING", "Error writing to %s" % op.join(root, hashfile))
        elif op.isfile(hashfile):
            os.remove(hashfile)
            
    os.chdir(oldcwd)

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
    
if __name__ == "__main__":
    # Parse command-line options
    optlist, args = getopt(
        sys.argv[1:], "3cf:hlmnqru",
        ["mp3","confirm", "file=", "help", "license", "master", "nocheck", "quiet", "remove", "update"])
    for opt, value in optlist:
        if opt in ["-3", "--mp3"]:
            mp3mode = True
        elif opt in ["-c", "--confirm"]:
            confirm = True
        elif opt in ["-f", "--file"]:
            hashfile = value
        elif opt in ["-h","--help"]:
            print __doc__
            sys.exit(0)
        elif opt in ["-l", "--license"]:
            print license
            sys.exit(0)
        elif opt in ["-m", "--master"]:
            master = True
        elif opt in ["-n", "--nocheck"]:
            check = False
        elif opt in ["-q", "--quiet"]:
            quiet = True
        elif opt in ["-r", "--remove"]:
            remove = True
        elif opt in ["-u", "--update"]:
            update = True
    if len(args) == 0:
        log("WARNING", "Exiting because no directories given (use -h for help)")
        sys.exit(0)

    # Remove old changelog
    if op.exists(changelog):
        os.remove(changelog)
    
    # Treat each argument separately
    for start in args:
        if not op.isdir(start):
            log("WARNING", "Argument %s is not a directory" % start)
            continue

        # Remove checksum files
        if remove:
            for root, dirs, files in os.walk(start):
                dirs.sort()
                files.sort()
                for fname in files:
                    if fname == hashfile:
                        log("REMOVING", op.join(root,fname))
                        os.remove(op.join(root,fname))

        # Master checksum
        elif master:
            md5dir(start, master_list(start), master=True)

        # Per-directory checksum
        else:
            for root, dirs, files in os.walk(start):
                dirs.sort()
                files.sort()
                if "master" in hashflags(root):
                    del dirs[:]
                    md5dir(root, master_list(root), master=True)
                else:
                    md5dir(root, files, master=False)