# ARC Collection Script

Written by Evan Fioritto, May to August 2024  
For MSU College of Business - Management Department

## Requirements
- `selenium`
- `alive-progress`
- `fitz`
- `pymupdf`
- `pypdf2`
- `getpass`
- `pandas`
- `docTR`
- `torch`
- Evan's abridged icgauge package

## CSV Explanations
- **ziptracker.csv**: Information scraped from each search, along with the status of the bulk download.
- **filestracker.csv**: Information regarding every successfully downloaded file (not verified).
- **metadata.csv**: Extrapolation off `filestracker.csv` and `ziptracker.csv`, pairing each entry with its location on disk.
- **matching.csv**: Relation of `filestracker.csv` and `ziptracker.csv` to `ARC_missing.csv`.
- **found_firms.csv**: Collection of all desired entries with a GVKey and year match with at least one file.
- **missing_firms.csv**: Collection of all desired entries either not on Mergent or not with a year match.
- **confirmations.csv**: Basic OCR results validating actual contents of PDFs derived from `metadata.csv`.

## Folder Explanations
- **/zips**: zips downloaded from mergent by `downloadscript.py`
- **/folders**: all zips unzipped, populated in `verifyscript.py`
- **/trackers**: csv files containing information about all zips and files downloaded by `downloadscript.py`
- **/matched_folders**: folders with a proved correlation to `ARC_mising.csv`
- **/sample_data**: folder containing json training data `toy.json` for icgauge to compare against in `OCRscript.py`

# Other
- **lastindex.txt**: the index of unique firm last reached in `downloadscript.py`, used to store globally across runs
- **temp.json**: file to hold NLP parsed data for icgauge validation in `OCRscript.py`

## Abbreviations
- **OK**: A GVKey match
- **Y**: A year match
- **N**: No year match
- **NA**: No GVKey Match
- **TL**: zip skipped due to being over 1.8 GB
- **SK**: zip skipped due to bug in webpage processing

## Process Overview
1. **Downloadscript.py**: Runs the initial bulk download based off entries in `ARC_HH_OK_AK_missing.csv`, storing information about each search and successful download in `ziptracker.csv` and `filestracker.csv`.
2. **Verifyscript.py**: Details what information we believe the files hold in `metadata.csv`, as well as rerunning a secondary search for skipped or missing files using functions from `downloadscript.py`. Basic fuzzy matching is conducted to verify the contents of PDFs.
3. **Analyzeresults.py**: Uses data stored in `matching.csv` from `verifyscript.py` to produce statistics as well as store in separate files `found_firms.csv` and `missing_firms.csv`.
4. **Copy_found_firms.py**: Copies all downloaded files correlated with an entry in `ARC_HH_OK_AK_missing.csv` to the `matched_folders` directory.
5. **OCRscript.py**: Uses docTr and icgauge packages to extract text and weigh semantic complexity for each file specified from `found_firms.csv`

## Running the Scripts
Running `main.py` will execute all scripts in order. If one errs, they are all fit to be rerun individually and repeatedly.
