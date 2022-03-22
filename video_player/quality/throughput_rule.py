from .abr import *

class ThroughputRule(Abr):

    safety_factor = 0.9
    low_buffer_safety_factor = 0.5
    low_buffer_safety_factor_init = 0.9
    abandon_multiplier = 1.8
    abandon_grace_time = 500

    def __init__(self):
        self.ibr_safety = ThroughputRule.low_buffer_safety_factor_init
        self.no_ibr = False #config['no_ibr']
    
    #Arguments are throughput, buffer level in secs, latency(srtt), quality-bitrate list, duration of playing segment.
    def get_quality_delay(self, throughput, buffer_level, latency, bitrates_dict, segment_duration):

        bitrates = list(bitrates_dict.items())
        print("bitrates before sort:", bitrates)
        bitrates.sort(key=lambda tup: tup[1] , reverse=False)
        index, quality = self.quality_from_throughput(throughput * ThroughputRule.safety_factor, segment_duration,bitrates, latency)
        print("qqqqqqqqqqqqqqqqquality from throughput:", quality, index)
        #insufficient buffer rule check
        if not self.no_ibr:
            # insufficient buffer rule
            safe_size = self.ibr_safety * (buffer_level - latency) * throughput
            self.ibr_safety *= ThroughputRule.low_buffer_safety_factor_init
            self.ibr_safety = max(self.ibr_safety, ThroughputRule.low_buffer_safety_factor)
            for i in range(index):
                if bitrates[i + 1][1] * segment_duration > safe_size:
                    quality = bitrates[i][0]
                    print("iiiiiiiiiiiiiiiinsufficient buffer rule", quality)
                    break

        #return (quality, 0) # 0 is when to schedule, used in other rules
        return quality
    '''
    def check_abandon(self, progress, buffer_level):
        global manifest

        quality = None # no abandon

        dl_time = progress.time - progress.time_to_first_bit
        if progress.time >= ThroughputRule.abandon_grace_time and dl_time > 0:
            tput = progress.downloaded / dl_time
            size_left = progress.size - progress.downloaded
            estimate_time_left = size_left / tput
            if (progress.time + estimate_time_left >
                ThroughputRule.abandon_multiplier * manifest.segment_time):
                quality = self.quality_from_throughput(tput * ThroughputRule.safety_factor)
                estimate_size = (progress.size *
                                 manifest.bitrates[quality] / manifest.bitrates[progress.quality])
                if quality >= progress.quality or estimate_size >= size_left:
                    quality = None

        return quality
'''
