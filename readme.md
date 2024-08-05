# ARC Collection Script

Written by Evan Fioritto, May to August 2024  
For MSU College of Business - Management Department


## Requirements
- `alive-progress==3.1.5`
- `glib==1.0.0`
- `gobject==0.1.0`
- icgauge (my abridged version) @ https://drive.google.com/drive/folders/1ym4tD91R-KLLtsqS1h12otNivBDugHOv, download into root project folder (/ARC-COLLECTION-SCRIPT)
- `httplib2==0.22.0`
- `nltk==3.8.1`
- `numpy==1.26.4`
- `scikit-learn==1.5.1`
- `panda==0.3.1`
- `pango==0.0.1`
- `pycairo==1.26.1`
- `PyMuPDF==1.24.9`
- `PyPDF2==3.0.1`
- `python-doctr==0.8.1`
- `thefuzz==0.22.1`
- `selenium==4.23.1`
- `stanfordcorenlp==3.9.1.1`
- `torchvision==0.19.0`
-`webdriver-manager==4.0.2`

## CSV Explanations
- **ziptracker.csv**: Information scraped from each search, along with the status of the bulk download. Of format: [Global Company Key, Company Name, Page Found On]
- **filestracker.csv**: Information regarding every successfully downloaded file (not verified). Of format: [Global Company Key, Company Name, Row Number, Page Number, Filing Date, Doctype]
- **metadata.csv**: Extrapolation off `filestracker.csv` and `ziptracker.csv`, pairing each entry with its location on disk. Of format: [Filename, GVKey, HH Name, Mergent Name, Year, Date, DocType, Parent Zip]
- **matching.csv**: Relation of `filestracker.csv` and `ziptracker.csv` to `ARC_missing.csv`. Of format: [GVKey, Company Name, Year, Data Date, Status, Year Match, File Count]
- **found_firms.csv**: Collection of all desired entries with a GVKey and year match with at least one file. Of format: [GVKey, Company Name, Year, Data Date, File Count]
- **missing_firms.csv**: Collection of all desired entries either not on Mergent or not with a year match. Of format: [GVKey, Company Name, Year, Data Date, Status]
- **confirmations.csv**: Basic OCR results validating actual contents of PDFs derived from `metadata.csv`. [Path, GVKey, HH Name, Mergent Name, Year, Doctype Confirmed, Name Confirmed, Year Confirmed, Index in missing.csv]
- **complexities.csv**: Semantic complexities of files ran through OCRscript. [GVKey, HH name, Mergent Year]


## Folder Explanations
- **/zips**: zips downloaded from mergent by `downloadscript.py`
- **/folders**: all zips unzipped, populated in `verifyscript.py`
- **/trackers**: csv files containing information about all zips and files downloaded by `downloadscript.py`
- **/matched_folders**: folders with a proved correlation to `ARC_mising.csv`
- **/sample_data**: folder containing json training data `toy.json` for icgauge to compare against in `OCRscript.py`, will run significantly slower on machines will low specifications
- **/extracted_text**: folder containing text extractions for files passed through OCRscript.py

# Other
- **lastindex.txt**: the index of unique firm last reached in `downloadscript.py` or `OCRscript.py`, used to store globally across runs
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
4. **Copyfoundfirms.py**: Copies all downloaded files correlated with an entry in `ARC_HH_OK_AK_missing.csv` to the `matched_folders` directory.
5. **OCRscript.py**: Uses docTr and icgauge packages to extract text and weigh semantic complexity for each file specified from `found_firms.csv`

## Running the Scripts
Running `main.py` will execute all scripts in order. If one errs, they are all fit to be rerun individually and repeatedly.
