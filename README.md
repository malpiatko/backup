Backup integrity checker
=========

The purpose of this project is to create a tool which checks for changes in files on the system and informs
the owners of the directories about the changes.

Directory comparison tool.
----
You can use this tool for creating a file with md5 sums for each file present in a chosen directory. Using this file as a "state" of the directory you can compare current version of the directory with a previous one. To do this run the md5dir script with the following command:

 `python scripts/md5dir.py [options] [directory:mdsumpath]`

 Depending on the options the command can do the following:

 * without options - it creates an md5sum file for each of the given directories, compares it with the previous version of the file and replaces it. If the "md5sumpath" is given it is used as the path of the md5sum file, otherwise "directory/md5sum" is used.
 * `compare` - compares two previously created md5sum files.
 - `two_dir` - compares two directories. Saves the hashfiles of the directories only if explicitely specified my giving mdsumpath.

Ignoring files
------
 You can also specify files and directories that you would like to ignore in the analysis by using the `ignore` flag and giving it a path to a YAML file. The file should have the following structure:
`ignore:
	- "pathname"
	- "pathname2"
	- ...`
Where the pathnames can use Unix shell-style wildcards.
An example file can be found under "example/config.yaml"

Informing owners
-----
This option is currently not implemented

TODO
----
* the flag for hashing mp3 files was never tested
* using the tool to inform owners of the files, does not work at the moment
* currently only the "md5dir.py" file is suitable for usage.