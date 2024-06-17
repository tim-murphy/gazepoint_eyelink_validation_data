import csv
from kneed import KneeLocator
from math import sqrt
import matplotlib.pyplot as plt
from numpy import argsort, mean
import os
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import sys

from ExperimentResults import ALL_STUDIES

BOTTOM="Bottom"
TOP="Top"
POSITIONS_POS = (BOTTOM, TOP)

NEAR="near_chinrest"
MID="mid_chinrest"
UNRESTRICTED="mid_unrestricted"
FAR="far_chinrest"
POSITIONS_VAL = (FAR, MID, UNRESTRICTED, NEAR)

SHOW_SCATTER_PLOT = False

# If True, will not display scatter plot properly. Not fixing as this is for
# debugging purposes only.
SHOW_SSE_PLOT = False

PLOT_SIZE=(1350, 600)
PLOT_DPI=125

SEED=3142 #93 # make sure we get the same results every time we run this script

CHROMATIC_PLOT=True

def loadTargetStats(target_stats_csv):
    # paranoia
    if not os.path.exists(target_stats_csv):
        print("ERROR: target stats CSV file does not exist: " + target_stats_csv, file=sys.stderr)
        sys.exit(1)

    raw_data = []
    with open(target_stats_csv) as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            raw_data.append(row)

    return raw_data

def runKMeans(input_data, num_clusters, seed=SEED):
    kmeans = KMeans(init="random", n_clusters=num_clusters, n_init=10, max_iter=300, random_state=seed)
    kmeans.fit(acc_prec_data_scaled[pos])
    return kmeans

if __name__ == '__main__':
    def printUsage():
        print("Usage: " + sys.argv[0] + " <target_stats_csv> <project> " +
              "<outfile_csv> <outfile_png> [<study=" + ALL_STUDIES[1] + ">]")

    if len(sys.argv) < 5:
        printUsage()
        sys.exit(1)

    target_stats_csv = sys.argv[1]
    if not os.path.exists(target_stats_csv):
        print("ERROR: target stats CSV file does not exist: " + target_stats_csv, file=sys.stderr)
        sys.exit(1)

    project = sys.argv[2]
    outfile = sys.argv[3]
    outpng = sys.argv[4]

    study = ALL_STUDIES[1]
    if len(sys.argv) > 5:
        study = sys.argv[5]

    if not study in ALL_STUDIES:
        print("ERROR: invalid study:", study)
        sys.exit(1)

    ALL_POSITIONS = POSITIONS_VAL
    if study == ALL_STUDIES[0]:
        ALL_POSITIONS = POSITIONS_POS

    # load the data
    # headers: Target,Bottom_Accuracy,Bottom_Precision,Bottom_Invalid,Top_Accuracy,Top_Precision,Top_Invalid
    raw_data = loadTargetStats(target_stats_csv)

    # cluster accuracy/precision
    acc_prec_data = {}
    acc_prec_data_scaled = {}

    for pos in ALL_POSITIONS:
        acc_prec_data[pos] = []
        acc_prec_data_scaled[pos] = []

    plotDims = (1, len(ALL_POSITIONS))
    fig = plt.figure(figsize=(PLOT_SIZE[0]/PLOT_DPI, PLOT_SIZE[1]/PLOT_DPI), dpi=PLOT_DPI)
    # fig.suptitle("Accuracy, precision and invalid readings per target", fontsize=20)

    with open(outfile, 'w') as out_csv:
        for plotIndex, pos in enumerate(ALL_POSITIONS):
            print("===================")
            print(pos)
            print("===================")
            scatter_data = [[],[],[]]
            for row in raw_data:
                raw_x = row[pos + '_Accuracy']
                raw_y = row[pos + '_Precision']
                raw_z = row[pos + '_Invalid']
                acc_prec_data[pos].append([raw_x, raw_y, raw_z])
                scatter_data[0].append(float(raw_x))
                scatter_data[1].append(float(raw_y))
                scatter_data[2].append(int(raw_z))

            # scale
            acc_prec_data_scaled[pos] = StandardScaler().fit_transform(acc_prec_data[pos])

            sse = [[],[]]
            clust_min = 2
            clust_max = 10
            for num_clusters in range(clust_min, clust_max+1):
                kmeans = runKMeans(acc_prec_data_scaled[pos], num_clusters)
                sse[0].append(num_clusters)
                sse[1].append(kmeans.inertia_)

            # find the knee to determine cluster size
            kl = KneeLocator(*sse, curve="convex", direction="decreasing")
            ideal_clusters = kl.elbow

            # plot the num clusters per SSE and highlight the elbow
            if SHOW_SSE_PLOT:
                plt.plot(*sse)
                plt.scatter([ideal_clusters], [sse[1][ideal_clusters - clust_min]], marker="+", s=200, color="black")
                plt.title("Elbow Method for Cluster Determination: " + pos)
                plt.xlabel("Number of Clusters")
                plt.ylabel("SSE")
                plt.show()
                plt.close()

            # plot the data
            kmeans = runKMeans(acc_prec_data_scaled[pos], ideal_clusters)
            data_cluster = []

            # order the groups by distance from the origin
            # This is a bit messy. First, gather all the points in the cluster.
            # Next, calculate the mean distance for each cluster.
            # Then order the clusters by distance.
            num_groups = max(kmeans.labels_) + 1

            group_raw = []
            for i in range(num_groups):
                group_raw.append([])

            for i in range(len(scatter_data[0])):
                # distance from origin = sqrt(x^2 + y^2 + z^2)
                dist = sqrt(scatter_data[0][i]**2 + scatter_data[1][i]**2 + scatter_data[2][i]**2)
                group = kmeans.labels_[i]
                group_raw[group].append(dist)

            group_means = [None] * num_groups
            for i in range(len(group_raw)):
                group_means[i] = mean(group_raw[i])

            sorted_group_means = argsort(argsort(group_means))

            if CHROMATIC_PLOT:
                # re-assign cluster number per distance from origin
                for i in range(len(kmeans.labels_)):
                    data_cluster.append(sorted_group_means[kmeans.labels_[i]])
            else:
                data_cluster = kmeans.labels_

            ax = fig.add_subplot(*plotDims, plotIndex + 1, projection='3d')
            # ax.set_title(pos + " position", fontsize=15)
            ax.scatter(*scatter_data, c=data_cluster)
            ax.set_xlabel("Accuracy in degrees")
            ax.set_ylabel("Precision in degrees")
            ax.set_zlabel("Invalid Readings")

            # show the clusters
            clusters = [[] for i in range(ideal_clusters)]
            for index, cluster in enumerate(kmeans.labels_):
                if index % 6 == 5:
                    print(cluster)
                else:
                    print(cluster, end=" ")

                # if not cluster in clusters:
                    # clusters[cluster] = []

                clusters[cluster].append(index)

            print("")
            best_group = list(sorted_group_means).index(0)

            # write out results to file
            print(pos, *clusters[best_group], sep=",", file=out_csv)

        plt.tight_layout()
        plt.savefig(outpng)

        if SHOW_SCATTER_PLOT:
            plt.show()

        plt.close()

# EOF
