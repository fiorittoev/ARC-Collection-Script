import csv


def WriteMissing():
    """
    Analyzes matching.csv for files that returned no mergent result or no matching year

    Keyword arguments:
    Return: number of incomplete entries, number of gap year entries
    """

    missing_count = 0
    gap_count = 0

    with open("missing_firms.csv", "w", newline="") as csvfile1:

        writer = csv.writer(csvfile1)
        writer.writerow(  # write header
            [
                "GVKey",
                "Company Name",
                "Year",
                "Data Date",
                "Status",
            ]
        )

        with open("matching.csv", "r") as csvfile2:
            reader = csv.reader(csvfile2)

            for row in reader:

                if row[4] == "NA":  # no mergent result
                    writer.writerow([row[0], row[1], row[2], row[3], "NA"])
                    missing_count += 1
                elif row[5] == "N":  # no matching year
                    writer.writerow([row[0], row[1], row[2], row[3], "N"])
                    gap_count += 1
                    missing_count += 1

    return missing_count, gap_count


def WriteFound():
    """
    Analyzes matching.csv for files that OK and have a year match and at least one file

    Keyword arguments:
    Return: number of downloaded entries
    """

    with open("found_firms.csv", "w", newline="") as csvfile1:

        found_count = 0

        with open("found_firms.csv", "w", newline="") as csvfile1:

            writer = csv.writer(csvfile1)
            writer.writerow(  # write header
                ["GVKey", "Company Name", "Year", "Data Date", "File Count"]
            )

            with open("matching.csv", "r") as csvfile2:
                reader = csv.reader(csvfile2)

                for row in reader:
                    if row[4] == "OK" and row[5] == "Y" and int(row[6]) > 0:
                        writer.writerow([row[0], row[1], row[2], row[3], row[6]])
                        found_count += 1

    return found_count


def CreateEntryDict():
    """
    Create a dictionary to correlate gvkey to number of downloaded zips

    Keyword arguments:
    Return: dictionary {str(gvkey): int(count)}
    """
    entry_dict = {}

    with open("matching.csv", "r") as csvfile2:
        reader = csv.reader(csvfile2)
        next(reader)

        for row in reader:

            if row[0] in entry_dict.keys():
                entry_dict[row[0]] += 1

            else:
                entry_dict[row[0]] = 1

    return entry_dict


def CreateVerifiedEntryDict():
    """
    Create a dictionary to correlate gvkey to number of verified downloaded zips
    (zips with valid status, year match, and at least one file)

    Return: dictionary {str(gvkey): int(count)}
    """
    entry_dict = {}

    with open("matching.csv", "r") as csvfile2:
        reader = csv.reader(csvfile2)
        next(reader)

        for row in reader:

            if row[5] == "Y" and int(row[6]) > 0:

                if row[0] in entry_dict.keys():
                    entry_dict[row[0]] += 1

                else:
                    entry_dict[row[0]] = 1

            elif row[0] not in entry_dict.keys() and row[4] == "NA":
                entry_dict[row[0]] = 0

    print(entry_dict)
    return entry_dict


def CountFirms():
    """
    Counts complete firms and total entries

    Return: (# of matches, total entries)
    """

    matching_count = 0
    na_count = 0
    entry_dict = CreateEntryDict()
    verified_entry_dict = CreateVerifiedEntryDict()

    for v_entry, v_entry_count in verified_entry_dict.items():

        for entry, entry_count in entry_dict.items():

            if v_entry == entry:

                if v_entry_count == entry_count:
                    matching_count += 1

                elif str(v_entry_count) == "0":
                    na_count += 1

                break

    return matching_count, len(entry_dict), na_count


def main():
    missing_entries, gap_count = WriteMissing()
    found_entries = WriteFound()
    complete_firms, total_firms, na_firms = CountFirms()
    print("Number of total entries:", found_entries + missing_entries)
    print("Number of verified entries:", found_entries)
    print("Number of NA entries and entries with no year match:", missing_entries)
    print(
        "Number of entries from firms we have downloaded, but did not have a year for (gap years):",
        gap_count,
    )
    print("Firms with complete entries:", complete_firms, "/", total_firms)
    print("Firms returned completely NA:", na_firms, "/", total_firms)

    return 0


if __name__ == "__main__":
    main()
