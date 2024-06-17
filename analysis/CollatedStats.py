import csv
from math import sqrt
import os
import sys

from ExperimentResults import gazePosFromBothEyes, BAD_BOTH, subjectToLabel, ALL_STUDIES

# this class contains all of the Qualtrics data as well as the stats data
class CollatedStats:
    def __init__(self, qualtrics_csv, participant_csv, raw_csv, study=ALL_STUDIES[1]):
        self.study = study
        self.participantData = {}
        self.warnMissingTargets = False

        self.loadQualtricsData(qualtrics_csv)
        self.loadParticipantData(participant_csv)
        self.loadRawData(raw_csv)

    def loadQualtricsData(self, qualtrics_csv):
        if not os.path.exists(qualtrics_csv):
            print("ERROR: Qualtrics data file does not exist: " + qualtrics_csv, file=sys.stderr)
            sys.exit(1)

        with open(qualtrics_csv, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                qRecord = QualtricsRecord()
                qRecord.id = int(row['ID'])
                qRecord.eyeColour = row['EyeColour']
                qRecord.eyesBlue = ("Blue eyes" if qRecord.eyeColour == "Blue" else "Not blue eyes")
                qRecord.eyesDark = ("Dark eyes" if qRecord.eyeColour in("Brown", "Dark Brown") else "Light eyes")
                qRecord.correction = row['Correction']
                qRecord.eyeConditions = row['EyeConditions']
                qRecord.posture3m = float(row['Posture3mVal'])
                qRecord.posture33cm = float(row['Posture33cmVal'])
                qRecord.hasARCoat = (True if row['HasARCoat'] == '1' else False)
                qRecord.vertRight = row['VertRight']
                qRecord.vertLeft = row['VertLeft']
                qRecord.sphericalDistRx = float(row['SphericalDistRx'])
                qRecord.MFAdd = (None if row['MFAdd'] == "" else float(row['MFAdd']))
                qRecord.panto = (None if row['Panto'] == "" else float(row['Panto']))

                if self.study == ALL_STUDIES[0]:
                    qRecord.validationErrorsTop = int(float(row['ValidationErrorsTop']))
                    qRecord.validationErrorsBottom = int(float(row['ValidationErrorsBottom']))

                qRecord.targetStats = []

                self.participantData[qRecord.id] = qRecord

    def loadParticipantData(self, participant_csv):
        if not os.path.exists(participant_csv):
            print("ERROR: Participant stats file does not exist: " + participant_csv, file=sys.stderr)
            sys.exit(1)

        with open(participant_csv, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                participant = int(row['participant'])
                if not participant in self.participantData:
                    print("INFO: skipping record as not in Qualtrics: " + participant)
                    continue

                tStats = TargetStats()
                tStats.participant = participant
                tStats.label = row['label']
                tStats.targetID = ("all" if row['target_id'] == "all" else int(row['target_id']))
                tStats.testN = int(row['test_n'])
                tStats.recordN = int(row['record_n'])
                tStats.workingDistanceCm = float(row['working_distance_cm'])
                tStats.accuracyPx = float(row['accuracy_px'])
                tStats.accuracyDeg = float(row['accuracy_deg'])

                # if there is insufficient data to calculate precision, make
                # sure we ignore it and don't use the value zero
                if row['precision_px'] == row['precision_deg'] == '0':
                    tStats.precisionPx = None
                    tStats.precisionDeg = None
                else:
                    tStats.precisionPx = float(row['precision_px'])
                    tStats.precisionDeg = float(row['precision_deg'])

                tStats.badReadBoth = int(row['bad_both'])
                tStats.badReadRight = int(row['bad_right'])
                tStats.badReadLeft = int(row['bad_left'])
                tStats.rawDistanceValuesPx = []

                self.participantData[participant].targetStats.append(tStats)

                if self.participantData[participant].PxToDegConvFactor is None:
                    self.participantData[participant].PxToDegConvFactor = (tStats.accuracyDeg / tStats.accuracyPx)

    def loadRawData(self, raw_csv):
        if not os.path.exists(raw_csv):
            print("ERROR: Raw data file does not exist: " + raw_csv, file=sys.stderr)
            sys.exit(1)

        with open(raw_csv, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                # detect header rows
                if row['Target-ID'] == "Target-ID":
                    continue

                participant = int(row['Subject'])
                if not participant in self.participantData:
                    print("INFO: skipping record as not in Qualtrics: " + participant)
                    continue
                
                if self.participantData[participant].targetStats is None:
                    print("ERROR: stats data has not been loaded yet for " + participant, file=sys.stderr)
                    continue

                # calculate the distance from the target to the recorded position
                target_id = int(row['Target-ID'])
                label = subjectToLabel((row['Tracker'], row['Label']))

                target_x = int(row['Target-X'])
                target_y = int(row['Target-Y'])
                gazePos, bad_side = gazePosFromBothEyes((int(row['Actual-X-Right']), int(row['Actual-Y-Right'])),\
                                                        (int(row['Actual-X-Left']), int(row['Actual-Y-Left'])))

                # if both eye records are bad, the data are not useful
                if bad_side == BAD_BOTH:
                    continue

                dist = sqrt((target_x - gazePos[0]) ** 2\
                          + (target_y - gazePos[1]) ** 2)

                # add this to the participant's records
                targFound = False
                for rec in self.participantData[participant].targetStats:
                    if not targFound and rec.label == label and rec.targetID == target_id:
                        targFound = True
                        rec.rawDistanceValuesPx.append(dist)

                        # also add in the position (stored in the Label field in this CSV)
                        rec.position = row['Label']

                if not targFound and self.warnMissingTargets:
                    print("ERROR: target record not found for " + str(label) + " :: " + str(target_id) + " :: " + str(participant))

class QualtricsRecord:
    def __init__(self):
        self.id = None
        self.eyeColour = None
        self.eyesBlue = None
        self.eyesDark = None
        self.correction = None
        self.eyeConditions = None
        self.posture3m = None
        self.posture33cm = None
        self.hasARCoat = None
        self.vertRight = None
        self.vertLeft = None
        self.sphericalDistRx = None
        self.MFAdd = None
        self.panto = None
        self.validationErrorsTop = None
        self.validationErrorsBottom = None
        self.PxToDegConvFactor = None
        self.targetStats = None

class TargetStats:
    def __init__(self):
        self.participant = None
        self.label = None
        self.targetID = None
        self.testN = None
        self.recordN = None
        self.workingDistanceCm = None
        self.accuracyPx = None
        self.accuracyDeg = None
        self.precisionPx = None
        self.precisionDeg = None
        self.badReadBoth = None
        self.badReadRight = None
        self.badReadLeft = None
        self.position = None
        self.rawDistanceValuesPx = None

# EOF
