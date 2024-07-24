
ARC-Collection-Script
Written by Evan Fioritto, 2024 
For MSU College of Business - Management Department

Requirements:
    selenium
    alive-progress
    fitz
    pymupdf
    pypdf2
    getpass
    pandas

CSV explanations:   
    ziptracker.csv - information scraped from each search, along with the status of the bulk download
    filestracker.csv - information regarding every successfully downloaded file (not verified)
    metadata.csv - extrapolation off filestracker.csv and ziptracker.csv, pairing each entry with its location on disk
    matching.csv - relation of filestracker.csv and ziptracker.csv to ARC_missing.csv
    found_firms.csv - collection of all desired entries with a GVKey and year match with at least one file
    missing_firms.csv - collection of all desired entries either not on mergent or not with a year match
    confirmations.csv - basic OCR results validating actual contents of pdf's derived from metadata.csv

Some helpful abbreviations:
    OK - A GVKey match
    Y - A year match
    N - No year match
    NA - No GVKey Match

The process operates as follows:
    1. Downloadscript.py runs the initial bulk download based off of entries in ARC_HH_OK_AK_missing.csv, storing information about each search and sucessful download in ziptracker and filestracker
    2. Verifyscript.py details what information we believe the files hold in metadata.csv, as well as reruning a secondary search for skipped or missing files using functions from downloadscript. basic fuzzymatching conducted to verify contents of pdf
    3. Analyzeresults.py uses data stored in matching.csv from verifyscript to produce staticstics as well as store in seperate files found and missing firms.
    4. Copy_found_firms.py copys all downloaded files correlated with an entry in ARC_HH_OK_AK_missing.csv to the matched_folders directory

Running main.py will run all scripts in order, if one errs, they are all fit to be reran individually and repeatedly.