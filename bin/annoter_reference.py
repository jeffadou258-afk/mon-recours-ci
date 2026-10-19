# -*- coding: utf-8 -*-
"""Consigne une note datée et sourcée sur une référence du corpus.

    python3 bin/annoter_reference.py REF-B6FE04121ED1 "texte de la note" https://source
"""

import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from core import base  # noqa: E402


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 3:
        print(__doc__)
        return 2
    print(base.annoter_reference(argv[0], argv[1], argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
