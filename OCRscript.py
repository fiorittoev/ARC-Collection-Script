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
import scipy
from nltk.parse.corenlp import CoreNLPParser
from icgauge import experiment_frameworks
from doctr.models import ocr_predictor
from doctr.io import DocumentFile
from random import randint


def OCRSetup():
    """
    Creates neccesary environment for NLP and OCR processes to run

    Return: server- subprocess running nlp server,model- OCR prediction model for pdfs
    """

    # Define model for docTR ocr
    model = ocr_predictor(
        "linknet_resnet18",  # link_resnet18" for rotated files
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
        if len(paragraphs) > 10:
            break

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


def main():

    server, model = OCRSetup()

    # Temporary hardcode for one file, scale for all found_firms.csv?
    doc = DocumentFile.from_pdf(
        "D:/ARC-Collection-Script/folders/1013_ADC-TELECOMMUNICATIONS-INC_1996_2001_1/334345_1.pdf"
    )

    result = model(doc)
    out = result.render()

    # TEMP TO VIEW OUTPUT
    f = open("temp.txt", "w")
    f.write(out)
    f.close()

    complexity = GetICGaugeScore(out)
    print(complexity)

    server.terminate()


if __name__ == "__main__":
    main()
