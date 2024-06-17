# statistics from an experiment run
class ExperimentStats:
    def __init__(self):
        self.participant = None
        self.target = None
        self.label = None
        self.test_n = None
        self.record_n = None
        self.accuracy_px = None
        self.precision_px = None
        self.accuracy_deg = None
        self.precision_deg = None
        self.bad_data_left = None
        self.bad_data_right = None
        self.bad_data_both = None
        self.distance_cm = None
        self.targets = {}

        # stats
        self.parametric = None # Kolgomorov-Smirnov to test for normal distribution

    @staticmethod
    def csv_header():
        return "participant,label,target_id,test_n,record_n,working_distance_cm,accuracy_px,accuracy_deg,precision_px,precision_deg,bad_both,bad_right,bad_left,parametric\n"

    def __str__(self):
        outstr = '"' + ("" if self.participant is None else str(self.participant)) + '",' \
                 '"' + str(self.label) + '",' +\
                 ("all" if self.target is None else str(self.target)) + "," +\
                 str(self.test_n) + "," +\
                 str(self.record_n) + "," +\
                 ("" if self.distance_cm is None else str(self.distance_cm)) + "," +\
                 str(self.accuracy_px) + "," +\
                 ("" if self.accuracy_deg is None else str(self.accuracy_deg)) + "," +\
                 str(self.precision_px) + "," +\
                 ("" if self.precision_deg is None else str(self.precision_deg)) + "," +\
                 str(self.bad_data_both) + "," +\
                 str(self.bad_data_right) + "," +\
                 str(self.bad_data_left) + "," +\
                 str(self.parametric) + "\n"

        for target_id in self.targets:
            outstr += str(self.targets[target_id]) 

        return outstr

# EOF
