#!/bin/sh
# automatically synchonize changes to /var/lib/sokoban/sokoban/

if [ ! `which inotifywait 2>/dev/null` ]; then
	echo inotifywait is missing! Please make sure inotify-tools is installed.
	exit 1
fi
if [ ! `which rsync 2>/dev/null` ]; then
	echo rsync is missing!
	exit 1
fi
if [ "$(id -u)" != "0" ]; then
	echo You have better run it as root. Or you may not be allowed to access files.
fi

srcdir="$( cd ../../sokoban; pwd -P )/"
disdir=/var/lib/sokoban/sokoban/

# initial sync
rsync -avz --delete "$srcdir" "$disdir"

inotifywait -r -q -m "$srcdir" -e modify,delete,create,attrib | while read line
do
	rsync -avz --delete "$srcdir" "$disdir"
done

