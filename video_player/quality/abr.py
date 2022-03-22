from math import ceil

class Abr:

    #session = session_info

    def __init__(self, config):
        pass
    def get_quality_delay(self, segment_index):
        raise NotImplementedError
    def get_first_quality(self):
        return 0
    def report_delay(self, delay):
        pass
    def report_download(self, metrics, is_replacment):
        pass
    def report_seek(self, where):
        pass
    def check_abandon(self, progress, buffer_level):
        return None

    def quality_from_throughput(self, tput,segment_duration, bitrates, latency):
        #global manifest
        #global throughput
        #global latency

        p = segment_duration

        index, quality = 0, 8
        # since the highest number indicates thje lowest quality,indexes start from zero, and the difference between two video quality values is two
        #quality = len(bitrates)*2 - 2
        print("bitrates in abr:", bitrates)
        while (index + 1 < len(bitrates) and
               latency + p * bitrates[index + 1 ][1] / tput <= p):
            index +=1
        quality = bitrates[index][0]
        print("ddddddddddddelay from throughput: ", latency + p * bitrates[index][1] / tput, ", segment_duration", p)
        return index, quality
