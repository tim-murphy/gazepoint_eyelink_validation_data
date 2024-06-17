import csv
from math import atan, sqrt
from numpy import rad2deg
from scipy import stats
from statistics import mean, pstdev

from ExperimentStats import ExperimentStats

DATA_COLS = {
    "Label": 0,
    "Subject": 1,
    "Tracker": 2,
    "Timestamp": 3,
    "Target-ID": 4,
    "Target-X": 5,
    "Target-Y": 6,
    "Cursor-X": 7,
    "Cursor-Y": 8,
    "Actual-X-Right": 9,
    "Actual-Y-Right": 10,
    "Actual-X-Left": 11,
    "Actual-Y-Left": 12
}

INVALID_COORD = 0x7FFFFFFF # INT_MAX in C

# screen settings
SCREEN_RESOLUTION = (1920, 1080)
SCREEN_SIZE_CM = (23.8 * 2.54) # convert inches to cm

# studies
ALL_STUDIES = ("position", "validation")

BAD_RIGHT = 0
BAD_LEFT = 1
BAD_BOTH = 2

# calculate the hypotenuse of a right angle triangle using the screen resolution.
# e.g a 800x600 monitor would make a triangle with sides 800, 600, and hypotenuse.
PIXEL_HYPOTENUSE = sqrt(pow(SCREEN_RESOLUTION[0], 2) + pow(SCREEN_RESOLUTION[1], 2))
PIXEL_SIZE_CM = SCREEN_SIZE_CM / PIXEL_HYPOTENUSE

# set to True if the tracker uses the last good reading instead of marking
# invalid readings as MAX_INT or another overly large number.
REMOVE_DUPLICATE_READINGS = False

######################
## Helper functions ##
######################

def subjectToLabel(subj):
    return subj[0] + " :: " + subj[1]

# calculate the number of pixels per degree of angular subtense
def pixelsPerDegree(distance_cm):
    pixel_angle = rad2deg(atan(PIXEL_SIZE_CM / distance_cm))
    pixels_per_degree = 1.0/pixel_angle
    return pixels_per_degree

def gazePosFromBothEyes(right_eye, left_eye):
    bad_side = None
    actual_ave = [INVALID_COORD, INVALID_COORD]

    for i in (0,1):
        if 0 <= right_eye[i] <= SCREEN_RESOLUTION[i] and 0 <= left_eye[i] <= SCREEN_RESOLUTION[i]:
            actual_ave[i] = (right_eye[i] + left_eye[i]) / 2
        elif 0 <= right_eye[i] <= SCREEN_RESOLUTION[i]:
            # left_eye[i] is invalid
            actual_ave[i] = right_eye[i]
            bad_side = BAD_LEFT if bad_side in (None, BAD_LEFT) else BAD_BOTH
        elif 0 <= left_eye[i] <= SCREEN_RESOLUTION[i]:
            # right_eye[i] is invalid
            actual_ave[i] = left_eye[i]
            bad_side = BAD_RIGHT if bad_side in (None, BAD_RIGHT) else BAD_BOTH
        else:
            # both data points bad
            bad_side = BAD_BOTH

    return actual_ave, bad_side

# this class contains the experiment details (target locations, etc) as well
# as eye tracking results for each participant.
class ExperimentResults:
    def __init__(self, data_csv, plot_dimensions, targets_bottom=None, targets_top=None):
        self.position = None
        self.targets_bottom = {}
        self.targets_top = {}
        self.subject_data = {}
        self.ident_count = {}
        self.ident_count_target = {}
        self.invalid_rows = set()
        self.bad_data = {} # a count of bad data per tracker/label pair
        self.target_bad_data = {} # a count of bad data per target for each tracker/label pair
        self.raw_data = None
        self.stats = None
        self.plot_size = plot_dimensions
        self.loadData(data_csv, targets_bottom, targets_top)

    def loadData(self, data_csv, targets_bottom=None, targets_top=None):
        # We're not using a dictreader here as we can't guarantee there will
        # be a header row present.
        with open(data_csv, 'r') as csvfile:
            self.raw_data = list(csv.reader(csvfile, delimiter=','))

        # keep a record of the previous row values and remove duplicates (if
        # that's what we want) as this means the eye tracker did not get any
        # reading for that target.
        prev_x = -1
        prev_y = -1

        # for readability
        x_max = self.plot_size[0]
        y_max = self.plot_size[1]

        # flip to True when a header row is read. Used to count participants.
        header_found = False

        for index, row in enumerate(self.raw_data):
            # remove the header rows
            # note: we assume the row is a header if the last element is not a number
            try:
                _ = int(row[-1])
            except:
                print("Ignoring header row: " + str(row))
                self.invalid_rows.add(index)
                header_found = True
                continue

            subject = row[DATA_COLS["Subject"]]
            if not subject in self.subject_data:
                self.subject_data[subject] = {}

            # select the targets based on the CSV label
            self.position = row[DATA_COLS["Label"]] # bottom or top
            if not (self.position.endswith("bottom") or self.position.endswith("top")):
                print("Not top or bottom - using all targets:", self.position)

            targets = targets_top
            if self.position.endswith("bottom"):
                targets = targets_bottom

            # extract the targets
            target_id = int(row[DATA_COLS["Target-ID"]])

            # if we're looking at a subset of targets, filter them here
            if targets is not None and target_id not in targets:
                continue

            target_coords = (int(row[DATA_COLS["Target-X"]]),\
                            int(row[DATA_COLS["Target-Y"]]))

            if target_id in self.getTargets():
                # make sure the data is consistent
                if self.getTargets()[target_id] != target_coords:
                    print("ERROR: inconsintent data for target " + str(target_id)\
                          + ": coords recorded at " + str(self.getTargets()[target_id])\
                          + " and " + str(target_coords))
                    sys.exit(1)
            else:
                print("Adding target:", target_id)
                self.getTargets()[target_id] = target_coords

            # extract subject data
            identifier = (row[DATA_COLS["Tracker"]], row[DATA_COLS["Label"]])

            if not identifier in self.ident_count:
                self.ident_count[identifier] = 0

            if not identifier in self.ident_count_target:
                self.ident_count_target[identifier] = {}

            if not target_id in self.ident_count_target[identifier]:
                self.ident_count_target[identifier][target_id] = 0
            self.ident_count_target[identifier][target_id] += 1

            if header_found:
                self.ident_count[identifier] += 1
                header_found = False

            # We have two readings for x and y. Average if they are valid, or
            # use the best if only one is valid. If both invalid then keep
            # as an invalid reading.
            x_right = int(row[DATA_COLS["Actual-X-Right"]])
            x_left  = int(row[DATA_COLS["Actual-X-Left"]])
            y_right = int(row[DATA_COLS["Actual-Y-Right"]])
            y_left  = int(row[DATA_COLS["Actual-Y-Left"]])

            if not identifier in self.bad_data:
                self.bad_data[identifier] = [0,0,0] # right, left, both

            if not identifier in self.target_bad_data:
                self.target_bad_data[identifier] = {}

            if not target_id in self.target_bad_data[identifier]:
                self.target_bad_data[identifier][target_id] = [0,0,0] # right, left, both

            actual_ave, bad_side = gazePosFromBothEyes((x_right, y_right), (x_left, y_left))

            if bad_side is not None:
                self.bad_data[identifier][bad_side] += 1
                self.target_bad_data[identifier][target_id][bad_side] += 1

            if bad_side == BAD_BOTH:
                print("Ignoring invalid data: right =", x_right, y_right, " left =", x_left, y_left)
                self.invalid_rows.add(index)
                continue

            coords = (int(row[DATA_COLS["Target-ID"]]),\
                      actual_ave[0], actual_ave[1])

            if REMOVE_DUPLICATE_READINGS and coords[1] == prev_x and coords[2] == prev_y:
                print("Ignoring duplicate data: " + str(coords))
                self.invalid_rows.add(index)
                self.bad_data[identifier][BAD_BOTH] += 1
                continue

            prev_x = coords[1]
            prev_y = coords[2]

            if identifier in self.subject_data[subject]:
                self.subject_data[subject][identifier] += [coords]
            else:
                self.subject_data[subject][identifier] = [coords]

    def getTargets(self):
        if not (self.position.endswith("bottom") or self.position.endswith("top")):
                print("Not top or bottom - using all targets:", self.position)

        if self.position.endswith("bottom"):
            return self.targets_bottom

        return self.targets_top

    def getStats(self, subject=None, identifier=None, distance_cm=None, participant=None):
        if self.stats is not None:
            return self.stats

        self.stats = {}

        # collect all of the stats in a larger dictionary to allow multiple
        # subjects to be included
        distances = {}
        targetdist = {}

        for subj in self.subject_data:
            if subj not in self.stats:
                if subject is not None and subject != subj:
                    continue

            for ident in self.subject_data[subj]:
                if identifier is not None and identifier != ident:
                    continue

                if ident not in distances:
                    distances[ident] = []

                if ident not in targetdist:
                    targetdist[ident] = {}

                # coords is in the format (target_id, x_pos, y_pos)
                for coords in self.subject_data[subj][ident]:
                    target_id = coords[0]
                    x_pos = coords[1]
                    y_pos = coords[2]

                    # HACK: set the position to get the correct target subset
                    self.position = ident[1]
                    if target_id not in self.getTargets():
                        print("WARN: not including target", target_id, "for", ident)
                        continue

                    # use pythagoras to determine the distance
                    dist = sqrt((self.getTargets()[target_id][0] - x_pos) ** 2\
                              + (self.getTargets()[target_id][1] - y_pos) ** 2)
                    distances[ident].append(dist)

                    if target_id not in targetdist[ident]:
                        targetdist[ident][target_id] = []

                    targetdist[ident][target_id].append(dist)

        for ident in distances:
            label = subjectToLabel(ident)

            if label in self.stats:
                print("WARN: overwriting stats for " + label)

            self.stats[label] = ExperimentStats()

            # for accuracy, calculate the mean pixel distance from the target.
            # for precision, we calculate the standard deviation.
            # we also convert this into degrees, if we have a working distance

            conversion_factor = None
            if distance_cm is not None:
                conversion_factor = rad2deg(atan(PIXEL_SIZE_CM / distance_cm))

            self.stats[label].participant = participant
            self.stats[label].label = label
            self.stats[label].distance_cm = distance_cm
            self.stats[label].accuracy_px = mean(distances[ident])
            self.stats[label].precision_px = pstdev(distances[ident])
            self.stats[label].bad_data_right = self.bad_data[ident][BAD_RIGHT]
            self.stats[label].bad_data_left = self.bad_data[ident][BAD_LEFT]
            self.stats[label].bad_data_both = self.bad_data[ident][BAD_BOTH]
            self.stats[label].test_n = self.ident_count[ident]
            self.stats[label].parametric = ("True" if stats.kstest(distances[ident], 'norm').pvalue >= 0.05 else "False")

            self.stats[label].record_n = 0
            for target_id in self.ident_count_target[ident]:
                self.stats[label].record_n += self.ident_count_target[ident][target_id]

            if conversion_factor is not None:
                self.stats[label].accuracy_deg = self.stats[label].accuracy_px * conversion_factor
                self.stats[label].precision_deg = self.stats[label].precision_px * conversion_factor

            # add the target stats too
            if ident in targetdist:
                for target_id in sorted(targetdist[ident]):
                    if target_id not in self.stats[label].targets:
                        self.stats[label].targets[target_id] = ExperimentStats()
                    self.stats[label].targets[target_id].participant = participant
                    self.stats[label].targets[target_id].label = label
                    self.stats[label].targets[target_id].distance_cm = distance_cm
                    self.stats[label].targets[target_id].target = target_id
                    self.stats[label].targets[target_id].accuracy_px = mean(targetdist[ident][target_id])
                    self.stats[label].targets[target_id].precision_px = pstdev(targetdist[ident][target_id])
                    self.stats[label].targets[target_id].bad_data_right = self.target_bad_data[ident][target_id][BAD_RIGHT]
                    self.stats[label].targets[target_id].bad_data_left = self.target_bad_data[ident][target_id][BAD_LEFT]
                    self.stats[label].targets[target_id].bad_data_both = self.target_bad_data[ident][target_id][BAD_BOTH]
                    self.stats[label].targets[target_id].test_n = self.ident_count[ident]
                    self.stats[label].targets[target_id].record_n = self.ident_count_target[ident][target_id]
                    self.stats[label].targets[target_id].parametric = ("True" if stats.kstest(targetdist[ident][target_id], 'norm').pvalue >= 0.05 else "False")

                    if conversion_factor is not None:
                        self.stats[label].targets[target_id].accuracy_deg = self.stats[label].targets[target_id].accuracy_px * conversion_factor
                        self.stats[label].targets[target_id].precision_deg = self.stats[label].targets[target_id].precision_px * conversion_factor

        return self.stats

# EOF
