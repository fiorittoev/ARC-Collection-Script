"""
Creates a metadata csv based on two trackers and zips in their respective folders, unzips each zip, 
then matches each file name to what data it should be holding and tracks within the metadata.csv

requirements:
pip insall alive-progress
By Evan Fioritto
"""

import os
import zipfile
import csv
import fitz
import pymupdf
import pandas as pd
from PyPDF2.errors import PdfReadError
from rapidfuzz import fuzz
from alive_progress import alive_bar

zip_directory = "./zips"
folder_directory = "./folders"
tracker_directory = "./trackers"


def InitializeFiles():
    """
    Creates folders trackers and zips folder if ther do not already exist

    Return: void
    """
    dirs = [zip_directory, folder_directory, tracker_directory]
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)
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
                try:
                    with zipfile.ZipFile(f, "r") as zip_ref:
                        zip_ref.extractall(path)
                except zipfile.BadZipFile:
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
    for folder_name in os.listdir(folder_directory):

        folder_name_list = folder_name.split("_")

        if key == folder_name_list[0] and zip_page == folder_name_list[-1]:

            folder_path = os.path.join(folder_directory, folder_name)

            for file_name in os.listdir(folder_path):

                file_number = file_name[:-4].strip()[-1]
                if file_number == row_number:

                    file_path = os.path.join(folder_path, file_name)

                    return file_name, file_path
    return 0, 0


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
        next(zip_reader)

        df = pd.read_csv(tracker_directory + "/ziptracker.csv")
        num_lines = len(df)
        with alive_bar(num_lines) as bar:

            bar.text("Pulling Metadata")

            for zip in zip_reader:

                key = zip[0]
                name_HH = zip[1]
                zip_page = zip[2]  # Could be "TL" or "NA", if it is we skip

                if zip_page not in invalids:

                    with open(
                        tracker_directory + "/filestracker.csv", newline=""
                    ) as csvfile2:

                        file_reader = csv.reader(csvfile2)
                        next(file_reader)

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
                                    used_files.append(file_info[0])
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
            if row == temp:
                return 0
    with open("metadata.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(temp)


def ValidateMatches():

    na_statuses = ["NA", "TL", "SK"]
    used_files = []
    all_files = []

    with open("ARC_HH_OK_AR_missing.csv", "r", newline="") as arc_file:

        arc_reader = csv.reader(arc_file)
        next(arc_reader)

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
                next(zips_reader)

                for zips_row in zips_reader:

                    if zips_row[0] == key:
                        if zips_row[2] not in na_statuses:

                            with open(
                                tracker_directory + "/filestracker.csv", "r", newline=""
                            ) as files_file:

                                if len(all_files) == 0:
                                    flag = 1

                                files_reader = csv.reader(files_file)
                                next(files_reader)

                                appended = False
                                for files_row in files_reader:
                                    if flag:
                                        all_files.append(
                                            files_row
                                        )  # store all files on first iteration
                                    if (
                                        files_row[0] == zips_row[0]
                                        and files_row[3] == zips_row[2]
                                        and files_row not in used_files
                                    ):
                                        status = "OK"

                                        if appended == False:
                                            used_files.append(files_row)
                                            appended = True
                                flag = 0
                        if status != "OK":
                            if zips_row[2] in na_statuses:
                                status = zips_row[2]
                            else:
                                status = "NA"
            if status == "OK":
                for item in all_files:
                    if item[4].split("/")[-1] == year and item[0] == key:
                        year_match = "Y"
                        file_count += 1
            MatchingAppend(key, name, year, data_date, status, year_match, file_count)


def MatchingAppend(key, name, year, data_date, status, year_match, file_count):
    temp = [key, name, year, data_date, status, year_match, file_count]
    with open("matching.csv", "r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
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
        except UnicodeEncodeError:
            return 0


def VerifyAppearances(
    text, doctype_confirmed, name, name_confirmed, year, year_confirmed
):
    """
    Iterates through textpages list of words and check simultaneously for doctype name and year if not already confirmed

    Keyword arguments:
    text -- list of words from page
    doctype_confirmed -- bool, true if doctype found
    name -- string, name to check against
    name_confirmed -- bool true if name found
    year -- string, year to check against
    year_confirmed -- bool, true if year found
    Return: doctype_confirmed,name_confirmed, ,year_confirmed
    """
    name_matches = {}
    for word in text:
        word = word.strip()
        if (
            doctype_confirmed == "None"
            and fuzz.ratio(word.lower(), "annual report") >= 70
        ):
            doctype_confirmed = word
        elif name_confirmed == "None":
            r = fuzz.ratio(word.lower(), name.lower())
            if r >= 80:
                name_matches[word] = r
        elif (
            year_confirmed == "None" and len(word) == 4 and fuzz.ratio(word, year) >= 80
        ):
            year_confirmed = word
    if name_confirmed == "None":
        if len(name_matches) == 1:
            for key in name_matches:
                name_confirmed = key
        elif len(name_matches) > 1:
            name_confirmed = list(sorted(name_matches))[-1]

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
        count = 0
        for row in reader:
            if row[9] == date[-4:] and (row[1] == key or row[16] == HH_name):
                if count not in occs:
                    return count
            count += 1
    return "NA"


def VerifyPdfs():
    """
    Searches through pdfs for doctype, year, and name matches

    Return: void
    """

    occs = []
    total_count = 0
    found_count = 0

    df = pd.read_csv("metadata.csv")
    num_lines = len(df)
    with open("metadata.csv", "r", newline="") as file:
        reader = csv.reader(file)
        next(reader)  # skip titles

        with alive_bar(num_lines) as bar:

            bar.text("Verifying files")
            for row in reader:

                if row[7]:
                    doc = False
                    total_count += 1
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

                    doctype_confirmed = "None"
                    name_confirmed = "None"
                    year_confirmed = "None"

                    if doc:
                        found_count += 1
                        try:
                            for page in doc:

                                if not (
                                    doctype_confirmed != "None"
                                    and name_confirmed != "None"
                                    and year_confirmed != "None"
                                ):
                                    text = page.get_text().split("\n")

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
                        occs.append(missing_index)
                bar()
    if total_count != 0:
        print(
            str((found_count / total_count) * 100)
            + "% of documents were able to be opened and read \n"
        )


def PrintStatistics():
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

            all = True

            if str(row[5]) != "None":
                doc_verified += 1
            else:
                all = False

            if str(row[6]) != "None":
                name_verified += 1
                if str(row[6]) == str(row[3]):
                    name_exacts += 1
            else:
                all = False

            if str(row[7]) != "None":
                year_verified += 1
                if str(row[7] == row[4]):
                    year_exacts += 1
            else:
                all = False

            if all == True:
                true_count += 1
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
    total = 0
    matches = 0
    with open("confirmations.csv", "r", newline="") as file:
        reader = csv.reader(file)
        next(reader)
        for row in reader:
            if row[8] != "NA":
                matches += 1
            total += 1
    return total, matches


def main():
    pymupdf.TOOLS.set_icc(False)
    InitializeFiles()
    UnzipFiles()
    # OpenTrackers()
    ValidateMatches()
    VerifyPdfs()
    PrintStatistics()
    results = CountMatches()
    print(str(results[1]) + "Matches to search terms confirmed")

    return 0


if __name__ == "__main__":

    main()
