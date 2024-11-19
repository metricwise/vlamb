#!/bin/sh -e
usage() {
    echo "Usage: $0 [-h]" 1>&2;
    echo "  -h Display this help message." 1>&2;
    exit 1;
}

while getopts "hi" opt; do
  case $opt in
    *)
      usage
      ;;
  esac
done

PYTHON=python3.9
$PYTHON -m unittest
