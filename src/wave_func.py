import time
import math


def sin_func(x):
    # x expected to be normalized between 0 and 1
    x = min(1.0, max(0, x))
    y = math.cos((x * 2 * math.pi))

    # y normalized to between 0 and 1
    y = (y + 1) / 2
    return y


base_funcs = {
    'sin': sin_func
}


class WaveFunc(object):
    def __init__(self, ref_time=0, period=0, decay=0, funcs=None, serialized=None):
        if not funcs:
            funcs = []

        self.ref_time = float(ref_time)
        self.period = float(period)
        self.decay = float(decay)
        self.funcs = funcs

        if serialized:
            self.init_from_serialized(serialized)

    def init_from_serialized(self, serialized):
        self.ref_time = serialized['ref_time']
        self.period = serialized['period']
        self.decay = serialized['decay']

        funcs = serialized['funcs']

        for func_def in funcs:
            f = func_def['func']
            if type(f) is dict:
                self.funcs.append({
                    'func': SuperWaveFunc(serialized=f),
                    'phase': func_def['phase']
                })
            else:
                self.funcs.append(func_def.copy())

    def resolve(self, anchor_timestamp=None):
        if not anchor_timestamp:
            anchor_timestamp = time.time()

        age, partial_period, fractional_period = self.compute_periods(anchor_timestamp)
        aggregate_val = self.compute_pos(fractional_period, anchor_timestamp)
        decay_factor = self.calc_decay(age)
        return aggregate_val / decay_factor

    def resolve_max(self, anchor_timestamp=None):
        if not anchor_timestamp:
            anchor_timestamp = time.time()

        decay_age = anchor_timestamp - self.ref_time
        d = self.calc_decay(decay_age)
        val = self.compute_pos(1.0, anchor_timestamp)

        return val * d

    def compute_periods(self, anchor_timestamp, period=None, ref_time=None):
        if ref_time is None:
            ref_time = self.ref_time

        if period is None:
            period = self.period

        age = anchor_timestamp - ref_time

        # Portion of the period already past
        partial_period = age % period

        # Normalized to between 0.0 and 1.0
        fractional_period = partial_period / period

        return age, partial_period, fractional_period

    def compute_pos(self, pos, anchor_timestamp):
        total_val = 0.0
        for func_def in self.funcs:
            f = func_def['func']

            if isinstance(f, WaveFunc):
                func_val = f.compute(anchor_timestamp)
            else:
                func_val = base_funcs[f](pos)

            total_val += func_val

        normalized_val = total_val / len(self.funcs)
        return normalized_val

    def calc_decay(self, age):
        period_distance = age / self.period
        decay_exponent = self.decay * period_distance
        d = math.pow(math.e, decay_exponent)

        return d

    def serialize(self):
        out_funcs = []

        for func_def in self.funcs:
            f = func_def['func']

            if isinstance(f, WaveFunc):
                out_funcs.append({
                    'func': f.serialize(),
                    'phase': func_def['phase']
                })
            else:
                out_funcs.append(func_def.copy())

        return {
            'ref_time': self.ref_time,
            'period': self.period,
            'decay': self.decay,
            'funcs': out_funcs
        }


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


if __name__ == '__main__':
    period = 600
    decay = 0.02

    wave_func = {
        'ref_time': time.time(),
        'period': period,
        'decay': decay,
        'funcs': [{
            'func': 'sin',
            'phase': 0
        }]
    }

    wf = WaveFunc(serialized=wave_func)

    for i in range(0, 50):
        offset = (50 * (i + 1))
        ref_time = time.time() - offset
        val = wf.resolve(ref_time)

        print(offset, int(val * 100))
