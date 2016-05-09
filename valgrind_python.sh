#!/bin/bash

valgrind --tool=memcheck --leak-check=full --num-callers=30 --suppressions=valgrind-python.supp python3.5 $1.py