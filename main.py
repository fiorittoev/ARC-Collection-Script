"""
Runs all scripts in necessary order

Evan Fioritto
"""

import downloadscript
import verifyscript
import analyzeresults
import copyfoundfirms
import OCRscript


def main():
    downloadscript.main()
    verifyscript.main()
    analyzeresults.main()
    copyfoundfirms.main()
    OCRscript.main()


if __name__ == "__main__":
    main()
