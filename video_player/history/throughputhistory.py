import math

class ThroughputHistory:
    def __init__(self, config):
        pass
    def push(self, time, tput, lat):
        raise NotImplementedError


class Ewma(ThroughputHistory):

    # for throughput:
    default_half_life = [8000, 3000]

    def __init__(self, segment_duration):
        #global throughput
        #global latency
        
        # TODO: init somewhere else?
        throughput = None
        latency = None

        #if 'half_life' in config and config['half_life'] != None:
        #    self.half_life = [h * 1000 for h in config['half_life']]
        #else:
        self.half_life = Ewma.default_half_life

        self.latency_half_life = [h / segment_duration for h in self.half_life]

        self.throughput = [0] * len(self.half_life)
        self.weight_throughput = 0
        self.latency = [0] * len(self.half_life)
        self.weight_latency = 0

    def push(self, time, tput, lat): #here time is download_time, we use a less accurate  total_time - lrtt_at_request time
        #global throughput
        #global latency

        for i in range(len(self.half_life)):
            alpha = math.pow(0.5, time / self.half_life[i])
            self.throughput[i] = alpha * self.throughput[i] + (1 - alpha) * tput
            alpha = math.pow(0.5, 1 / self.latency_half_life[i])
            self.latency[i] = alpha * self.latency[i] + (1 - alpha) * lat

        self.weight_throughput += time
        self.weight_latency += 1

        tput = None
        lat = None
        for i in range(len(self.half_life)):
            zero_factor = 1 - math.pow(0.5, self.weight_throughput / self.half_life[i])
            t = self.throughput[i] / zero_factor
            tput = t if tput == None else min(tput, t)  # conservative case is min
            zero_factor = 1 - math.pow(0.5, self.weight_latency / self.latency_half_life[i])
            l = self.latency[i] / zero_factor
            lat = l if lat == None else max(lat, l) # conservative case is max
        #throughput = tput
        #latency = lat
        return tput, lat

