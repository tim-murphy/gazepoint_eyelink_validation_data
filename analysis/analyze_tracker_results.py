# Take a CSV file for a single or multiple subjects and do the following:
#  - graph the points, with different sets for each label/tracker pair
#  - calculate the accuracy
#  - calculate the precision

import csv
import matplotlib.pyplot as plt
import os
import sys

from ExperimentResults import ExperimentResults
from ExperimentPlot import ExperimentPlot, GRAPH_TYPES, SCATTER_PLOT, VECTOR_PLOT, PLOT_DPI

PLOT_SIZE = (1920, 1080)

SPLIT_VECTOR_PLOTS = True

# target subsets
TARGETS_ALL = range(36)

def printUsage():
    print("Usage: " + sys.argv[0] + " <data_csv> [<(scatter|vector)=scatter> [<distance_cm=None> [<graph_output_png=None>] [<participant=None> [<subset_file=None>]]]]")

if __name__ == '__main__':
    print("==========================================")
    print("  Data analysis for eye tracking results")
    print("==========================================")
    print("")

    # parse command line arguments
    if len(sys.argv) < 2:
        printUsage()
        sys.exit(1)

    data_csv = sys.argv[1]
    graph_output_png = None

    graph_type = GRAPH_TYPES[0]
    if len(sys.argv) > 2:
        graph_type = sys.argv[2]

    distance_cm = None
    if len(sys.argv) > 3:
        distance_cm = int(sys.argv[3])

    if len(sys.argv) > 4:
        graph_output_png = sys.argv[4]

        if os.path.exists(graph_output_png):
            response = None
            while response not in ("y", "n"):
                response = input("WARNING: The graph output path \"" +\
                                 graph_output_png + "\" already exists. Would "\
                                 "you like to overwrite it? [y/n]: ").lower()

            if response == "n":
                print("Exiting")
                sys.exit(1)
            else:
                print("File will be overwritten")

    participant = None
    if len(sys.argv) > 5:
        participant = sys.argv[5]
        if participant == "None":
            participant = None

    targets = [TARGETS_ALL, TARGETS_ALL]
    if len(sys.argv) > 6:
        subset_file = sys.argv[6]
        if not os.path.exists(subset_file):
            print("ERROR: subset file does not exist:", sys.argv[6])
            printUsage()
            sys.exit(1)

        # grab the targets out of the file
        with open(subset_file, 'r') as targfile:
            reader = csv.reader(targfile)
            for row in list(reader):
                if row[0].lower() == "top":
                    targets[0] = list(int(i) for i in row[1:])
                elif row[0].lower() == "bottom":
                    targets[1] = list(int(i) for i in row[1:])

    # error checking
    if not os.path.exists(data_csv):
        print("ERROR: data file does not exist: " + data_csv)
        printUsage()
        sys.exit(1)

    if graph_type not in GRAPH_TYPES:
        print("ERROR: invalid graph type: " + graph_type)
        printUsage()
        sys.exit(1)

    #################################
    ## Data extraction starts here ##
    #################################

    print("Using input file: " + data_csv)

    if graph_output_png is None:
        print("Displaying output on screen")
    else:
        print("Writing output to: " + graph_output_png)

    ex_data = ExperimentResults(data_csv, PLOT_SIZE,
                                targets_bottom=targets[1],
                                targets_top=targets[0])

    if len(ex_data.subject_data) == 0:
        print("ERROR: no subject data found", file=sys.stderr)
        sys.exit(1)

    subject = None
    if len(ex_data.subject_data) == 1:
        subject = list(ex_data.subject_data.keys())[0]

    print(str(len(ex_data.raw_data) - len(ex_data.invalid_rows)) + " data rows found")
    print(str(len(ex_data.bad_data)) + " invalid rows found")

    ##########################
    ## Plotting starts here ##
    ##########################

    ex_plot = ExperimentPlot(ex_data)

    # if manually adding a legend, add the records here
    legend_elements = None
    if graph_type == SCATTER_PLOT:
        ex_plot.plotScatter(subject)
    elif graph_type == VECTOR_PLOT:
        ex_plot.plotVector(subject, split=SPLIT_VECTOR_PLOTS, distance_cm=distance_cm, outname=graph_output_png)
    else:
        # this should never happen
        print("ERROR: invalid graph type: " + graph_type)
        printUsage()
        sys.exit(1)

    # add a polar grid over the top
    # if distance_cm is not None:
        # ex_plot.plotPolarGrid(distance_cm)

    stats_raw = ex_plot.plotStats(subject, distance_cm=distance_cm, participant=participant)

    if graph_output_png is None:
        plt.show()
        if stats_raw is not None:
            print(stats_raw)
    else:
        # print("Writing plot to file")
        # plt.tight_layout()
        # plt.savefig(graph_output_png, dpi=PLOT_DPI)

        print("Writing stats to file")
        with open(graph_output_png + ".stats.csv", 'w+') as f:
            f.write(stats_raw)

    plt.close()

    print("Finished. Have a nice day :)")

# EOF
