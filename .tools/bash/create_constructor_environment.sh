#!/usr/bin/env bash
# Create the conda environment used for constructor builds.
set -euo pipefail

conda create -y -n "${CONSTRUCTOR_ENV:?}" -c conda-forge -c defaults python=3.11 constructor
