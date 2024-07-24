"""
Copies desired folders from "./folders" to "./matched_folders" using results from found_firms
"""

import csv
import shutil
import os

folder_dir = "./folders"
matched_folder_dir = "./matched_folders"


def CreateGVKeyList():
    """
    Creates a list of all desired unique gvkeys

    Return: list of ints
    """

    found_gvkeys = []

    with open("found_firms.csv") as csvfile:

        reader = csv.reader(csvfile)

        for row in reader:

            if row[0] not in found_gvkeys:

                found_gvkeys.append(row[0])

    return found_gvkeys


def main():
    found_gvkeys = CreateGVKeyList()

    for folder in os.listdir(folder_dir):

        if folder.split("_")[0] in found_gvkeys:

            src_dir = folder_dir + "/" + folder
            dest_dir = matched_folder_dir + "/" + folder
            try:
                shutil.copytree(src_dir, dest_dir)
            except FileExistsError:
                continue
    return 0


if __name__ == "__main__":
    main()
