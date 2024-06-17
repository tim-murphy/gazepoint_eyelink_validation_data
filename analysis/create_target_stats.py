# Take a stats file (like [proj]\all\plots\position_vector.png.stats.csv) and
# convert it into a format which can be used by cluster_targets.py, and can
# be copied into a manuscript.

import csv
import os
import sys

from ExperimentResults import ALL_STUDIES

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage:", sys.argv[0], "<input_stats_csv> <output_csv>",
              "[<study=" + ALL_STUDIES[1] + ">]")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2]

    study = ALL_STUDIES[1]
    positions = ("far_chinrest", "mid_chinrest", "mid_unrestricted", "near_chinrest")
    if len(sys.argv) > 3:
        study = sys.argv[3]

        if study == ALL_STUDIES[0]:
            positions = ("Top", "Bottom")

    # error checking
    if not os.path.exists(input_csv):
        print("ERROR: input csv file does not exist:", input_csv, file=sys.stderr)
        sys.exit(1)

    if not study in ALL_STUDIES:
        print("ERROR: invalid study:", study, file=sys.stderr)
        sys.exit(1)

    # retrieve the stats
    targStats = {}
    with open(input_csv, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # we want individual stats only
            if row['target_id'] == "all":
                continue

            target = int(row['target_id'])
            accuracy = float(row['accuracy_deg'])
            precision = float(row['precision_deg'])
            bad = int(row['bad_both'])
            label = row['label'].split()[-1] # remove the "Gazepoint GP3 :: [mf -]" bits

            if not target in targStats:
                targStats[target] = {}

            targStats[target][label] = {'accuracy': accuracy,\
                                        'precision': precision,\
                                        'bad': bad }

    # write the data to a new file
    with open(output_csv, 'w') as outfile:
        header = "Target"
        for p in positions:
            for stat in ("Accuracy", "Precision", "Invalid"):
                header += "," + p + "_" + stat

        print(header, file=outfile)

        for target, stats in targStats.items():
            line_data = [target]
            for pos in positions:
                for stat in ("accuracy", "precision", "bad"):
                    line_data.append(stats[pos][stat])

            print(*line_data, sep=",", file=outfile)

    print("Done. File written to", output_csv)

# EOF
