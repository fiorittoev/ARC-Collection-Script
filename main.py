"""
Runs all scripts in necessary order

Evan Fioritto
"""

import downloadscript
import verifyscript
import analyzeresults
import copy_found_firms


def main():
    downloadscript.main()
    verifyscript.main()
    analyzeresults.main()
    copy_found_firms.main()


if __name__ == "__main__":
    main()
