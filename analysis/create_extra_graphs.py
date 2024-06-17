import matplotlib.cm as pltcm
import matplotlib.colors as pltcolors
import matplotlib.pyplot as plt
import numpy as np
import os
import pandas as pd
from scikit_posthocs import posthoc_dunn
from scipy import stats
from statistics import pstdev, median
import sys

from CollatedStats import CollatedStats
from ExperimentResults import INVALID_COORD, ALL_STUDIES

# print full pandas DataTable instead of truncating
pd.set_option('display.max_columns', None)
pd.set_option('display.max_colwidth', None)
pd.set_option('display.width', 1000)

SHOW_PLOTS=False
PLOT_SIZE=(1280, 640)
PLOT_DPI=125
COLOURMAP="Paired"

TITLE_FONTSIZE='large'
SUPTITLE_FONTSIZE=30

# mapping from attribute to label
attribLabel = {
    None: "<unknown>",
    "eyeColour": "Eye colour",
    "eyesBlue": "Blue eyes",
    "eyesDark": "Eye Darkness",
    "correction": "Spectacle type",
    "panto": "Pantoscopic tilt in degrees",
    "posture33cm": "Vergence posture at 33cm",
    "posture3m": "Vergence posture at 3m"
}

# labels to use throughout the stats, for consistency (and to avoid typos)
ACCURACY = 'Accuracy'
PRECISION = 'Precision'
SPECRX = 'Spectacle_Rx'

# magic numbers for stat detail indices
NUM_OBS_IDX = 0
MEAN_IDX = 2
VARIANCE_IDX = 3

# create a scatterplot of spectacle Rx vs accuracy and precision
def plotRxStats(allStats, project, addLegend=True):
    # create three lists: specRx, accuracy, and precision. This is the
    # easiest way to plot with matplotlib
    # split this by label
    chartData = {}

    for (p, d) in allStats.participantData.items():
        # only use if this is a spec record
        if d.vertRight == "" and d.vertLeft == "":
            continue

        # find the records for all targets
        dataFound = False
        for row in d.targetStats:
            if row.targetID != "all":
                continue

            # we found one!
            dataFound = True

            if row.label not in chartData:
                chartData[row.label] = { 'ids': [], SPECRX: [], ACCURACY: [], PRECISION: [] }
            
            chartData[row.label]['ids'].append(d.id) # mostly for testing
            chartData[row.label][SPECRX].append(d.sphericalDistRx)
            chartData[row.label][ACCURACY].append(row.accuracyDeg)
            chartData[row.label][PRECISION].append(row.precisionDeg)

        if not dataFound:
            print("ERROR: could not find 'all' stats for participant", p, file=sys.stderr)
            print(d.targetStats, file=sys.stderr)

    # set up the canvas
    plt.rcParams["figure.figsize"] = (PLOT_SIZE[0]/PLOT_DPI, PLOT_SIZE[1]/PLOT_DPI)
    plt.rcParams["figure.dpi"] = PLOT_DPI

    # plot the data
    fig, axs = plt.subplots(1,2)
    print(" === Spectacle Rx stats for", project, "(stat vs. power) ===")
    for label, datasets in chartData.items():
        for i, l in enumerate((ACCURACY, PRECISION)):
            y = np.array(datasets[l])
            x = datasets[SPECRX]
            m, b = np.polyfit(x, y, 1) # generate y=mx+b formula
            y_slope = [x_element * m for x_element in x]
            axs[i].plot(x, y_slope + b)
            axs[i].scatter(x, y, label=label)
            axs[i].set(xlabel="Spectacle strength in diopters (average spherical equivalent)",\
                       ylabel=l + " in degrees")

        acc = stats.spearmanr(datasets[SPECRX], datasets[ACCURACY])
        prec = stats.spearmanr(datasets[SPECRX], datasets[PRECISION])
        df = len(datasets[SPECRX]) - 2

        print("  ====", label, "====")
        for l,s in ((ACCURACY, acc), (PRECISION, prec)):
            print("    ", l, ": SpearmanR=", s.statistic, ", p=", s.pvalue, " (df=", df, ")", sep="")
            if s.pvalue < 0.05:
                print("        !!! SIGNIFICANT !!!")
        print("")
        
    # fig.suptitle("Accuracy and Precision per Spectacle Power", fontsize=SUPTITLE_FONTSIZE)

    # shrink plot area and place legend above the plot
    if addLegend:
        for ax in axs:
            ax.legend(loc='upper right') # FIXME , bbox_to_anchor=(0.5, 1.1))

    plt.tight_layout()
    plt.savefig(os.path.join(project, "all", "plots", project + "_Rx_scatter.png"))

    if SHOW_PLOTS:
        plt.show()

    plt.close()

def mannWhitneyTest(datasets, prefix=""):
    mannwhitney = stats.mannwhitneyu(*datasets)
    print(prefix, mannwhitney, sep="")
    if mannwhitney.pvalue < 0.05:
        print(prefix, "!!! SIGNIFICANT RESULT: SAMPLES ARE DIFFERENT !!!", sep="")
    else:
        print(prefix, "non-significant result: samples are not different", sep="")

def kruskalTest(dataset_dict, prefix=""):
    # make sure the keys and values are ordered correctly
    vals = []
    keys = []

    for k,v in dataset_dict.items():
        keys.append(k)
        vals.append(v)
        print(" ", k, "::", stats.describe(v))
    print("")

    kruskal = stats.kruskal(*vals)
    print(prefix, kruskal, sep="")
    if kruskal.pvalue < 0.05:
        print(prefix, "!!! SIGNIFICANT RESULT: SAMPLES ARE DIFFERENT !!!", sep="")
        print(prefix, "Posthoc Dunn test (Bonferroni):", sep="")
        dunn = posthoc_dunn(vals, p_adjust='bonferroni')
        for a in (0,1):
            dunn.set_axis(keys, axis=a)
        print(dunn)
        print("")
    else:
        print(prefix, "non-significant result: samples are not different", sep="")

def confidenceInterval(dataset, confidence=0.95, prefix=""):
    mean = np.mean(dataset)
    sem = stats.sem(dataset)
    ci = stats.t.interval(confidence, len(dataset)-1, loc=mean, scale=sem)
    print(prefix, "SEM=", str(sem), " ", int(confidence * 100), "% CI: ", str(ci), sep="")
    return (np.mean(dataset), sem)

def confidenceIntervals(datasets, confidence=0.95, prefix=""):
    for n, (lab, dat) in enumerate(datasets.items()):
        pre = str(prefix) + str(n+1) + " :: " + str(lab) + ": "
        confidenceInterval(dat, confidence, pre)

def compareSamples(allStats, project, attrib=None, plotTitle="A Nice Plot Title", addLegend=True):
    # compare positions for the given attribute values, or all if None
    datasets = {}

    print(" == Comparing sets within the same tracker setup:", plotTitle, "==")

    counts = {}

    badReads = {}
    for (p, d) in allStats.participantData.items():
        category = "all"
        if attrib != None:
            category = getattr(d, attrib)

        if not category in counts:
            counts[category] = 0
        counts[category] += 1

        if category not in datasets:
            datasets[category] = {ACCURACY: {}, PRECISION: {}}

        for targ in d.targetStats:
            for stat in (ACCURACY, PRECISION):
                if targ.label not in datasets[category][stat]:
                    datasets[category][stat][targ.label] = []

            if not category in badReads:
                badReads[category] = {}

            if not targ.label in badReads[category]:
                badReads[category][targ.label] = {'n': 0, 'one': 0, 'both': 0, 'none': 0}

            if targ.targetID == "all":
                badReads[category][targ.label]['n'] += targ.recordN
                badReads[category][targ.label]['one'] += targ.badReadRight + targ.badReadLeft
                badReads[category][targ.label]['both'] += targ.badReadBoth
                badReads[category][targ.label]['none'] +=\
                    (targ.recordN - targ.badReadLeft - targ.badReadRight - targ.badReadBoth)

            targRawVals = []
            for v in targ.rawDistanceValuesPx:
                if v != INVALID_COORD: # paranoia - this shouldn't happen
                    targRaw = v * d.PxToDegConvFactor
                    datasets[category][ACCURACY][targ.label].append(targRaw)
                    targRawVals.append(targRaw)

            if len(targRawVals) > 0:
                datasets[category][PRECISION][targ.label].append(pstdev(targRawVals))

    print(" === category counts ===")
    print(counts)
    print("")

    print(" === chi-square of bad reads (per position) ===")

    # HACK: compare different trackers in the same position (validation study)
    trackersPerPos = {}

    catVals = {}
    EYE_CATS = ["one eye", "both eyes", "none"]
    for cat, vals in badReads.items():
        print("  ", cat, sep="")

        items = list(list(v.values()) for v in vals.values())
        assert(len(items) >= 2) # sanity check
        catVals[cat] = items[0]

        if len(items) < 2:
            print("    Ignoring category as insufficient data")
            continue

        # collate the values by category
        for i in range(1, len(items)):
            catVals[cat] = [x + y for x, y in zip(items[i], catVals[cat])]

        print("    " + str(['n'] + EYE_CATS))
        for i, (k,v) in enumerate(vals.items()):
            print("    ", k, v, sep="")

            # trackers per position (hack)
            sp = k.split(" :: ")
            if len(sp) == 2:
                if not sp[1] in trackersPerPos:
                    trackersPerPos[sp[1]] = {}

                trackersPerPos[sp[1]][sp[0]] = items[i]

        #chi = stats.chisquare(items[0][1:], items[1][1:], axis=None)
        chi = stats.chisquare([i[1:] for  i in items])

        for i, c in enumerate(EYE_CATS):
            if chi.pvalue[i] < 0.05:
                print("    !!! bad reads (" + c + ") are statistically different !!!")

        print("    n = ", items[0][0], ", m = ", items[1][0], sep="")
        print("    chi = ", chi[0], sep="")
        print("    p = ", chi[1], sep="")

        # now compare each distance
        for pos, posData in trackersPerPos.items():
            chitable = []
            print()
            print(" ", pos)
            for tracker, chiData in posData.items():
                print("  ", tracker)
                chitable.append(chiData)

            chi = stats.chisquare([i[1:] for i in chitable])

            for i, c in enumerate(EYE_CATS):
                if chi.pvalue[i] < 0.05:
                    print("    !!! bad reads (" + c + ") are statistically different !!!")
                    print("    n = ", chitable[0][0], ", m = ", chitable[1][0], sep="")
                    print("    chi = ", chi[0][i], sep="")
                    print("    p = ", chi[1][i], sep="")
                    print("")

    print("")

    # compare categories irrespective of position
    if len(catVals) >= 2:
        print("  All")
        print("    " + str(['n'] + EYE_CATS))
        chitable = []
        for cat, vals in catVals.items():
            print("    " + str([cat] + vals))
            chitable.append(vals[1:])

        chi = stats.chisquare(chitable)
        for i, c in enumerate(EYE_CATS):
            if chi.pvalue[i] < 0.05:
                print("    !!! bad reads (" + c + ") are statistically different !!!")

        print("    chi = ", chi[0], sep="")
        print("    p = ", chi[1], sep="")

    print("")

    bylabel = {ACCURACY: {}, PRECISION: {}} # compare sets with the same label (e.g. all in top position)
    for category, labelstats in datasets.items():
        print(" ===", category, "(per position) ===")
        for stat, labels in labelstats.items():
            print(" === Comparing", stat, "(per position) ===")
            for label, vals in labels.items():
                if len(vals) == 0:
                    continue
                if label not in bylabel[stat]:
                    bylabel[stat][label] = {}
                if category not in bylabel[stat][label]:
                    bylabel[stat][label][category] = []
                bylabel[stat][label][category] += vals
                stat_details = stats.describe(vals)

                print("    ", label, " :: n=", stat_details[NUM_OBS_IDX],\
                      ", mean=", stat_details[MEAN_IDX],\
                      ", median=", median(vals),\
                      ", variance=", stat_details[VARIANCE_IDX], sep="")
                confidenceInterval(vals, prefix="      Confidence: ")

            if len(labels) == 0:
                continue

            print("")
            if len(labels.values()) < 2:
                print("  << no stats can be done as two groups needed, only have one >>")
            elif len(labels.values()) == 2:
                mannWhitneyTest(labels.values(), prefix="    ")
            else:
                kruskalTest(labels, prefix="    ")
                print("    Confidences:")
                confidenceIntervals(labels, prefix="      ")
            
            print("")

    if len(datasets) > 1: # this means we have more than one category
        print("#############################")
        print(plotTitle)
        print("#############################")
        print("")

        # set up the canvas
        plt.rcParams["figure.figsize"] = (PLOT_SIZE[0]/PLOT_DPI, PLOT_SIZE[1]/PLOT_DPI)
        plt.rcParams["figure.dpi"] = PLOT_DPI

        errorbardata = {}    # data to be processed here (summary data)
        errorbaroutdata = [['label', 'stat', 'category', 'values']] # data to be written to file
        for stat, labels in bylabel.items():
            for label, cats in labels.items():
                print(" ##", label, "::", stat, "##")
                print("")
                if not label in errorbardata:
                    errorbardata[label] = {ACCURACY: [[],[],[]], PRECISION: [[],[],[]]} # x, y, error

                for index, (cat, vals) in enumerate(cats.items()):
                    if cat is None:
                        continue

                    errorbaroutdata.append([label, stat, cat, ",".join(str(v) for v in vals)])

                    stat_details = stats.describe(vals)
                    print("  ", (index + 1), " (", cat, ") ::",\
                          " n=", stat_details[NUM_OBS_IDX],\
                          ", mean=", stat_details[MEAN_IDX],\
                          ", median=", median(vals),\
                          ", variance=", stat_details[VARIANCE_IDX],\
                          ", SD=", pstdev(vals),\
                          ", skew=", stats.skew(vals), sep="")
                    ci = confidenceInterval(vals, prefix="    Confidence: ")
                    errorbardata[label][stat][0].append(cat)
                    errorbardata[label][stat][1].append(ci[0])
                    errorbardata[label][stat][2].append(ci[1])

                print("")
                if len(cats.values()) == 2:
                    mannWhitneyTest(cats.values(), prefix="    ")
                else:
                    kruskalTest(cats, prefix="    ")
                print("    Confidences:")
                confidenceIntervals(cats, prefix="      ")
                print("")
                print("#############################")
                print("")


        plotDims = (1,2)
        axs = [None, None]
        for index, title in ((0, ACCURACY), (1, PRECISION)):
            axs[index] = plt.subplot(*plotDims, index+1)
            # plt.title(title, fontsize=TITLE_FONTSIZE)
            plt.xlabel(attribLabel[attrib])
            plt.ylabel(title + " in degrees")

        print(" ## Linear Regressions", "::", plotTitle, "##")

        for cnum, (label, datStats) in enumerate(errorbardata.items()):
            print("  ###", label, "###")

            index = 0
            for stat, dat in datStats.items():
                col = "C" + str(cnum)
                axs[index].errorbar(*dat, linestyle='None', marker="o", label=label, color=col)

                # linear regression
                if type(dat[0][0]) in (int, float):
                    x = np.array(dat[0])

                    print("  ", stat, sep="")
                    m, b = np.polyfit(x, dat[1], 1) # generate y=mx+b formula
                    axs[index].plot(x, m*x + b, color=col)

                    print("    y=mx+b, m=", m, ", b=", b, sep="")
                    print("    ", stats.spearmanr(dat[0], dat[1]), " (df=", len(dat[0])-2, ")", sep="")

                index += 1

        if addLegend:
            for ax in axs:
                ax.legend(loc="upper right")

        # plt.suptitle(plotTitle, fontsize=SUPTITLE_FONTSIZE)

        plt.tight_layout()
        plt.savefig(os.path.join(project, "all", "plots", project + "_" + str(attrib) + "_error_bars.png"))

        # also save the data
        with open(os.path.join(project, "all", "plots",
                  project + "_" + str(attrib) +\
                  "_error_bars.png.csv"), 'w') as ofile:
            for line in errorbaroutdata:
                print(*line, sep=",", file=ofile)

        if SHOW_PLOTS:
            plt.show()

        plt.close()
    
    print("")

def plotValidationErrors(allStats, project):
    # we want to plot validation error vs accuracy per position
    valErrorStats = { "top": {}, "bottom": {} }

    for (p, d) in allStats.participantData.items():
        for (label, attrib) in (("bottom", "validationErrorsBottom"),\
                                ("top", "validationErrorsTop")):
            numErrors = getattr(d, attrib)
            if not numErrors in valErrorStats[label]:
                valErrorStats[label][numErrors] = [[],[],[]] # accuracy, precision, numErrors

            for targStats in d.targetStats:
                if targStats.position == label:
                    valErrorStats[label][numErrors][0].append(targStats.accuracyDeg)
                    valErrorStats[label][numErrors][1].append(targStats.precisionDeg)
                    valErrorStats[label][numErrors][2].append(numErrors) # for easy plotting

    # set up the canvas
    plt.rcParams["figure.figsize"] = (PLOT_SIZE[0]/PLOT_DPI, PLOT_SIZE[1]/PLOT_DPI)
    plt.rcParams["figure.dpi"] = PLOT_DPI

    # plot the data
    plotDims = (2, 2)
    plotIndex = 1
    for position, errorStats in valErrorStats.items():
        accPlotData = [[],[],[]] # x, y, error
        precPlotData = [[],[],[]]
        for numErrors, plotData in errorStats.items():
            ci = confidenceInterval(plotData[0])
            accPlotData[0].append(numErrors)
            accPlotData[1].append(ci[0])
            accPlotData[2].append(ci[1])

            ci = confidenceInterval(plotData[1])
            precPlotData[0].append(numErrors)
            precPlotData[1].append(ci[0])
            precPlotData[2].append(ci[1])

        plt.subplot(*plotDims, plotIndex)
        # plt.title(position)
        plt.xlabel("Validation errors")
        plt.ylabel("Accuracy in degrees (95% CI)")
        plt.errorbar(*accPlotData, linestyle='None', marker="o")
        print(position + " acc: " + str(stats.spearmanr(accPlotData[0], accPlotData[1])))
        print("df=" + str(len(accPlotData[0])-2))

        plt.subplot(*plotDims, plotIndex+1)
        # plt.title(position)
        plt.xlabel("Validation errors")
        plt.ylabel("Precision in degrees (95% CI)")
        plt.errorbar(*precPlotData, linestyle='None', marker="o")
        print(position + " prec: " + str(stats.spearmanr(precPlotData[0], precPlotData[1])))
        print("df=" + str(len(precPlotData[0])-2))
        plotIndex += 2

    # plt.suptitle("Accuracy and Precision per Number of Validation Errors", fontsize=SUPTITLE_FONTSIZE)

    plt.savefig(os.path.join(project, "all", "plots", project + "_validation_error_bars.png"))

    if SHOW_PLOTS:
        plt.show()

    plt.close()

if __name__ == '__main__':
    def printUsage():
        print("Usage: " + sys.argv[0] + " <qualtrics_csv> <participant_stats_csv> <raw_csv> <project> " +
              "[<study=" + ALL_STUDIES[1] + ">]")

    if len(sys.argv) < 5:
        printUsage()
        sys.exit(1)

    qualtrics_csv = sys.argv[1]
    participant_stats_csv = sys.argv[2]
    raw_csv = sys.argv[3]
    project = sys.argv[4]
    study = sys.argv[5]

    argsValid = True
    for f in (qualtrics_csv, participant_stats_csv, raw_csv):
        if not os.path.exists(f):
            print("Error: input file does not exist: " + f, file=sys.stderr)
            argsValid = False

    if not study in ALL_STUDIES:
        print("Error: study must be", "or".join(ALL_STUDIES), "::", study)
        argsValid = False

    if not argsValid:
        sys.exit(1)

    # load all of the data from the two files into one usable object
    allStats = CollatedStats(qualtrics_csv, participant_stats_csv, raw_csv, study)

    plotRxStats(allStats, project)
    plt.close('all')
    compareSamples(allStats, project, None, "Eye tracker performance - all data")
    # compareSamples(allStats, project, 'eyeColour', "Eye tracker performance in relation to eye colour")
    # compareSamples(allStats, project, 'eyesBlue', "Eye tracker performance in relation to eye blueness")
    compareSamples(allStats, project, 'eyesDark', "Eye tracker performance in relation to eye darkness")
    compareSamples(allStats, project, 'correction', "Eye tracker performance in relation to vision correction")
    compareSamples(allStats, project, 'panto', "Eye tracker performance in relation to pantoscopic tilt")
    compareSamples(allStats, project, 'posture33cm', "Eye tracker performance in relation to near vergence")
    compareSamples(allStats, project, 'posture3m', "Eye tracker performance in relation to distance vergence")
    # plotValidationErrors(allStats, project)

# EOF
