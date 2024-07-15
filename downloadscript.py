"""
Script for MSU Research to download 13k annual reports within batch zip files.

Filestracker - every file that we have downloaded successfully
Ziptracker - information scraped from each search, along with the status of the bulk download


By Evan Fioritto

requires:
pip install selenium
pip install alive-progress
"""

import csv
import time
import os
import glob
import os.path
import zipfile
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementClickInterceptedException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from alive_progress import alive_bar
from getpass import getpass


def GetDict():
    """
    Stores company data in return dictionary as as {'Global Company Key':'Company Name'}
    Return: Dictionary based off ARC_HH_OK_AR_missing.csv
    """
    # Create dictionary
    ret = {}

    # Populate dictionary
    with open("ARC_HH_OK_AR_missing.csv") as csvfile:
        reader = csv.reader(csvfile)

        next(reader)  # skip titles
        for row in reader:  # iterate through csv
            ret[row[1]] = row[
                16
            ]  # row[1] = Global Company Key , row [16] = Company Name , overwrites repeated company entries

    return ret


def GetDownloadDirectory():
    """
    Used in setting default web browser and renaming downloaded files
    Return: void
    """
    # This gets the current working directory where the script is located
    script_dir = os.getcwd()
    download_dir = os.path.join(script_dir, "zips")  # specifies to subforlder

    return download_dir


def CreateDriver():
    """
    Creates a Webdriver that dowloads to AnnualReports subfolder
    Return: Webdriver with mergent archives loaded
    """
    # Define the subfolder for downloads relative to the script location
    download_dir = GetDownloadDirectory()
    os.makedirs(
        download_dir, exist_ok=True
    )  # make new download folder if ARC_Zips doesnt exist

    # Create options profile
    chrome_options = webdriver.ChromeOptions()
    chrome_options.set_capability("acceptInsecureCerts", True)
    chrome_options.add_argument("--window-size=1920,1080")
    # ignore errors
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--ignore-certificate-errors")
    chrome_options.add_argument("--ignore-certificate-errors-spki-list")
    chrome_options.add_argument("--ignore-ssl-errors")
    chrome_options.add_argument("--disable-quic")

    chrome_options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": download_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )
    # apply options
    driver = webdriver.Chrome(options=chrome_options)

    # Initial Access mergent archives
    driver.get("https://www-mergentarchives-com.proxy1.cl.msu.edu/search.php")
    return driver


def CompleteAuth(driver, user, pw):
    """
    Logs into an MSU authorization page

    driver -- Initialized webdriver that has landed on an msu authorization page
    user -- string that contains msu email address
    pw -- password for associated email addres
    Return: void
    """
    # create element object
    wait = WebDriverWait(driver, 15)
    usernameQuery = wait.until(
        EC.presence_of_element_located((By.ID, "input28"))
    )  # wait for load, create element that holds username
    passwordQuery = driver.find_element(
        By.ID, "input36"
    )  # element that holds password,if username is loaded this one should be too

    # send in credentials
    usernameQuery.send_keys(user)
    passwordQuery.send_keys(pw)

    # submit
    submitButton = driver.find_element(
        By.CSS_SELECTOR, "#okta-sign-in.auth-container .button-primary"
    )  # as with pwQuery, should be safe to click
    submitButton.click()  # Loads search page
    # CHECK FOR HANG AFTER SUBMITBUTTON


def SearchActions(driver, bar, key, val, total_download, search_all, specific_years=[]):
    """
    All of the actions completed on the Search page, will land on results page

    driver -- webdriver element on the search page
    val -- string value, the company name
    total_download -- kb downloaded in current cycle

    Return: void
    """
    # Wait until doctype box appears, signalling page load
    wait = WebDriverWait(driver, 15)
    documentQuery = wait.until(EC.presence_of_element_located((By.ID, "ext-comp-1014")))

    documentQuery.click()
    # Wait for inner dropdown menu wrapper
    doctype = driver.find_element(
        By.ID,
        "doctype",
    )

    companyQuery = driver.find_element(
        By.NAME, "companyName"
    )  # element that holds company name
    companyQuery.send_keys(val)

    wait.until(EC.presence_of_element_located((By.ID, "ext-gen302")))

    # Two cases, annual reports or unfiltered doctype
    if search_all == False:

        attempt_count = 0  # counter for doctype attempts, if it takes more than 5, download will proceed with selected doctype

        while doctype.get_attribute("value") != "ANR":
            if attempt_count > 10:
                break
            # Scroll to top
            for x in range(0, 20):
                documentQuery.send_keys(Keys.ARROW_UP)
            # Select ANR
            for x in range(0, 3):
                documentQuery.send_keys(Keys.ARROW_DOWN)
            documentQuery.send_keys(Keys.ENTER)

            attempt_count += 1

    submitButton = driver.find_element(By.ID, "ext-gen224")
    submitButton.click()

    total_download = ResultActions(
        driver, bar, key, val, total_download, search_all, specific_years
    )

    return total_download


def ResultActions(driver, bar, key, val, total_download, search_all, specific_years=[]):
    """
    All of the actions completed on the Search Results page

    driver -- webdriver landed on search results page
    Return: total download in kb
    """

    # initialize variables
    date_values = []
    current_page = 1
    zipsize = 0

    # check page count
    wait = WebDriverWait(driver, 20)
    # Checks for occasional hang after search
    load_success = 0

    try:
        pageCountContainer = wait.until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "/html/body/div[9]/div[2]/div/div[3]/div[2]/div/div[2]/div[2]/div/div/div[1]/div[5]/div/table/tbody/tr/td[6]/span",
                )
            )
        )
        reportCountContainer = wait.until(
            EC.presence_of_element_located((By.ID, "limitCount"))
        )
        load_success = 1
    except TimeoutException:
        driver.refresh()

        try:
            pageCountContainer = wait.until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "/html/body/div[9]/div[2]/div/div[3]/div[2]/div/div[2]/div[2]/div/div/div[1]/div[5]/div/table/tbody/tr/td[6]/span",
                    )
                )
            )
            reportCountContainer = wait.until(
                EC.presence_of_element_located((By.ID, "limitCount"))
            )
            load_sucess = 1

        except TimeoutException:
            load_sucess = 0

    if load_success == 1:
        try:
            last_page_number = ((pageCountContainer.text).split())[-1]
        except IndexError:
            last_page_number = "1"
        # If there is only one page
        if last_page_number == "1":
            scraperesults = ScrapeRows(
                driver, key, date_values, last_page_number, search_all, specific_years
            )

            date_values = scraperesults[0]
            page_size = scraperesults[1]
            filename = GenFileName(date_values, key, val, last_page_number, search_all)

            total_download = CheckAndWait(
                bar, total_download + page_size
            )  # check in between each file

            if (page_size + total_download) <= 1800000:

                if reportCountContainer.text == "0":

                    if (
                        search_all
                    ):  # If we are searching all doctypes and there are no results, we will write NA
                        WriteZipTracker(key, val, "NA")
                    else:
                        # After either case, we go back to resume search
                        driver.get(
                            "https://www-mergentarchives-com.proxy1.cl.msu.edu/search.php"
                        )
                        total_download = SearchActions(
                            driver, bar, key, val, total_download, True
                        )  # Search again, no filter this time

                else:

                    zipsize = BulkDownload(driver, filename, search_all)
                    WriteZipTracker(key, val, last_page_number)
                    total_download += zipsize
                    if filename:
                        bar.text(
                            str((total_download + zipsize) / 1000000.0)
                            + "GB Downloaded"
                        )

            else:
                WriteZipTracker(key, val, "TL")  # TL for too large

        # multiple pages
        else:
            while current_page <= int(
                last_page_number
            ):  # until we are on the last page

                zipsize = 0

                scraperesults = ScrapeRows(
                    driver, key, date_values, current_page, search_all, specific_years
                )

                date_values = scraperesults[0]
                page_size = scraperesults[1]
                filename = GenFileName(
                    date_values, key, val, str(current_page), search_all
                )

                total_download = CheckAndWait(
                    bar, total_download + page_size
                )  # check in between each file

                if (
                    page_size + total_download
                ) <= 1800000:  # if file greater than 180000 kb, mark and ship
                    zipsize += BulkDownload(driver, filename, search_all)
                    total_download += zipsize
                    date_values.clear()  # need seperate ranges for each page's zip

                    WriteZipTracker(key, val, str(current_page))
                    if filename:
                        bar.text(
                            str((total_download + zipsize) / 1000000.0)
                            + "GB Downloaded"
                        )

                else:
                    WriteZipTracker(key, val, "TL")  # TL for too large

                total_download = CheckAndWait(
                    bar, total_download
                )  # check in between each file

                if current_page != int(last_page_number):
                    # Go to next page
                    current_page += 1
                    wait = WebDriverWait(driver, 60)
                    try:
                        pageQuery = wait.until(
                            EC.presence_of_element_located((By.ID, "ext-gen147"))
                        )
                    except TimeoutError:
                        driver.refresh()
                        pageQuery = wait.until(
                            EC.presence_of_element_located((By.ID, "ext-gen147"))
                        )
                    pageQuery.send_keys(Keys.CONTROL + "a")
                    pageQuery.send_keys(Keys.BACK_SPACE)
                    pageQuery.send_keys(current_page)
                    pageQuery.send_keys(Keys.ENTER)  # redirects to next page
                else:
                    break
    else:
        WriteZipTracker(key, val, "SK")

    # After either case, we go back to resume search
    driver.get("https://www-mergentarchives-com.proxy1.cl.msu.edu/search.php")

    return total_download


def LoadTable(driver):
    """
    Completely loads table and all of its rows for the search results page

    driver -- webdriver on the search page
    Return: rows: list of row elements
    """

    time.sleep(5)  # TEMP PREVENTS STALE ERROR

    # Wait until table of results completely loads
    wait = WebDriverWait(driver, 20)
    wait.until(
        EC.presence_of_element_located((By.XPATH, "//*[@id='ext-gen96']/table/tbody"))
    )
    rows = wait.until(
        EC.presence_of_all_elements_located(
            (By.XPATH, "//*[@id='ext-gen96']/table/tbody/tr")
        )
    )

    return rows


def ScrapeRows(driver, key, date_values, page_number, search_all, specific_years=[]):
    """
    Grabs date values from table of results

    driver -- webdriver on a company's results page
    Return: return_description
    """
    rows = LoadTable(driver)
    invalids = ["", " "]
    valid_docs = ["Annual/10K Report", "10K or Int'l Equivalent"]
    page_size_kb = 0
    # check each row for values
    count = 1
    for row in rows:
        cells = row.find_elements(By.TAG_NAME, "td")
        if (
            len(cells) > 5
        ):  # rows with empty cols used for spacing, anything greater than 3 holds real data

            year_div = cells[3].find_element(
                By.TAG_NAME, "div"
            )  # dates are nested within a div, cells[3] holds year information
            doc_div = cells[4].find_element(
                By.TAG_NAME, "div"
            )  # cells[4] holds doc_type information
            name_div = cells[1].find_element(
                By.TAG_NAME, "div"
            )  # cells[1] holds name information
            size_div = cells[5].find_element(
                By.TAG_NAME, "div"
            )  # dates are nested within a div, cells[5] has full date

            if not search_all or doc_div.text in valid_docs:

                year = (year_div.text)[-4:]

                # If were looking through multiple doctypes we need to select individual files
                if search_all:
                    try:
                        if len(specific_years) > 0:  # If looking for specific years
                            if year not in specific_years:
                                continue  # Will not toggle checkbox
                        (cells[0].find_element(By.TAG_NAME, "input")).click()
                    except (
                        ElementClickInterceptedException
                    ):  # Will only occur at small resolutions, not in headlessly
                        continue  # Will not toggle checkbox

                value = (size_div.text)[:-2]
                units = size_div.text[-2:]

                if units not in invalids and value not in invalids:
                    value = float(value)
                    if units == "MB":
                        value *= 1000
                    elif units == "GB":
                        value *= 1000000
                    page_size_kb += value

                # year will be last four digits

                if year not in invalids:  # Some empty values after last year
                    date_values.append(year)  # last 4 chars will always be the year

                    # If a valid year is found, the file is going to be downloaded, so we need to track
                    WriteFilesTracker(
                        key,
                        name_div.text,
                        count,
                        page_number,
                        year_div.text,
                        doc_div.text,
                    )
            count += 1

    return date_values, page_size_kb


def GenFileName(date_values, key, val, page, search_all):
    """
    Generates a file name, empty if date_values is empty

    date_values -- list of years
    Return: formated string : companykey + clickedterm + minyear+ maxyear all seperated by '_'
    """
    filename = ""
    # Store oldest and most recent dates
    if len(date_values) >= 1:
        end_date = date_values[0]  # most recent
        start_date = date_values[-1]  # least recent
        filename = (
            key + "_" + val + "_" + start_date + "_" + end_date + "_" + page
        )  # adjust to format

        if search_all:
            filename += "_altreport"

        if ZipExistCheck("\\" + filename.replace(" ", "-")):
            filename = ""  # if it exists, we pass a blank filename so it wont trigger a download

    return filename


def ZipExistCheck(filename):
    """
    Checks if a zip file exists in ARC_Zips

    Keyword arguments:
    filename-- string which stores formatted file name
    Return: bool
    """
    return os.path.isfile(GetDownloadDirectory() + filename + ".zip")


def BulkDownload(driver, filename, search_all):
    """
    Starts a bulk download, halts selenium until download is complete and renamed

    driver -- webdriver on a search results page
    filename -- valid formatted string
    Return: size of zip file downloaded
    """

    file_size = 0

    if filename:

        # wait for buttons to load
        wait = WebDriverWait(driver, 20)
        bulkDownloadButton = wait.until(
            EC.presence_of_element_located((By.ID, "bulk_download_btn"))
        )
        wait = WebDriverWait(driver, 30)

        time.sleep(4)  # TEMP in case above 2 lines do not work
        checkAllButton = wait.until(
            EC.presence_of_element_located((By.ID, "check_all_label"))
        )
        try:
            # Files will be selected individually for alt reports
            if not search_all:
                checkAllButton.click()  # selects all files

            bulkDownloadButton.click()  # begin bulk download
            file_size = CompleteDownloadAndRename(filename)
        except ElementClickInterceptedException:
            file_size = 0

    return file_size


def CompleteDownloadAndRename(filename):
    """
    Waits for the download of the most recent file to complete, renames it with the string parameter.
    To be called with each download.

    filename -- string to rename file with
    Return: size of the file downloaded
    """
    file_size_kb = 0

    if len(filename) > 0:  # check for empty string

        # replace spaces with hyphens to avoid spaces in a path
        filename = filename.replace(" ", "-")

        # Get ARC_Zips path
        download_dir = GetDownloadDirectory()
        search_pattern = os.path.join(download_dir, f"*.*")

        # Grab most recent
        files = glob.glob(search_pattern)

        if not files:
            return 0  # If no files, break

        while 1:
            # Grab most recent
            files = glob.glob(search_pattern)
            try:
                most_recent_file = max(files, key=os.path.getmtime)
                if most_recent_file[-3:] == "tmp":
                    time.sleep(2)
                    most_recent_file = max(files, key=os.path.getmtime)
                break
            except FileNotFoundError:
                continue

        try:
            file_size_kb = os.path.getsize(most_recent_file) / 1024
        except FileNotFoundError:
            file_size_kb = 0.0

        # Only rename if file is fully downloaded
        if most_recent_file.endswith(".crdownload") or most_recent_file.endswith(
            ".tmp"
        ):  # these extensions mean the download is not complete
            time.sleep(1)
            file_size_kb = CompleteDownloadAndRename(filename)

        else:
            new_name = os.path.join(download_dir, filename)
            os.rename(most_recent_file, new_name + ".zip")

    return file_size_kb


def UncompSize(folder):
    """
    Returns uncompressed size of all files in a zip

    Keyword arguments:
    folder -- zip folder
    Return: size in bytes
    """
    total = 0.0
    with zipfile.ZipFile(folder, "r") as zip:
        for f in zip.infolist():

            # compressed size = file.compress_size
            # uncompressed size
            total += f.file_size
    return total


def CreateTrackers():
    """
    Creates tracking csv of all files.
    To be called once before WriteTracker.

    Return: void
    """
    if os.path.exists("./trackers/ziptracker.csv") == 0:
        # Create and write headers for trackers
        with open("./trackers/ziptracker.csv", "w", newline="") as file:
            writer = csv.writer(file)
            fields = ["Global Company Key", "Company Name", "Page Found On"]
            writer.writerow(fields)

    if os.path.exists("./trackers//filestracker.csv") == 0:
        with open("./trackers/filestracker.csv", "w", newline="") as file:
            writer = csv.writer(file)
            fields = [
                "Global Company Key",
                "Company Name",
                "Row Number",
                "Page Number",
                "Filing Date",
                "Doctype",
            ]
            writer.writerow(fields)


def WriteZipTracker(key, val, page):
    """
    Writes parameters to zip tracker file
    SK=skipped
    NA=not available
    TL=too long (above 0.18 gb)
    key -- Global company key
    val -- Company name
    page- page found on
    Return: void
    """
    temp = [key, val, page]

    # If row exists we will not write it, and break out
    with open("./trackers/ziptracker.csv", "r", newline="") as file:
        reader = csv.reader(file)
        if page != "SK":
            for row in reader:
                if row == temp:
                    return 0
        else:  # If a file is already NA, a revisit should not be appended as SK
            for row in reader:
                if [temp[0], temp[1], "NA"] == row:
                    return 0

    with open("./trackers/ziptracker.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(temp)


def WriteFilesTracker(key, val, row_number, page_number, filing_date, doc_type):
    """
    Writes parameters to files tracker file

    key -- global company key
    val -- Company name
    page_number -- page number result was found on
    filing_date -- date the file was created
    doc_type -- type of document (should always be annual report but we wanna make sure)
    Return: void
    """
    # Check if file exists
    temp = [
        str(key),
        str(val),
        str(row_number),
        str(page_number),
        str(filing_date),
        str(doc_type),
    ]
    with open("./trackers/filestracker.csv", "r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            if row == temp:
                return 0

    # If file doesnt exist, append
    with open("./trackers/filestracker.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(temp)


def CheckAndWait(bar, amt_downloaded_kb):
    # 1.8 gb cap TEMP
    if amt_downloaded_kb >= 1800000.0:  # Cap for mergent archives download throttle
        bar.text("Waiting...")
        time.sleep(
            3660  # 1 hour 1 minute stall
        )  # When we reach safe threshold, we wait an hour to prevent lockout
        amt_downloaded_kb = 0.0

    return amt_downloaded_kb


def GetIndices():
    """
    Prompt user for Indices for use as parameters for search, both inclusive

    Return: two ints, first is starting index, second is ending_index
    """
    # Loop until input is valid
    while 1:
        starting_index = input(
            "Input starting firm index (1-958), 'c' to continue from last index stored\n"
        )
        ending_index = input("Input ending firm index (1-958)\n")

        if starting_index.isnumeric() and ending_index.isnumeric():
            starting_index = int(starting_index)  # strings to int
            ending_index = int(ending_index)
            if (
                (starting_index >= 1 and starting_index <= 958)
                and (ending_index >= 1 and ending_index <= 958)
                and (starting_index <= ending_index)
            ):
                break  # If within safe bounds, return
        elif starting_index == "c" and ending_index.isnumeric():
            ending_index = int(ending_index)
            if (ending_index >= 1 and ending_index <= 958) and (
                GetIndex() <= ending_index
            ):
                starting_index = GetIndex()
                break  # If within safe bounds, return
        print("Error: One or more entries invalid")
    return starting_index, ending_index


def StoreIndex(val):
    """
    Overwrites value in lastindex.txt if new value is greater

    val -- int of index to overwrite with
    Return: void
    """
    if val > GetIndex():
        f = open("lastindex.txt", "w")
        f.write(str(val))
        f.close()


def GetIndex():
    """
    Returns the index left off on by the last run

    Return: int index of last download
    """
    f = open("lastindex.txt", "r")
    ret = int(f.read())
    f.close()
    return ret


def main():

    # Create company dictionary for iteration
    companyDict = GetDict()

    # Gather search parameters
    starting_index, ending_index = GetIndices()

    # Create Webdriver and tracker files
    driver = CreateDriver()
    CreateTrackers()

    # Typically takes under a second to redirect if authorization needed
    time.sleep(1)

    if (
        driver.current_url  # Authentication
        == "https://auth.msu.edu/app/msu_libezproxy1_1/exk9lztnrdDlyj27O357/sso/saml"
    ):
        # Obtain valid credentials for log in
        msuUser = input("Input a valid msu email to access mergent archives.\n")
        msuPass = getpass("Input a valid msu password.\n")
        CompleteAuth(driver, msuUser, msuPass)  # Execute authorization page actions

    # Initialize loop variables
    amt_downloaded_kb = 0  # needs to stay under 1800000 kb #should be zero
    curr_firm = 1  # Start on first firm

    # Progress bar to visualize download eta
    with alive_bar(len(companyDict)) as bar:

        bar.text("Starting...")
        bar()  # start on 1

        # Key=Company Key, Val=clicked term
        for key, val in companyDict.items():
            if (curr_firm >= starting_index) and (curr_firm <= ending_index):

                amt_downloaded_kb = CheckAndWait(
                    bar, amt_downloaded_kb
                )  # Will wait an hour on trigger and reset amt to 0

                amt_downloaded_kb = SearchActions(
                    driver, bar, key, val, amt_downloaded_kb, False
                )  # Execute search page actions

                # firm complete
                StoreIndex(curr_firm)  # mark completion

            curr_firm += 1
            bar()  # update bar progress after each company
    print("Complete, " + str(amt_downloaded_kb / 1000000.0) + " downloaded.")
    driver.quit()


if __name__ == "__main__":
    main()
