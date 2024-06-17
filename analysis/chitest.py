import csv
import os
from scipy.stats import chisquare
import sys

# tracker positions
TOP = 'Top Position'
BOTTOM = 'Bottom Position'
DF = 'Degrees of Freedom'
TOTAL = 'Total Records'

def printUsage():
    print("Usage:", sys.argv[0], "<all_stats_csv>")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        printUsage()
        sys.exit(1)

    # load the data
    target_data = sys.argv[1]
    if not os.path.exists(target_data):
        print("ERROR: stats file does not exist:", target_data, file=sys.stderr)
        printUsage()
        sys.exit(1)

    stats_summary = {'invalid_both': 0, 'invalid_right': 0, 'invalid_left': 0,
                     'valid': 0}
    with open(target_data, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stats['target'].append(int(row['Target']))

            
            stats['invalid_top'].append(int(row['Top_Invalid']))
            stats['invalid_bottom'].append(int(row['Bottom_Invalid']))

    print(stats)
    sys.exit(1)
    
# row data is invalid_both, invalid_right, invalid_left, valid

## ALL TARGETS ##
allTotalRecords = {TOP: 2520, BOTTOM: 2448}

allSubjects = {TOP: [[539, 282, 244, 1455]],\
               BOTTOM: [[149, 187, 147, 1965]]}

allCorrection = {TOP: [[256, 83, 106, 635], [140, 127, 49, 404], [143, 72, 89, 416]],\
                 BOTTOM: [[48, 81, 51, 828], [44, 41, 32, 603], [57, 65, 64, 534]]}

allColour = {TOP: [[183, 43, 43, 163], [288, 161, 97, 822], [36, 4, 4, 28], [24, 11, 21, 88], [108, 63, 79, 254]],\
             BOTTOM: [[36, 27, 31, 338], [74, 97, 73, 1052], [2, 5, 3, 62], [3, 13, 13, 115], [34, 45, 27, 398]]}

## IDEAL POSITION ##
idealTotalRecords = {TOP: 840, BOTTOM: 884}

idealSubjects = {TOP: [[48, 63, 52, 677]],\
                 BOTTOM: [[10, 7, 7, 860]]}

idealCorrection = {TOP: [[29, 17, 16, 298], [10, 24, 10, 196], [9, 22, 26, 183]],\
                   BOTTOM: [[4, 4, 3, 353], [3, 0, 0, 257], [3, 3, 4, 250]]}

idealColour = {TOP: [[3, 15, 5, 121], [26, 31, 21, 378], [5, 1, 2, 16], [0, 2, 2, 44], [14, 14, 22, 118]],\
               BOTTOM: [[2, 2, 2, 150], [8, 2, 3, 455], [0, 0, 0, 26], [0, 0, 1, 51], [0, 3, 1, 178]]}

# make the collections
allData = {'All subjects': allSubjects,\
           'Correction': allCorrection,\
           'Eye Colour': allColour,\
            TOTAL: allTotalRecords}

idealData = {'All subjects': idealSubjects,\
             'Correction': idealCorrection,\
             'Eye Colour': idealColour,\
              TOTAL: idealTotalRecords}

# sanity check
for (datasetname, dataset) in (('allData', allData), ('idealData', idealData)):
    for label, dat in dataset.items():
        if label == TOTAL:
            continue
        for pos, vals in dat.items():
            countTotal = 0
            for row in vals:
                countTotal += sum(row)

            if countTotal != dataset[TOTAL][pos]:
                print("Invalid table data for", datasetname, "::", label, "::", pos,\
                      ": expecting", dataset[TOTAL][pos],\
                      "records, found", countTotal)
                print(vals)

        print(datasetname, "::", label)
        print(chisquare(dat[TOP], dat[BOTTOM], axis=None))

        # chi-square for top vs. bottom for each category
        vals_top = dat[TOP]
        vals_bottom = dat[BOTTOM]
        assert(len(vals_top) == len(vals_bottom))
        for i in range(len(vals_top)):
            print("chi:", datasetname, "##", label, i)
            print(chisquare(vals_top[i], vals_bottom[i], axis=None))

        print("")
            
# EOF
