import time

from wave_func import WaveFunc


class SuperWaveFunc(WaveFunc):
    def __init__(self, ref_time=0, period=0, int_phase=0, num_int_periods=0,
                 int_periods_active=None, decay=0, funcs=None, serialized=None):
        super(SuperWaveFunc, self).__init__(ref_time, period, decay, funcs, serialized=serialized)

        if not serialized:
            self.int_phase = float(int_phase)
            self.num_int_periods = int(num_int_periods)
            self.int_period = self.period / float(self.num_int_periods)

            if type(int_periods_active) is not list:
                int_periods_active = [int_periods_active]
            self.int_periods_active = int_periods_active

    def resolve(self, anchor_timestamp=None):
        if not anchor_timestamp:
            anchor_timestamp = time.time()

        # External age
        age, partial_period, fractional_period = self.compute_periods(anchor_timestamp)
        int_period_num, int_partial_period = divmod(partial_period, self.int_period)

        if int_period_num not in self.int_periods_active:
            return 0

        # The internal position
        int_period_frac = int_partial_period / self.int_period

        # Now the value
        val = self.compute_pos(int_period_frac, anchor_timestamp)
        d = self.calc_decay(age)

        return d * val

    def init_from_serialized(self, serialized):
        super(SuperWaveFunc, self).init_from_serialized(serialized)

        self.int_phase = serialized['IntPhase']
        self.int_period = serialized['IntPeriod']
        self.num_int_periods = serialized['NumIntPeriods']
        self.int_periods_active = serialized['IntPeriodsActive']

    def serialize(self):
        serialized = super(SuperWaveFunc, self).serialize()

        serialized['IntPhase'] = self.int_phase
        serialized['IntPeriod'] = self.int_period
        serialized['NumIntPeriods'] = self.num_int_periods
        serialized['IntPeriodsActive'] = self.int_periods_active

        return serialized
