# -*- coding: utf-8 -*-
###############################################################################
#
# Copyright (c) 2019 HERE Europe B.V.
#
# SPDX-License-Identifier: MIT
# License-Filename: LICENSE
#
###############################################################################

import os
import zipfile
import sys
if __name__ == "__main__":
    if len(sys.argv) -1 < 2:
        sys.exit("Missing arguments. Exiting..\nSyntax: in_folder out_zip")
    path, outfile = sys.argv[1:3]
    lst_files = [os.path.join(root, f) for root, dirs, files in os.walk(path) for f in files]
    if not len(lst_files) > 0:
        sys.exit("Empty or invalid input folder: %s"%path)
    with zipfile.ZipFile(outfile, "w", zipfile.ZIP_DEFLATED) as fzip:
        for file in lst_files:
            fzip.write(file)