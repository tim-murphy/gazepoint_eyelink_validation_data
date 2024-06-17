from math import atan, ceil, sqrt
import matplotlib.cm as pltcm
import matplotlib.colors as pltcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from numpy import rad2deg
import os
from statistics import pstdev

import ExperimentResults
from ExperimentStats import ExperimentStats

# some of our plots have lots of subplots
from matplotlib import rc
rc('figure', max_open_warning = 0)

SCATTER_PLOT = "scatter"
VECTOR_PLOT = "vector"
GRAPH_TYPES = [SCATTER_PLOT, VECTOR_PLOT]
PLOT_PADDING = 100
PLOT_DPI = 200
PLOT_FONT_SIZE = 'large'
COLOURMAP = "jet" #"nipy_spectral"

class ExperimentPlot:
    def __init__(self, experiment_results):
        self.results = experiment_results
        self.plot_size = experiment_results.plot_size

    def getTargets(self):
        return self.results.getTargets()

    # Filter the results by subject and/or identifier. Leave these parameters
    # as None to return all results.
    def filterBySubject(self, subject=None, identifier=None):
        filtered_data = {}
        for subj in self.results.subject_data:
            idents = self.results.subject_data[subj]
            for ident in idents:
                if (subject is None or subj == subject) and\
                   (identifier is None or ident == identifier):
                    if ident not in filtered_data:
                        filtered_data[ident] = []
                    filtered_data[ident] += idents[ident]

        return filtered_data

    def plotTargets(self):
        print(self.getTargets(), self.results.position)
        for targ in self.getTargets():
            coords = self.getTargets()[targ]
            plt.scatter(coords[0], coords[1], marker='x', color=(0.0, 0.0, 0.0, 0.5), s=750)

    def setupCanvas(self, num_plots=1):
        this_dpi = PLOT_DPI * num_plots # this keeps the sizing equal for composite plots
        plt.figure(figsize=(self.plot_size[0]/PLOT_DPI,
                            (self.plot_size[1]*num_plots)/PLOT_DPI),
                   dpi=this_dpi)
        plt.axis([-PLOT_PADDING, self.plot_size[0] + PLOT_PADDING,
                  -PLOT_PADDING, (self.plot_size[1] * num_plots) + PLOT_PADDING])
        plt.gca().invert_yaxis()

        # first plot the target positions
        self.plotTargets()

    def setupColourMapping(self, plot_data):
        colours = pltcm.ScalarMappable(norm=pltcolors.Normalize(vmin=0, vmax=len(plot_data) - 1),\
                                       cmap=plt.get_cmap(COLOURMAP))
        return colours

    def plotScatter(self, subject=None, identifier=None):
        # filter to the data we want
        plot_data = self.filterBySubject(subject, identifier)

        # canvas setup
        colours = self.setupColourMapping(plot_data)
        self.setupCanvas()
        plt.subplots_adjust(left=0.05, right=0.70, top=0.825, bottom=0.175)

        for i, subj in enumerate(plot_data):
            colour = (colours.to_rgba(i))
            label = ExperimentResults.subjectToLabel(subj)
            x_coords = []
            y_coords = []
            for coords in plot_data[subj]:
                x_coords.append(coords[1])
                y_coords.append(coords[2])
            plt.scatter(x_coords, y_coords, marker='o', color=colour, s=5, label=label)

        # plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1.01), title="Legend", fontsize="medium", title_fontsize="large")

    def plotVector(self, subject=None, identifier=None, split=True, save_all=True, distance_cm=None, outname="."):
        # filter to the data we want
        plot_data = self.filterBySubject(subject, identifier)

        # canvas setup
        colours = self.setupColourMapping(plot_data)

        if not split:
            self.setupCanvas()

            # make room for the legend and stats
            # plt.subplots_adjust(left=0.05, right=0.70, top=0.825, bottom=0.175)
            # plt.title("Subject: " + ("all" if subject is None else subject) +\
                      # ", Screen: 23.8in 1920x1080" +\
                      # ("" if distance_cm is None else " at " + str(distance_cm) + "cm"),\
                      # fontsize=30)
            plt.xlabel("Screen x position (pixels)", fontsize=15)
            plt.ylabel("Screen y position (pixels)", fontsize=15)
        else:
            fig = plt.gcf()
            fig.set_size_inches(self.plot_size[0]/PLOT_DPI, self.plot_size[1]/PLOT_DPI * 2)
            fig.set_dpi(PLOT_DPI)

        # plot individual graphs separately
        if save_all:
            for i, subj in enumerate(plot_data):
                self.setupCanvas()
                label = ExperimentResults.subjectToLabel(subj)
                self.results.position = subj[1]

                plt.axis([-PLOT_PADDING, self.plot_size[0]+PLOT_PADDING, -PLOT_PADDING ,self.plot_size[1]+PLOT_PADDING])
                plt.gca().invert_yaxis()
                # plt.title(label, fontsize=PLOT_FONT_SIZE)
                plt.xlabel("Screen x position (pixels)", fontsize=PLOT_FONT_SIZE)
                plt.ylabel("Screen y position (pixels)", fontsize=PLOT_FONT_SIZE)
                for target_id in self.getTargets():
                    target_coords = self.getTargets()[target_id]

                    colour = (0x01, 0x16, 0x1E) if (i % 2 == 0) else (0x49, 0x11, 0x1C) #(colours.to_rgba(i % 2))
                    colour = (colour[0] / 0xFF, colour[1] / 0xFF, colour[2] / 0xFF)
                    x_vals = []
                    y_vals = []
                    distances = []

                    # make semi-transparent
                    colour = (colour[0], colour[1], colour[2], 0.5)

                    for coords in plot_data[subj]:
                        if coords[0] == target_id and coords[1] != ExperimentResults.INVALID_COORD and coords[2] != ExperimentResults.INVALID_COORD:
                            x_vals.append(coords[1])
                            y_vals.append(coords[2])

                            # use pythagoras to determine the distance
                            dist = sqrt((self.getTargets()[target_id][0] - coords[1]) ** 2\
                                      + (self.getTargets()[target_id][1] - coords[2]) ** 2)
                            distances.append(dist)

                    if len(x_vals) > 0 and len(y_vals) > 0:
                        x_ave = sum(x_vals) / len(x_vals)
                        y_ave = sum(y_vals) / len(y_vals)
                        x_targ = self.getTargets()[target_id][0]
                        y_targ = self.getTargets()[target_id][1]
                        plt.quiver([x_targ], [y_targ],
                                   [-(x_targ - x_ave)], [-(y_targ - y_ave)], # negating due to our screen geometry
                                   color=list((colour)),
                                   angles='xy', scale_units='xy', scale=1)

                        # add circles to show precision
                        precision_px = ceil(pstdev(distances))
                        colour = (colour[0], colour[1], colour[2], 0.1) # make these circles more transparent
                        polar_grid = mpatches.Circle((x_ave, y_ave), precision_px, fill=True, color=colour)
                        plt.gcf().gca().add_patch(polar_grid)
                    else:
                        print("WARN: no valid data for target " + str(target_id))

                self.plotMonitorEdge()
                self.plotPolarGrid(distance_cm)
                self.plotTargets()
                outfilename = outname[:-4] + label.replace(":", "").replace(" ", "_") + ".png"
                plt.savefig(outfilename, dpi=PLOT_DPI)

        # join all plots together
        plotDims = (ceil(len(plot_data)),1)
        self.setupCanvas(num_plots=plotDims[0])
        for i, subj in enumerate(plot_data):
            label = ExperimentResults.subjectToLabel(subj)
            self.results.position = subj[1]

            plt.subplot(*plotDims, len(plot_data) - i, aspect='equal') # plot from bottom to top as it looks nicer
            plt.axis([-PLOT_PADDING, self.plot_size[0]+PLOT_PADDING, -PLOT_PADDING ,self.plot_size[1]+PLOT_PADDING])
            plt.gca().invert_yaxis()
            # plt.title(label, fontsize=PLOT_FONT_SIZE)
            plt.xlabel("Screen x position (pixels)", fontsize=PLOT_FONT_SIZE)
            plt.ylabel("Screen y position (pixels)", fontsize=PLOT_FONT_SIZE)
            for target_id in self.getTargets():
                target_coords = self.getTargets()[target_id]

                colour = (colours.to_rgba(i))
                x_vals = []
                y_vals = []
                distances = []

                # make semi-transparent
                colour = (colour[0], colour[1], colour[2], 0.5)

                for coords in plot_data[subj]:
                    if coords[0] == target_id and coords[1] != ExperimentResults.INVALID_COORD and coords[2] != ExperimentResults.INVALID_COORD:
                        x_vals.append(coords[1])
                        y_vals.append(coords[2])

                        # use pythagoras to determine the distance
                        dist = sqrt((self.getTargets()[target_id][0] - coords[1]) ** 2\
                                  + (self.getTargets()[target_id][1] - coords[2]) ** 2)
                        distances.append(dist)

                if len(x_vals) > 0 and len(y_vals) > 0:
                    x_ave = sum(x_vals) / len(x_vals)
                    y_ave = sum(y_vals) / len(y_vals)
                    x_targ = self.getTargets()[target_id][0]
                    y_targ = self.getTargets()[target_id][1]
                    plt.quiver([x_targ], [y_targ],
                               [-(x_targ - x_ave)], [-(y_targ - y_ave)], # negating due to our screen geometry
                               color=list((colour)),
                               angles='xy', scale_units='xy', scale=1)

                    # add circles to show precision
                    precision_px = ceil(pstdev(distances))
                    colour = (colour[0], colour[1], colour[2], 0.1) # make these circles more transparent
                    polar_grid = mpatches.Circle((x_ave, y_ave), precision_px, fill=True, color=colour)
                    plt.gcf().gca().add_patch(polar_grid)
                else:
                    print("WARN: no valid data for target " + str(target_id))

            self.plotMonitorEdge()
            self.plotPolarGrid(distance_cm)
            self.plotTargets()

        if not split:
            # manually generate the legend
            legend_elements = []
            for i, subj in enumerate(plot_data):
                colour = (colours.to_rgba(i))
                label = ExperimentResults.subjectToLabel(subj)
                legend_elements.append(mpatches.Patch(color=colour, label=label))

            # plt.legend(loc="upper left", bbox_to_anchor=(1.05, 1.01), title="Legend", fontsize="medium", title_fontsize="large", handles=legend_elements)

    def plotStats(self, subject=None, identifier=None, distance_cm=None, participant=None, split=True):
        # add the accuracy and precision data to the plot
        stats = self.results.getStats(subject, identifier, distance_cm, participant)

        stats_text = ""
        stats_verbose = ExperimentStats.csv_header()
        for label in stats:
            s = stats[label]
            stats_verbose += str(s)

            acc_px = "{:.0f}".format(s.accuracy_px) + "px"
            prec_px = "{:.0f}".format(s.precision_px) + "px"
            acc_deg = ""
            prec_deg = ""

            # include degrees and px if we can
            if distance_cm is not None:
                # calculate the angular subtense of each pixel, and multiply
                # our accuracy and precision pixel values accordingly
                s.distance_cm = distance_cm
                conversion_factor = rad2deg(atan(ExperimentResults.PIXEL_SIZE_CM / distance_cm))
                s.accuracy_deg = s.accuracy_px * conversion_factor
                acc_deg = " / " + "{:.1f}".format(s.accuracy_deg) + u'\N{DEGREE SIGN}'
                s.precision_deg = s.precision_px * conversion_factor
                prec_deg = " / " + "{:.1f}".format(s.precision_deg) + u'\N{DEGREE SIGN}'

            stats_text += label + " (test_n=" + str(s.test_n) + ", record_n=" + str(s.record_n) + ")\n    accuracy = " + acc_px + acc_deg + ", precision = " + prec_px + prec_deg + "\n    invalid readings: BE=" + str(s.bad_data_both) + ", RE=" + str(s.bad_data_right) + ", LE=" + str(s.bad_data_left) + "\n"

        if not split:
            plt.text(2200, 400, stats_text, fontsize=10, verticalalignment="top")

        # return a textual representation of the stats
        return stats_verbose

    
    def plotMonitorEdge(self):
        res = ExperimentResults.SCREEN_RESOLUTION;
        monitor_edge = mpatches.Rectangle((0, 0), res[0], res[1], linewidth=1, fill=False, edgecolor="grey")
        plt.gcf().gca().add_patch(monitor_edge)

    def plotPolarGrid(self, distance_cm=None, angle_delta=5, colour="#777777FF"):
        # if no distance is given, we can't calculate angles
        if distance_cm is None:
            return

        # it is easier to draw these circles manually than mess about with
        # plt.axes(projection="polar", facecolor="#FFFFFF00" ...)
        px_per_deg = ExperimentResults.pixelsPerDegree(distance_cm)
        max_radius_px = ExperimentResults.PIXEL_HYPOTENUSE / 2
        origin = (ExperimentResults.SCREEN_RESOLUTION[0] / 2, ExperimentResults.SCREEN_RESOLUTION[1] / 2)
        num_lines = int(max_radius_px / px_per_deg / angle_delta)

        for n in range(1, num_lines + 1):
            # circles
            radius = n * px_per_deg * angle_delta
            polar_grid = mpatches.Circle(origin, radius, fill=False, color=colour)
            plt.gcf().gca().add_patch(polar_grid)

            # labels
            plt.text(origin[0] + radius - 5, origin[1], str(n * angle_delta) + u'\N{DEGREE SIGN}', horizontalalignment="right", color=colour) 
            plt.text(origin[0] - radius + 5, origin[1], str(n * angle_delta) + u'\N{DEGREE SIGN}', horizontalalignment="left", color=colour)

        # cross for the origin
        plt.plot(origin[0], origin[1], 'x', color=colour)
        plt.plot(origin[0], origin[1], '+', color=colour)

# EOF
