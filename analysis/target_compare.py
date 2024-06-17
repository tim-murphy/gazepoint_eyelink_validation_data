from copy import deepcopy
import csv
import os
from scipy import stats
import sys

from create_extra_graphs import kruskalTest

def printUsage():
    print("Usage:", sys.argv[0], "<target_csv>")

def loadData(data_csv):
    if not os.path.exists(data_csv):
        print("ERROR: target csv file does not exist:", data_csv, file=sys.stderr)
        sys.exit(1)

    loaded_data = {}
    with open(data_csv, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        loaded_data = deepcopy(list(reader))

    return loaded_data

if __name__ == '__main__':
    if len(sys.argv) < 2:
        printUsage()
        sys.exit(1)

    target_csv = sys.argv[1]
    target_data = loadData(target_csv)

    # compare accuracy, precision and invalid readings from top and bottom
    for pos in ('Top', 'Bottom'):
        for stat in ('Accuracy', 'Precision', 'Invalid'):
            # edge vs. inner targets
            outer = []
            inner = []
 
            # top/bottom vs. other rows
            top_bottom = []
            not_top_bottom = []

            # invalid per row
            invalid_per_row = {}
            for targ_index, row in enumerate(target_data):
                stat_value = float(row[pos + "_" + stat])
                row_id = targ_index % 6

                if int(row['Target']) % 6 in (0, 5):
                    outer.append(stat_value)
                else:
                    inner.append(stat_value)

                if pos == 'Bottom' and int(row['Target']) < 6:
                    top_bottom.append(stat_value)
                elif pos == 'Top' and int(row['Target']) > 29:
                    top_bottom.append(stat_value)
                else:
                    not_top_bottom.append(stat_value)

                if stat == "Invalid":
                    if not row_id in invalid_per_row:
                        invalid_per_row[row_id] = []

                    invalid_per_row[row_id].append(int(row[pos + "_" + stat]))

            print("###", pos, stat)
            print("inner vs. outer")
            kruskalTest([inner, outer])
            print("")
            print("top/bottom vs. rest")
            kruskalTest([top_bottom, not_top_bottom])
            print("")
            if stat == "Invalid":
                invalid_scatter = [[],[]] # x and y coords for scatter
                for row, vals in invalid_per_row.items():
                    invalid_scatter[0].append(row)
                    invalid_scatter[1].append(sum(vals))

                print("Invalid per row")
                print(stats.spearmanr(*invalid_scatter))
                print("")

# EOF
