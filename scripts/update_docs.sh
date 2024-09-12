#!/usr/bin/env bash

cd documentation || exit 1
make html
cd .. || exit 1
./commit.sh