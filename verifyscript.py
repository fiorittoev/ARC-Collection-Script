"""
Creates a metadata csv based on two trackers and zips in their respective folders, unzips each zip, 
then matches each file name to what data it should be holding and tracks within the metadata.csv

Metadata - extrapolation off filestracker, pairing each entry with its location on disk
Matching - relation of filestracker and zipreader to ARC_missing.csv

requirements:
pip insall alive-progress
By Evan Fioritto
"""

import downloadscript
import os
import zipfile
import csv
import fitz
import pymupdf
import pandas as pd
from PyPDF2.errors import PdfReadError
from rapidfuzz import fuzz
from alive_progress import alive_bar
from getpass import getpass

zip_directory = "./zips"
folder_directory = "./folders"
tracker_directory = "./trackers"


def InitializeFiles():
    """
    Creates folders trackers and zips folder if ther do not already exist

    Return: void
    """
    pymupdf.TOOLS.set_icc(False)

    dirs = [zip_directory, folder_directory, tracker_directory]

    # Create directories
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

    # Write headers
    with open("metadata.csv", "w", newline="") as csvfile:
        w = csv.writer(csvfile)
        w.writerow(
            [
                "Filename",
                "GVKey",
                "HH Name",
                "Mergent Name",
                "Year",
                "Date",
                "DocType",
                "Parent Zip",
            ]
        )

    with open("confirmations.csv", "w", newline="") as csvfile:
        w = csv.writer(csvfile)
        w.writerow(
            [
                "Path",
                "GVKey",
                "HH Name",
                "Mergent Name",
                "Year",
                "Doctype Confirmed",
                "Name Confirmed",
                "Year Confirmed",
                "Index in missing.csv",
            ]
        )


def UnzipFiles():
    """
    Unzips all files in zips to folders

    Return: void
    """

    # Create Progress bar
    with alive_bar(len(os.listdir(zip_directory))) as bar:
        bar.text("Unzipping")
        # Iterate through zips folder
        for filename in os.listdir(zip_directory):

            # Create new subfolder based on filename
            path = os.path.join(
                folder_directory, filename[:-4]
            )  # indexing up to -4 gets string except for ".zip" extension
            if not os.path.exists(path):
                os.mkdir(path)  # create subfolder
                # Extract
                f = os.path.join(zip_directory, filename)  # Get path of each zip

                # If possible, extract the zip
                try:
                    with zipfile.ZipFile(f, "r") as zip_ref:
                        zip_ref.extractall(path)
                except zipfile.BadZipFile:
                    continue
                except zipfile.zlib.error:
                    continue
            bar()


def GetFileInfo(key, zip_page, row_number):
    """
    uses key, page of zip, and file row number to return file name and path

    Keyword arguments:
    key -- company gvkey, derived from ziptracker
    zip_page -- page # that the zip was downloaded from, derived from ziptracker
    row_number -- row of the file we want information from, derived from filestracker
    Return: [0] is file name, the string given by mergent, [1] is the local path to the file
    """

    # Iterate through each extracted zip
    for folder_name in os.listdir(folder_directory):

        folder_name_list = folder_name.split(
            "_"
        )  # Split path to list to allow indexing

        # account for altreports
        if folder_name_list[-1] == "altreport":
            file_page = folder_name_list[-2]
        else:
            file_page = folder_name_list[-1]

        if (
            key == folder_name_list[0] and zip_page == file_page
        ):  # Identifyin information for the folder is its gvkey and download page

            folder_path = os.path.join(folder_directory, folder_name)

            # Iterate through files in folder
            for file_name in os.listdir(folder_path):

                file_number = file_name[:-4].strip()[-1]  # Grab row of file from path
                if file_number == row_number:  # Find target

                    file_path = os.path.join(folder_path, file_name)

                    return file_name, file_path

    return 0, 0  # If iteration is complete with no matches, return 0s


def OpenTrackers():
    """
    Iterate through both trackers, grabbing neccesary data from each for appendage into metadata csv

    Return: void
    """

    # Too long or not available
    invalids = ["TL", "NA", "SK"]

    # Open both trackers
    with open(tracker_directory + "/ziptracker.csv", newline="") as csvfile1:

        zip_reader = csv.reader(csvfile1)
        used_files = []
        next(zip_reader)  # Skip header

        # Use panda to get a length for csv
        num_lines = len(pd.read_csv(tracker_directory + "/ziptracker.csv"))

        with alive_bar(num_lines) as bar:  # Progress bar
            bar.text("Pulling Metadata")

            for zip in zip_reader:
                key = zip[0]
                name_HH = zip[1]
                zip_page = zip[2]  # Could be "TL","NA","SK" or int value

                if zip_page not in invalids:

                    with open(
                        tracker_directory + "/filestracker.csv", newline=""
                    ) as csvfile2:
                        file_reader = csv.reader(csvfile2)
                        next(file_reader)  # Skip header

                        for file in file_reader:
                            file_key = file[0]
                            name_mergent = file[1]
                            row_number = file[2]
                            file_date = file[4]
                            doctype = file[5]

                            if file_key == key:
                                file_info = GetFileInfo(key, zip_page, row_number)

                                if (file_info[0] and file_info[1]) and (
                                    file_info[0] not in used_files
                                ):
                                    used_files.append(
                                        file_info[0]
                                    )  # Files must be unique

                                    MetadataAppend(
                                        file_info[0],
                                        key,
                                        name_HH,
                                        name_mergent,
                                        file_date[-4:],
                                        file_date,
                                        doctype,
                                        file_info[1],
                                    )
                bar()


def MetadataAppend(filename, key, name_HH, name_mergent, year, date, doctype, path):
    """
    Appends parameters to metadata.csv

    filename -- string generated by mergent
    key -- gvkey for company
    name_HH -- name from missing.csv
    name_mergent -- name from file that was downloaded
    year -- filing year
    date -- filing date
    doctype -- type of document
    path -- location of filename on disk
    Return: void
    """
    temp = [
        str(filename),
        str(key),
        str(name_HH),
        str(name_mergent),
        str(year),
        str(date),
        str(doctype),
        str(path),
    ]
    with open("metadata.csv", "r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            if row == temp:  # If row exists we will not rewrite
                return 0

    with open("metadata.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(temp)


def ValidateMatches():
    """
    Iterate through ARC_HH_OK_AR_missing.csv and account for statuses of desired files

    Return: void
    """

    with open("matching.csv", "w", newline="") as csvfile:
        w = csv.writer(csvfile)
        w.writerow(
            [
                "GVKey",
                "Company Name",
                "Year",
                "Data Date",
                "Status",
                "Year Match",
                "File Count",
            ]
        )

    valid_doctypes = ["10K or Int'l Equivalent", "Annual/10K Report", "Annual Report"]
    na_statuses = ["NA", "TL", "SK"]
    downloaded_files = []

    # Use panda to get a length for csv
    num_lines = len(
        pd.read_csv("ARC_HH_OK_AR_missing.csv", low_memory=False)
    )  # Low_memory=false removes warnings

    # Need all files in a list to get dates for files
    with open(tracker_directory + "/filestracker.csv", "r", newline="") as files_file:
        files_reader = csv.reader(files_file)
        next(files_reader)

        for files_row in files_reader:
            if (
                files_row[5] in valid_doctypes
            ):  # only care about valid doctypes, this will make other doctypes appear as N in the matching year column in matching.csv, signalling no file match
                downloaded_files.append(files_row)

    with alive_bar(num_lines) as bar:  # Progress bar
        bar.text("Validating ARC_missing.csv matches with files")

        with open("ARC_HH_OK_AR_missing.csv", "r", newline="") as arc_file:

            arc_reader = csv.reader(arc_file)
            next(arc_reader)  # Skip headers

            for arc_row in arc_reader:
                key = arc_row[1]
                name = arc_row[16]
                year = arc_row[9]
                data_date = (arc_row[8].split(" "))[0]
                status = "NA"
                year_match = "N"
                file_count = 0

                with open(
                    tracker_directory + "/ziptracker.csv", "r", newline=""
                ) as zips_file:
                    zips_reader = csv.reader(zips_file)
                    next(zips_reader)  # Skip headers

                    for zips_row in zips_reader:

                        if zips_row[0] == key:  # GVkeys match

                            if zips_row[2] not in na_statuses:
                                status = "OK"

                            if status != "OK":
                                if zips_row[2] in na_statuses:
                                    status = zips_row[2]
                                else:
                                    status = "NA"

                # If an entry has a file match, we will check the year
                if status == "OK":

                    for item in downloaded_files:
                        if (
                            item[4].split("/")[-1] == year and item[0] == key
                        ):  # Account for match if GVkey and exact year match
                            year_match = "Y"
                            file_count += 1
                bar()

                MatchingAppend(
                    key, name, year, data_date, status, year_match, file_count
                )


def CreateMissingYearsDict():
    """
    Creates a dictionary for firms that were found but have missing years

    Return: dictionary following format:
        GVKEY : (Company name, [List of missing years])
    """

    ret = {}

    with open("matching.csv", "r", newline="") as file:
        reader = csv.reader(file)

        for row in reader:

            if row[4] == "OK" and row[5] == "N":  # gap year criteria

                if row[0] not in ret:  # need to specify type on first encounter
                    ret[row[0]] = (row[1], [row[2]])

                else:  # if key has been created, we will add years
                    ret[row[0]][1].append(row[2])

    return ret


def TertiaryCheck():
    """
    Iterates through matching.csv, finds companys that werent NA with gaps in years, downloads and tracks them
    """

    missing_years_dict = CreateMissingYearsDict()

    # Need a webdriver as we will be downloading files in this function
    driver = downloadscript.CreateDriver()
    downloadscript.CompleteAuth(
        driver,
        input("Input a valid msu email to access mergent archives.\n"),
        getpass("Input a valid msu password.\n"),
    )

    amt_downloaded_kb = 0.0  # needs to stay under 1800000 kb #should be zero

    with alive_bar(len(missing_years_dict)) as bar:  # Progress bar

        bar.text("Starting tertiary check for gap years...")
        bar()

        for key, val_list in missing_years_dict.items():

            amt_downloaded_kb = downloadscript.CheckAndWait(bar, amt_downloaded_kb)

            amt_downloaded_kb = downloadscript.SearchActions(
                driver, bar, key, val_list[0], amt_downloaded_kb, True, val_list[1]
            )  # search all will be true,

            bar.text(str(amt_downloaded_kb / 1000000.0) + "GB Downloaded")
            bar()

    driver.quit()


def MatchingAppend(key, name, year, data_date, status, year_match, file_count):
    """
    Appends parameters as a row into matching.csv

    Keyword arguments:
    key -- GVkey for a firm
    name -- Company name from missing.csv
    year -- Year from ARC_missing.csv
    data_date -- full date from ARC_mising.csv
    status -- download statuses: "OK"(downloaded and matched), "SK" (skipped during download),"NA"(not on mergent),TL" (too long, skipped)
    Return: void
    """

    temp = [key, name, year, data_date, status, year_match, file_count]

    with open("matching.csv", "r", newline="") as file:
        reader = csv.reader(file)

        for row in reader:  # Avoid duplicate entries
            if row == temp:
                return 0

    with open("matching.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(temp)


def TypesAppend(
    path,
    key,
    name_HH,
    name_mergent,
    year,
    doctype_confirmed,
    name_confirmed,
    year_confirmed,
    missing_index,
):
    """
    Appends parameters to confirmations.csv

    Keyword arguments:
    path -- path to file on disk
    key -- company gvkey
    name_HH -- name in missing.csv
    name_mergent -- name from file downloaded from mergent
    year -- filing year
    doctype_confirmed -- boolean variable
    name_confirmed -- string highest fuzzymatched with search term
    year_confirmed -- year gathered from pdf
    missing_index -- index in missing.csv where the correlated file is related
    Return: void
    """
    temp = [
        str(path),
        str(key),
        str(name_HH),
        str(name_mergent),
        str(year),
        str(doctype_confirmed),
        str(name_confirmed),
        str(year_confirmed),
        str(missing_index),
    ]
    with open("confirmations.csv", "r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            if row == temp:
                return 0

    with open("confirmations.csv", "a", newline="") as file:
        writer = csv.writer(file)
        try:
            writer.writerow(temp)
        except UnicodeEncodeError:  # Thrown unexpectedly, cause not known
            return 0


def VerifyAppearances(
    text, doctype_confirmed, name, name_confirmed, year, year_confirmed
):
    """
    Iterates through textpages list of words and check simultaneously for doctype, name, and year if not already confirmed

    Keyword arguments:
    text -- list of words from page
    doctype_confirmed -- bool, true if doctype found
    name -- string, name to check against
    name_confirmed -- bool true if name found
    year -- string, year to check against
    year_confirmed -- bool, true if year found
    Return: doctype_confirmed ,name_confirmed, ,year_confirmed
    """

    name_matches = (
        {}
    )  # Used for storing potential name matches with their fuzz ratio for later ranking

    # Iterate through each wood in page
    for word in text:
        word = word.strip()  # Whitespace may decrease fuzzymatch accuracy

        # Each check will terminate on first conditional if a match has been already found

        if (
            doctype_confirmed == "None"
            and fuzz.ratio(word.lower(), "annual report") >= 70
        ):
            doctype_confirmed = word  # fuzzymatched above threshold

        elif name_confirmed == "None":
            r = fuzz.ratio(word.lower(), name.lower())

            if r >= 80:
                name_matches[word] = r  # Append word:r to dict

        elif (
            year_confirmed == "None" and len(word) == 4 and fuzz.ratio(word, year) >= 80
        ):  # Only interested in 4 character long strings
            year_confirmed = word

    # Find name with highest fuzz ratio
    if name_confirmed == "None":

        if len(name_matches) == 1:
            for key in name_matches:  # If one name match, just grab it
                name_confirmed = key

        elif len(name_matches) > 1:  # If multiple matches
            name_confirmed = list(sorted(name_matches))[
                -1
            ]  # Grab greatest value using sort algorithm and dict values

    return doctype_confirmed, name_confirmed, year_confirmed


def GetMissingIndex(key, HH_name, date, occs):
    """
    Finds a unique index holding correlated company in missing.csv

    key -- gvkey from metadata
    HH_name name from missing.csv and metadata
    date- date from metadata
    occs- every index that has already occured
    Return: int or string
    """

    with open("ARC_HH_OK_AR_missing.csv", "r", newline="") as file:
        reader = csv.reader(file)
        count = 0  # Index essentially

        for row in reader:

            if row[9] == date[-4:] and (row[1] == key or row[16] == HH_name):

                if count not in occs:  # Ensures unique indices
                    return count  # Appendage of count to occs will be done outside of function, as list will be destroyed by scope

            count += 1

    return "NA"


def VerifyPdfs():
    """
    Searches through pdfs for doctype, year, and name matches

    Return: void
    """
    occs = []  # Storage for occupied indices from ARC_missing.csv
    total_count = 0
    found_count = 0

    # Use panda to get length of csv
    num_lines = len(pd.read_csv("metadata.csv"))

    with open("metadata.csv", "r", newline="") as file:
        reader = csv.reader(file)
        next(reader)  # skip titles

        with alive_bar(num_lines) as bar:  # Initiliaze progress bar
            bar.text("Verifying files")

            for row in reader:

                if row[7]:  # Check for valid filepath (row[7])
                    doc = False  # Used to check if file loaded successfully
                    total_count += 1  # Total file count includes before

                    # Attempt reading of file via Pymupdf (fitz)
                    try:
                        doc = fitz.open(row[7])
                    except UnicodeDecodeError:
                        continue
                    except PdfReadError:
                        continue
                    except pymupdf.EmptyFileError:
                        continue
                    except pymupdf.FileDataError:
                        continue

                    # Before check all variables must be None for each file
                    doctype_confirmed = "None"
                    name_confirmed = "None"
                    year_confirmed = "None"

                    if doc:  # Check for successful load
                        found_count += 1

                        # Attempt fuzzymatching across all pages of doc
                        try:
                            for page in doc:

                                # Check for a complete profile, if not, check will resume
                                if not (
                                    doctype_confirmed != "None"
                                    and name_confirmed != "None"
                                    and year_confirmed != "None"
                                ):
                                    text = page.get_text().split(
                                        "\n"
                                    )  # Seperates paragraph into list of individual words

                                    results = VerifyAppearances(
                                        text,
                                        doctype_confirmed,
                                        row[2],
                                        name_confirmed,
                                        row[4],
                                        year_confirmed,
                                    )

                                    doctype_confirmed = results[0]
                                    name_confirmed = results[1]
                                    year_confirmed = results[2]

                                else:
                                    break

                        except pymupdf.mupdf.FzErrorFormat:
                            continue

                        missing_index = GetMissingIndex(row[1], row[2], row[5], occs)
                        TypesAppend(
                            row[7],
                            row[1],
                            row[2],
                            row[3],
                            row[4],
                            doctype_confirmed,
                            name_confirmed,
                            year_confirmed,
                            missing_index,
                        )
                        occs.append(missing_index)  # Index is now verifiably occupied

                bar()

    if total_count != 0:
        print(
            str((found_count / total_count) * 100)
            + "% of documents were able to be opened and read \n"
        )


def PrintStatistics():
    """
    Prints various stats about the results of VerifyPdfs()

    Return: void
    """

    scan_count = 0

    with open("confirmations.csv", "r", newline="") as file:
        reader = csv.reader(file)

        doc_verified = 0
        name_verified = 0
        name_exacts = 0
        year_verified = 0
        year_exacts = 0
        true_count = 0

        for row in reader:

            all = True  # Toggle to see if a conditional fails

            if str(row[5]) != "None":  # row[5] is doctype predition col
                doc_verified += 1
            else:
                all = False

            if str(row[6]) != "None":  # row[6] is name prediction col
                name_verified += 1
                if str(row[6]) == str(row[3]):  # row[3] is exact desired name from HH
                    name_exacts += 1
            else:
                all = False

            if str(row[7]) != "None":  # row[7] is year prediction col
                year_verified += 1
                if str(row[7] == row[4]):  # row[4] is exact desired year
                    year_exacts += 1
            else:
                all = False

            if (
                all == True
            ):  # If program reaches this line after 3 conditionals and all isnt toggled off, all targeted columns will have values
                true_count += 1

            # Total scanned docs
            scan_count += 1

    print(str((true_count / scan_count) * 100) + "% have all three fields verified\n")
    print(str((doc_verified / scan_count) * 100) + "% of files are annual reports\n")
    print(
        str((name_verified / scan_count) * 100)
        + "% of files have verified similar names\n"
    )
    print(str((name_exacts / name_verified) * 100) + "% of names are exact\n")
    print(
        str((year_verified / scan_count) * 100)
        + "% of files have verified similar years\n"
    )
    print(str((year_exacts / year_verified) * 100) + "% of years are exact\n")


def CountMatches():
    """
    Counts lines that have a unique match to ARC.csv

    Return: total - number of files opened and read, matches - unique match count
    """

    total = 0
    matches = 0

    with open("confirmations.csv", "r", newline="") as file:
        reader = csv.reader(file)
        next(reader)

        for row in reader:
            if row[8] != "NA":  # Only outcomes are NA or an index
                matches += 1
            total += 1

    return total, matches


def main():

    InitializeFiles()
    x = 0
    while x < 2:
        UnzipFiles()
        OpenTrackers()
        ValidateMatches()
        if x == 0:
            TertiaryCheck()
        x += 1
    VerifyPdfs()
    PrintStatistics()
    results = CountMatches()
    print(str(results[1]) + "Matches to search terms confirmed")

    return 0


if __name__ == "__main__":

    main()
