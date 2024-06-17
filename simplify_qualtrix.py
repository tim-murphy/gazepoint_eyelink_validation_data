import csv
import os
import re
from statistics import mean
import sys
from types import FunctionType

# regular expression for spectacle prescription (as used by me for this study)
# returns four groups: sphere, cyl, axis, add
RX_REGEX = r'(pl|[+-]\d+\.\d\d)(?:/([+-]\d+\.\d\d)x(\d+))?(?: \([+](\d+\.\d\d)\))?'
RX_SPHERE = 1
RX_CYL = 2
RX_AXIS = 3
RX_ADD = 4

# regular expression for pantoscopic tilt - forgot to put this as a separate
# question on the survey, and now we're paying for my oversight :(
PANTO_REGEX = r'[Pp]anto:[ ]?([-]?\d+)'
PANTO_VAL = 1

# study particulars
ALL_STUDIES = ("position", "validation")
TEST_ID = 1

# clean up the correction format
def getCorrection(row):
    corr = row['Correction']
    if corr ==  "Spectacles - single vision":
        return "Single Vision"
    elif corr == "Spectacles - multifocal / varifocal / occupational":
        return "Multifocal"
    elif corr in ("Contact lenses - soft", "None"):
        return corr
    else:
        raise ValueError("Invalid correction type: " + str(corr))

# posture type selection from Howell-Dwyer or Cover Test
def getPosture(postureType, hd, ct):
    if postureType == "Howell-Dwyer":
        return float(hd)
    elif postureType == "Cover Test":
        return float(ct)
    else:
        raise ValueError("postureType must be 'Howell-Dwyer' or 'Cover Test'" +
                         ", not '" + str(postureType) + "'")

def getPosture33cm(row):
    return getPosture(row['Posture33cm'],
                      row['Posture33cm_1_TEXT'],
                      row['Posture33cm_2_TEXT'])

def getPosture3m(row):
    return getPosture(row['Posture3m'],
                      row['Posture3m_1_TEXT'],
                      row['Posture3m_2_TEXT'])

def getAR(row):
    if row['Correction'] == 'None':
        return ""
    return (1 if "Has AR coating" in row['Vert'] else 0)

def getRxVals(row):
    vals = {RX_SPHERE: [], RX_CYL: [], RX_AXIS: [], RX_ADD: []}
    for side in range(1, 3):
        match = re.search(RX_REGEX, row['Vert_' + str(side) + '_TEXT'])

        for index in (RX_SPHERE, RX_CYL, RX_AXIS, RX_ADD):
            if match is None:
                vals[index].append(0.0)
                continue

            val = match.group(index)
            if val is not None:
                # pl == plano == 0
                if val == 'pl':
                    val = 0.0
                vals[index].append(float(val))
            else:
                vals[index].append(0.0)

    return vals

def getSpherical(row):
    rxVals = getRxVals(row)
    if len(rxVals[RX_SPHERE]) == 0:
        # no specs
        return ""

    return mean(rxVals[RX_SPHERE]) + (mean(rxVals[RX_CYL]) / 2.0)

def getAdd(row):
    adds = getRxVals(row)[RX_ADD]
    if mean(adds) == 0:
        return ""
    return mean(adds)

def getPanto(row):
    match = re.search(PANTO_REGEX, row['Vert_4_TEXT'])
    if match is None:
        return ""

    return int(match.group(PANTO_VAL))

# column name: data source
# if data source is a string, use that column
# if data source is a method, that method is called using the row data
DATA_COLS_POS = {"ID": "ID",
                 "EyeColour": "EyeColour",
                 "Correction": getCorrection,
                 "EyeConditions": "EyeConditions",
                 "Posture3m": "Posture3m",
                 "Posture3mVal": getPosture3m,
                 "Posture33cm": "Posture33cm",
                 "Posture33cmVal": getPosture33cm,
                 "HasARCoat": getAR,
                 "VertRight": "Vert_1_TEXT",
                 "VertLeft": "Vert_2_TEXT",
                 "SphericalDistRx": getSpherical,
                 "MFAdd": getAdd,
                 "Panto": getPanto,
                 "ValidationErrorsTop": "Q8",
                 "ValidationErrorsBottom": "Q9"}

DATA_COLS_VAL = {"ID": "ID",
                 "EyeColour": "EyeColour",
                 "Correction": getCorrection,
                 "EyeConditions": "EyeConditions",
                 "Posture3m": "Posture3m",
                 "Posture3mVal": getPosture3m,
                 "Posture33cm": "Posture33cm",
                 "Posture33cmVal": getPosture33cm,
                 "HasARCoat": getAR,
                 "VertRight": "Vert_1_TEXT",
                 "VertLeft": "Vert_2_TEXT",
                 "SphericalDistRx": getSpherical,
                 "MFAdd": getAdd,
                 "Panto": getPanto}

def printUsage():
    print("Usage:", sys.argv[0], "<qualtrix_orig_csv>", "<output_csv>",
          "[<study=" + ALL_STUDIES[1] + ">]")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        printUsage()
        sys.exit(1)

    orig_csv = sys.argv[1]
    out_csv = sys.argv[2]

    study = ALL_STUDIES[1]
    if len(sys.argv) > 3:
        study = sys.argv[3]

    args_ok = True
    if not os.path.exists(orig_csv):
        print("ERROR: <qualtrix_orig_csv> does not exist:", orig_csv, file=sys.stderr)
        args_ok = False

    if orig_csv == out_csv:
        print("ERROR: input and output files cannot be the same", file=sys.stderr)
        args_ok = False

    if study not in ALL_STUDIES:
        print("ERROR: invalid study: must be", "or".join(ALL_STUDIES), "::", study)
        args_ok = False

    if not args_ok:
        printUsage()
        sys.exit(1)

    DATA_COLS = DATA_COLS_VAL
    if study == ALL_STUDIES[0]:
        DATA_COLS = DATA_COLS_POS

    new_data = []

    with open(orig_csv, 'r') as csvfile:
        reader = csv.DictReader(csvfile)

        # skip first two rows after the header - irrelevant metadata
        next(reader)
        next(reader)

        for row in reader:
            if int(row['ID']) == TEST_ID:
                continue

            new_row = {}

            for col_name, source in DATA_COLS.items():
                if isinstance(source, str):
                    new_row[col_name] = "\"" + row[source] + "\""
                elif isinstance(source, FunctionType):
                    new_row[col_name] = "\"" + str(source(row)) + "\""
                else:
                    raise ValueError("Data source is not a function: " +\
                                     str(source) + " (" + str(type(source)) +\
                                     ") for column: " + str(col_name))

            new_data.append(new_row)

    # write to our new file
    with open(out_csv, 'w') as outfile:
        print(*DATA_COLS.keys(), sep=",", file=outfile)

        for row in new_data:
            for col_name in DATA_COLS.keys():
                if col_name != list(DATA_COLS.keys())[0]:
                    print(",", end="", file=outfile)
                print(row[col_name], end="", file=outfile)
            print("", file=outfile)

# EOF
