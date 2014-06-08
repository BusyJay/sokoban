#!/bin/bash
# docs build script
lang=python2
wd=`pwd`
while [ $# -gt 0 ]; do
	case "$1" in
		-h|--help)
			echo "$0 [options] command"
			echo ""
			echo "options:"
			echo "-h, --help          show help"
			echo "-l, --lang          project language, like python2, python3, etc, default is python2"
			exit 0
			;;
		-l|--lang)
			if [ $# -gt 1 ]; then
				lang=$2
				shift
			else
				echo "language expected after $1!"
				exit 1
			fi
			shift
			;;
		-w|--work-directory)
			if [ $# -gt 1 ]; then
				wd="$2"
				shift
			else
				echo "path expected after $1!"
				exit 1
			fi
			shift
			;;
		*)
			break
			;;
	esac
done
case "$lang" in
	python2)
		source ~/pyvenv2/bin/activate
		;;
	python3)
		source ~/pyvenv3/bin/activate
		;;
	*)
		echo "Unrecognized language!"
		exit 1
		;;
esac
cd "$wd"
$@
