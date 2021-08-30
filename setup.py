# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

from setuptools import setup, find_packages
from pathlib import Path
import os


def get_glob(path, patterns, excludes=tuple()):
    lst = [str(p.relative_to(path)) for pattern in patterns for p in Path(path).glob(pattern)]
    return [s for s in lst if all(ex not in s for ex in excludes)]


here = os.path.abspath(os.path.dirname(__file__))

# Get the core dependencies and installs
with open(os.path.join(here, "requirements.txt"), encoding="utf-8") as f:
    all_reqs = [s.strip() for s in f.readlines()]


install_requires = [x.strip() for x in all_reqs if "git+" not in x]
dependency_links = [x.strip().replace("git+", "") for x in all_reqs if x.startswith("git+")]

# Get extra dependencies
dev_reqs = []
if os.path.exists(os.path.join(here, "requirements_dev.txt")):
    with open(os.path.join(here, "requirements_dev.txt"), encoding="utf-8") as f:
        dev_reqs = [s.strip() for s in f.readlines()]

packages = find_packages(exclude=["docs*", "test*"])

setup(
    description="Plugin for QGIS to connect to the HERE XYZ Hub API and HERE Platform IML API",
    # scripts=[],
    packages=packages,
    include_package_data=True,
    package_data={packages[0]: get_glob(packages[0], ["metadata.txt", "**/*.ui", "**/*.xml"], [])},
    install_requires=install_requires,
    dependency_links=dependency_links,
    extras_require={"dev": dev_reqs},
)
