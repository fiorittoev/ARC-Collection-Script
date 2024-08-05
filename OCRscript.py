"""
OCR Testing

Evan Fioritto

use my abridged icgauge package, not one listed on github

dependecies:
pip install python-doctr
pip3 install torch==2.4.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/test/cu118
"""

import os
import time
import icgauge
from icgauge import data_readers
from icgauge import feature_extractors
from icgauge import label_transformers
from icgauge import training_functions
from icgauge import utils
import json
import subprocess
import requests
from alive_progress import alive_bar
import csv
import scipy
from nltk.parse.corenlp import CoreNLPParser
from icgauge import experiment_frameworks
from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from random import randint
from downloadscript import GetIndices
from downloadscript import StoreIndex
from downloadscript import ResetIndex

extracted_text_dir = "./extracted_text"


def OCRSetup(dataset):
    """
    Creates neccesary environment for NLP and OCR processes to run

    dataset - pretrained docTR dataset, string of name
    Return: server- subprocess running nlp server,model- OCR prediction model for pdfs
    """

    # Define model for docTR ocr, try for NVIDIA graphics, if not found run from cpu
    try:
        model = ocr_predictor(
            dataset,  # linknet_resnet18" for rotated files
            pretrained=True,
            assume_straight_pages=False,
            preserve_aspect_ratio=True,
        ).cuda()
    except RuntimeError:
        model = ocr_predictor(
            dataset,
            pretrained=True,
            assume_straight_pages=False,
            preserve_aspect_ratio=True,
        )

    # Host nlp locally
    path_to_stanford_nlp = os.environ.get("STANFORD_NLP_HOME")

    if not path_to_stanford_nlp:
        raise EnvironmentError("STANFORD_NLP_HOME environment variable not set")

    # Command to start a local CoreNLP server
    command = [
        "java",
        "-mx4g",
        "-cp",
        os.path.join(path_to_stanford_nlp, "*"),
        "edu.stanford.nlp.pipeline.StanfordCoreNLPServer",
        "-port",
        "9000",
        "-timeout",
        "600000",
        "-be_quiet",
        "False",
        "-memory",
        "6G",
    ]  # runtime of
    # Start the server as a subproces
    server = subprocess.Popen(
        command,
        cwd=path_to_stanford_nlp,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(5)  # allow time to start

    return server, model


def ParseBody(parser, text):
    """
    Splits a body of text by 5 sentance groups into a parsed dictionary

    text -- body of text extracted via OCR
    Return: dictionary of paragraphs derived from text following format key=content: value=parse
    """

    paragraphs = {}
    temp_paragraph = []
    sentances = []
    sentance_count = 0

    for sentance in text.split("\n"):

        if sentance:
            if sentance_count > 5:  # paragraphs of 5 sentances

                paragraphs["\n".join(sentances)] = list(temp_paragraph)

                # reset variables
                sentance_count = 0
                temp_paragraph.clear()
                sentances.clear()

            try:
                sentances.append(sentance)
                temp_paragraph.append(str(next(parser.raw_parse(sentance, timeout=10))))
                sentance_count += 1

            except StopIteration:
                continue

            except requests.exceptions.ReadTimeout:
                continue

    return paragraphs


def CreateTempJson(paragraphs):
    """
    Writes parsed dictionary created in Parsebody to temp.json folder

    argument -- paragraphs-dictionary of paragraphs derived from text following format key=content: value=parse
    Return: void
    """
    json_entries = []

    for paragraph, parse in paragraphs.items():
        json_entries.append(
            {
                "parse": parse,
                "paragraph": paragraph,
                "score": randint(
                    1, 7
                ),  # give garbage value, will not matter because we are only grabbing predictions
            }
        )
    obj = json.dumps(json_entries, indent=4)
    with open("temp.json", "w") as outfile:
        outfile.write(obj)


def GetICGaugeScore(text):
    """
    Returns the semantic complexity predicted using icgauge

    Keyword arguments:
    argument -- text- body of text extracted via OCR
    Return: float
    """

    parser = CoreNLPParser(url="http://localhost:9000")

    CreateTempJson(ParseBody(parser, text))

    results = experiment_frameworks.experiment_features(
        train_reader=icgauge.data_readers.toy,
        assess_reader=lambda: icgauge.data_readers.read_format(["temp.json"]),
        train_size=0.7,
        phi_list=[icgauge.feature_extractors.manual_content_flags],
        class_func=icgauge.label_transformers.identity_class_func,
        train_func=icgauge.training_functions.fit_maxent_with_crossvalidation,
        score_func=scipy.stats.pearsonr,
        verbose=False,
    )

    total = 0
    val_total = 0

    print(results[-1])

    for analysis in results[-1]:  # results dict holds prediction count
        val_total += analysis["prediction"]
        total += 1

    return val_total / total  # Average predicted semantic score


def FormatResult(result):
    """
    Remove tables from OCR'd text, maintain space between paragraphs
    result - return type of model(doc)
    return - string
    """

    ret = ""

    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                words = [word.value for word in line.words]
                if (
                    len(words) > 5
                ):  # Only parse lines with 5 or more words, filters out tabular or incomplete data
                    ret += " ".join(words) + "\n"
            if len(block.lines) > 0:
                ret += "\n"

    return ret


def CreatePathDict():
    """
    Create a dictionary using files in matched_folders and metadata matches
    Return: dictionary of format- path(key): (gvkey,company name,year) (value)
    """
    path_dict = {}

    matched_dir = os.path.join(os.getcwd(), "matched_folders")

    for folder in os.listdir(matched_dir):
        folder_path = os.path.join(matched_dir, folder)

        for file in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file)

            with open("metadata.csv", "r") as csvfile:
                reader = csv.reader(csvfile)
                next(reader)  # skip header

                for row in reader:

                    if row[0] == file:  # check for a file path match
                        path_dict[file_path] = (row[1], row[2], row[4])
                        break

    return path_dict


def WriteToExtractedText(formatted_text, val):
    """
    Writes formated_text ot a text file in extracted_text

    Keyword arguments:
    formatted_text-string
    val- tuple of (gvkey,company name, mergent year)
    Return: 0 or 1 depending on write sucess or fail
    """

    # TEMP TO VIEW OUTPUT
    file_name = val[0] + "_" + val[1] + "_" + val[2]
    if file_name + ".txt" not in os.listdir(extracted_text_dir):
        target_path = os.path.join(extracted_text_dir, file_name)
        f = open(target_path, "w")
        f.write(formatted_text)
        f.close()
        return 1
    return 0


def WriteComplexity(val, complexity):
    # Check if file exists
    temp = [str(val[0]), str(val[1]), str(val[2])]

    with open("./complexities.csv", "r", newline="") as file:
        reader = csv.reader(file)
        for row in reader:
            if row[:-1] == temp:  # if val has been written, we will not change
                return 0
    # If file doesnt exist, append
    with open("./complexities.csv", "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(temp.append(str(complexity)))


def main():

    server, model = OCRSetup("linknet_resnet18")

    path_dict = CreatePathDict()
    print(path_dict)

    ResetIndex(True)
    starting_index, ending_index = GetIndices(len(path_dict))

    curr_firm = 1
    with alive_bar(len(path_dict)) as bar:
        bar.text("Starting...")
        bar()

        for key, val in path_dict.items():

            if (curr_firm >= starting_index) and (curr_firm <= ending_index):
                doc = DocumentFile.from_pdf(key)
                result = model(doc)
                formatted_text = FormatResult(result)

                write_complete = WriteToExtractedText(
                    formatted_text, val
                )  # write_complete 0 or 1 depending if file already parsed
                if write_complete == 1:
                    WriteComplexity(val, GetICGaugeScore(formatted_text))
                StoreIndex(curr_firm)

        curr_firm += 1
        bar()

    server.terminate()


if __name__ == "__main__":

    main()
