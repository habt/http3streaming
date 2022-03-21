import os
from parser.parse_mpd import MPDParser
from mpegdash.nodes import MPEGDASH
from decoder.decoder_interface import decode_segment
from client.client_interface import *
from time import perf_counter
from quality.quality_handler import student_entrypoint
from quality.throughput_rule import *
from history.throughputhistory import *
#from qbuffer import QBuffer
import queue
import threading
import subprocess
import time
import math
from pathlib import Path
import logging
from datetime import datetime
import re

class RunHandler:

################################
#Init functions                #
################################

    def __init__(self, filename, host_ip, cca, log_level, naming_extra):
        self.filename = filename
        self.mpdPath = None
        self.Qbuf = None
        self.qSize = 0
        self.last_queued_segment_num = 0
        self.host_ip = host_ip
        self.cca = cca
        self.abr = None
        self.log_quic = log_level
        self.is_first_segment = True
        self.nextSegment = None
        self.newSegment = None
        self.rebuffCount = 0
        self.quality_changes = 0
        self.latest_quality = 0
        self.used_qualities = []
        self.acquired_segments_count = 0
        self.ongoing_requests = {} #dictionary to keep track of ongoing segment downloads
        self.waiting_associated = {} # dictionary to keep completed segments waiting for associated media to be completed for decoding
        self.outOfOrder = {}
        self.pause_cond = threading.Lock()
        self.tputList_lock = threading.Lock()
        self.thread = threading.Thread(target=self.queue_handler, daemon=True)
        self.stop = threading.Event()
        self.throughputList = []
        self.throughput_history = None
        self.throughput = 0
        self.latency = 0 
        print(self.hitIt(filename, naming_extra))
        self.thread.start()
        print("Init done")

    def define_request_types(self):
        self.mpd = 'MPD'
        self.init = 'INIT'
        self.segment = 'SEGMENT'

    def hitIt(self,filename, extra):
        self.define_request_types()
        self.mpdPath = self.request_mpd(filename)
        if not self.mpdPath: return "Error getting mpdPath in : request_mpd("+filename+")"
        tmp = self.init_Obj()
        self.request_all_init_files(self.parsObj.number_of_qualities())
        logging.basicConfig(filename="log/" + self.log_name_generator(filename, extra),
                                    filemode='a',
                                    format='%(asctime)s.%(msecs)d %(levelname)s %(message)s',
                                    datefmt='%H:%M:%S',
                                    level=logging.DEBUG)
        if not tmp[0]: return tmp

        print("hitit done")


    #request mpd file from client
    #triggered from videoplayer
    #get .mpd file back
    #PRE: Video_name
    #POST: path to downloaded .mpd file
    def request_mpd(self, filename):
        print("Request_mpd : filename = "+filename)
        self.title = filename
        dash_path = filename + "/dash.mpd"
        dir_path = f'{os.getcwd()}/vid/{filename}'
        os.mkdir(dir_path)
        print(dir_path)
        #print(os.listdir(path='./vid/'))
        request_mpd(dash_path, dir_path, self.host_ip, self.cca, self.log_quic, self.mpd)
        mpdPath = f'{dir_path}/dash.mpd'
        mpdPath_isfile = os.path.isfile(mpdPath)
        print(f'{mpdPath_isfile}   file is   {mpdPath}')
        if(mpdPath_isfile):
            print("MPD path exists")
            return mpdPath
        else:
            print("Bad filename")
            return False
            #return False + 'Problem with downloading mpd'


    def request_all_init_files(self, quality_count):
        directory_name = self.title
        init_base_name = "dash_init_"
        file_ending = ".m4s"

        for index in range(quality_count):
            print(index,",", f'{directory_name}/{init_base_name}{index}{file_ending}')
            request_init(f'{directory_name}/{init_base_name}{index}{file_ending}', f'{os.getcwd()}/vid/{directory_name}', self.host_ip, self.cca, self.log_quic, self.init)

    #PRE: Path to downloaded .mpd file
    #POST: parser object
    def init_Obj(self):
        self.parsObj = MPDParser(self.mpdPath)
        self.segment_duration = self.parsObj.get_presentation_duration()/self.parsObj.amount_of_segments()
        print("min buf time: ",self.parsObj.get_min_buffer_time(), ", Avg. segment duration: ", self.segment_duration)
        self.abr = ThroughputRule()
        self.throughput_history = Ewma(self.segment_duration)
        print("ttttttttttttttttttthroughput history: ", self.throughput_history)
        try:
            #TODO: here we are using avg segment duration since the segments are not of the same duration
            self.qSize = int(self.parsObj.get_min_buffer_time()/self.segment_duration) + 3 
            print("Queue Size: ", self.qSize)
            if self.parsObj.amount_of_segments() < self.qSize:
                self.qSize = self.parsObj.amount_of_segments()
            self.Qbuf = queue.Queue(self.qSize)
            self.initialized = True
            print("Queue Size: ", self.qSize)
            print("Available qualities: ",self.parsObj.get_qualities()) 
            return True, ""
        except:
            print(type(self.Qbuf), type(self.parsObj), "Failed to get QBuffer object")
            return False, "Failed to get QBuffer object"

################################
#Log                           #
################################

    def log_name_generator(self, filename, extra):
        now = datetime.now()
        dt_string = now.strftime("%Y_%m_%d_%H-%M-%S")
        return filename + "_" + self.cca + "_" + extra + "_" +  dt_string + ".log"

    def log_message(self, msg):
        logging.info(msg)
        logger = logging.getLogger(f'urbanGUI')


################################
#Segment functions             #
################################

    def get_segment_length(self):
        return self.parsObj.get_segment_duration(self.newSegment)

    def quality_handler(self):
        q = 8

        if(len(self.throughputList) > 0):
            self.tputList_lock.acquire()
            #q = student_entrypoint(self.throughputList[-1]* 8, self.queue_time(), self.parsObj.get_qualities(), self.rebuffCount)
            q = self.abr.get_quality_delay(self.throughput, self.queue_time(), self.latency, self.parsObj.get_qualities(),self.segment_duration)
            self.tputList_lock.release()
            self.rebuffCount = 0

        if q is not self.latest_quality:
            msg = ""
            self.quality_changes += 1
            if q in self.used_qualities:
                msg = f'QUALITY_CHANGE {self.latest_quality:} -> {q}'
            else:
                msg = f'QUALITY_CHANGE {self.latest_quality:} -> {q} (NEW QUALITY)'
                self.used_qualities.append(q)
            self.log_message(msg)
        self.latest_quality = q

        return q

    def parse_segment(self):
        segment_meta = []
        self.quality_handler()
        segment = self.parsObj.get_next_segment(self.latest_quality)
        if(segment is not False):
            #segment_meta.append(self.segment) #0
            segment_meta.append(segment[0]) #1
            vidPath = self.mpdPath.replace("dash.mpd", "")
            segment_meta.append(vidPath) #2
            #self.whatisthis(vidPath)
            try:
                index = segment[0][-9:-4]
                quality = segment[0][-11:-10]
                segment_meta.append(index) #3
                segment_meta.append(quality) #4
            except:
                print("Failed to get index and quality")
            t1_start = perf_counter()
            segment_meta.append(t1_start) #5
            video_segment_rl = f'/{self.title}/{segment[0]}'
            audio_segment_rl = f'/{self.title}/{segment[1]}'
            segment_meta.append(False) #6 iscompleted?

            #TODO: put segment meta construction in a function
            segment_rls = video_segment_rl + "," + audio_segment_rl 
            print(segment_meta)
            # TODO: change meta from list to two-level dictionary
            # Metadata order[ segment[0], vidPath, index, quality, t1_start, iscompleted, associated video/audio ]
            self.ongoing_requests[video_segment_rl] = ['VIDEO'] + segment_meta + [audio_segment_rl]
            self.ongoing_requests[audio_segment_rl] = ['AUDIO'] + segment_meta + [video_segment_rl]
            #TODO: request all segments from multipleadaptation sets (i.e. video, audio...) in a single call 
            if self.is_first_segment:
                print("retrieving first segment")
                #self.pipe = request_first_segment(segment_urls, vidPath, self.host_ip, self.cca, self.log_quic, self.segment)
                self.pipe = request_first_segment(video_segment_rl, vidPath, self.host_ip, self.cca, self.log_quic, self.segment)
                request_new_segment(self.pipe, audio_segment_rl)
                #request_first_segment(f'{self.title}/{segment[1]}', vidPath, self.host_ip, self.cca, self.log_quic, self.segment)
                self.is_first_segment = False
                self.start_readThread(self.pipe)
            else:
                #request_new_segment(self.pipe, segment_urls)
                request_new_segment(self.pipe, video_segment_rl)
                request_new_segment(self.pipe, audio_segment_rl)

            #calculated_throughput = round(os.path.getsize(vidPath + segment[0])/(t1_stop - t1_start))
        else:
            self.nextSegment = False
            self.killthread()


    #PRE: path to next chunks(dir), Index of start and end chunk, quality
    #POST: path to .mp4 file
    def decode_segments(self, path, si, ei, q):
        success,mp4Path = decode_segment(path, si, ei, q, self.title)#(bool, pathToMp4File)
        print("decode_segments: ", path, si, ei, q, self.title)
        return mp4Path if success else [False, mp4Path]

################################
#Media player interfaces       #
################################

    def isInitialized(self):
        return self.initialized

    #Used by the videoplayer to get next .mp4 path
    def get_next_segment(self):
        block_duration = 100 #block for the given amt of seconds if empty
        self.newSegment = self.Qbuf.get(block=True, timeout=block_duration)
        if not self.newSegment:
            print("get_next_segment ERROR: no newSegment")

        if self.pause_cond.locked():
            #print("lock locked, releasing lock")
            self.pause_cond.release()

        if(len(self.Qbuf.queue) < 1):
            self.rebuffCount +=1
            self.log_message(f'REBUFFERING {self.newSegment}')
        print("playing segment is :", self.newSegment) 
        if(self.newSegment):
            return self.newSegment, self.get_segment_length()
        else:
            return self.newSegment, 0

################################
#Queue functions               #
################################

    #PRE:
    #POST:
    #decides when new segments(chunks) should be sent to videoplayer
    def queue_handler(self):
        while not self.stop.is_set():
            with self.pause_cond:
                #while not self.Qbuf.full():
                while (self.acquired_segments_count + (len(self.ongoing_requests) + len(self.waiting_associated))/2) < self.parsObj.amount_of_segments():
                    # Divide by 2 because ongoing requests includes both audio and video
                    #if (len(self.Qbuf.queue) + len(self.outOfOrder) + (len(self.ongoing_requests) + len(self.waiting_associated))/2) < self.qSize:
                    if (len(self.Qbuf.queue) + len(self.ongoing_requests)/2) < self.qSize:
                        print("Tot num of segments: ", self.parsObj.amount_of_segments(), ", acquired segments: ", self.acquired_segments_count)
                        print("called for new segment")
                        print("num queued segs: ", len(self.Qbuf.queue))
                        print("num out of order", len(self.outOfOrder))
                        print("num ongoing: ", len(self.ongoing_requests))
                        print("num waiting: ", len(self.waiting_associated))
                        print("queue capacity: ", self.qSize)
                        #time.sleep(2)
                        print("called for new segment")
                        if len(self.ongoing_requests) < 3: #allow only one request (one audio and video) at a time (forced sequential)
                            self.parse_segment()
                        #if not self.newSegment:
                            #break
            #self.pause_cond.acquire()
        print("All segments retrieved")



    # Return the total time currently in the queue
    def queue_time(self):
        time = 0
        q = list(self.Qbuf.queue)
        for item in q:
            if item is not False:
                time += self.parsObj.get_segment_duration(item)
        return time


    # Kill the thread. Stops filling the buffer
    def killthread(self):
        self.stop.set()
        if(self.pause_cond.locked()):
            self.pause_cond.release()
            print("killing thread")




    #######################################
    # stdout Pipe stream communication    #
    # TODO: use async i/o not thread      #
    # TODO: use IPC                       #
    #######################################
    
    # Metadata order[ video/audio, segment[0], vidPath, index, quality, t1_start, iscompleted, associated video/audio ]
    def update_metrics(self, metadata, t_end, srtt, decode_ready):
        adaptation_type = metadata[0] #video, audio or other
        segment_id = metadata[1]
        vidPath = metadata[2]
        index = metadata[3]
        quality = metadata[4]
        t_start = metadata[5]
        is_completed = metadata[6]
        associated_media = metadata[7]
        
        print(vidPath, index,index,quality)
        if adaptation_type == "VIDEO":
            #TODO: replace this by actual download time using stream start and end times from quic
            estimated_download_duration = t_end - t_start - srtt
             # calculate throughput in Bytes per second
            calculated_throughput = round(os.path.getsize(vidPath + segment_id)/estimated_download_duration)
            self.tputList_lock.acquire()
            #self.throughputList.append(calculated_throughput)
            self.throughput, self.latency = self.throughput_history.push(estimated_download_duration,calculated_throughput,srtt)
            self.tputList_lock.release()
            self.log_message(f'THROUGHPUT {calculated_throughput * 8/1000000} mbps')
            print("calc. throughput: ", calculated_throughput,", hist. tput: ",self.throughput)
            print("data size: ", os.path.getsize(vidPath + segment_id), "duration(sec): ", t_end - t_start, '-', srtt, ", hist. latency: ", self.latency)
            self.acquired_segments_count = self.acquired_segments_count + 1
        #decoder needs both audio and video files to be completed
        #if metadata.video_completed = True and metadata.audio_completed = True
        print("completed update_metrics")
    
    # This function should be moved to a utils file
    def get_blocked_segs(self,seg_num):
        to_unblock = []
        #indexes =  sorted(self.outOfOrder.keys()) # sorting list is costly, in C++ atleast
        for i in sorted(self.outOfOrder.keys()):
            if int(i) == int(seg_num) + 1:
                print("Found out of order blocked segment: ", i)
                to_unblock.append(i)
                seg_num = i
            else:
                break
        return to_unblock


    def update_outOfOrder(self, seg_num):
        to_buffer_segs = self.get_blocked_segs(seg_num)
        if to_buffer_segs:
            for seg_idx in to_buffer_segs:
                self.Qbuf.put(self.outOfOrder[seg_idx])
                del self.outOfOrder[seg_idx]
                self.log_message(f'SEGMENTS IN BUFFER {len(self.Qbuf.queue)}')
            self.last_queued_segment_num = to_buffer_segs[-1]

    
    def update_play_buffer(self, segment_meta, is_decode_ready):
        if is_decode_ready:
            vidPath = segment_meta[2]
            vidIndex = segment_meta[3]
            quality = segment_meta[4]
            self.nextSegment = self.decode_segments(vidPath, vidIndex, vidIndex, quality)
            idx = vidIndex.lstrip('0')
            if(int(idx) == int(self.last_queued_segment_num) + 1):
                self.Qbuf.put(self.nextSegment) 
                self.last_queued_segment_num = idx
                self.log_message(f'SEGMENTS IN BUFFER {len(self.Qbuf.queue)}')
                #add out of order completed segments to the buffer
                if bool(self.outOfOrder):
                    self.update_outOfOrder(idx)
                else:
                    pass
            else:
                #index of the segment is the key(change 3 by 'index', i.e access the index with a key instead of list number)
                print("out of order segment found: ", vidIndex)
                self.outOfOrder[idx] = self.nextSegment


    def is_associated_media_completed(self, metadata):
        associated_media = metadata[7] # #TODO: change to metadata['associated'], also associated media should be a list
        if associated_media in self.waiting_associated:
            print("-----all media of segment downloaded? ", self.waiting_associated[associated_media][6])
            return self.waiting_associated[associated_media][6] #TODO: change to ['iscompleted'] instead of [5]
        else:
            print("segment associated media remaining")
            return False

    def check_associated_completion(self, segment_key, segment_meta):
        if self.is_associated_media_completed(segment_meta):
            del self.ongoing_requests[segment_key]
            print(segment_meta)
            associated_key = segment_meta[7] # change this to a get function that returns a list of media adaptations
            del self.waiting_associated[associated_key]
            print("----deleted from ongoing requests: ", len(self.ongoing_requests))
            return True
        else:
            self.ongoing_requests[segment_key][6] = True #TODO: change [6] to key:is_completed
            self.waiting_associated[segment_key] = self.ongoing_requests[segment_key]
            del self.ongoing_requests[segment_key]
            return False
    
    def check_request_completion(self, stdout_line):
        out_list = stdout_line.split(b',')
        if len(out_list) < 2:
            return False
        if b'EOM' in out_list[len(out_list)-1]:
            print(out_list)
            t_end = perf_counter() # TODO: use first and last packet arrival time (through stdout stream or IPC)
            segment_key = out_list[0].decode("utf-8")
            srtt_sec = float(out_list[len(out_list)-2].decode("utf-8"))/1000000
            print("Segment completed:-------- ", segment_key)
            #TODO: lock ongoing dict mutex
            segment_meta = self.ongoing_requests[segment_key]
            is_decode_ready = self.check_associated_completion(segment_key, segment_meta)
            #release ongoing dict mutex
            self.update_play_buffer(segment_meta, is_decode_ready)
            self.update_metrics(segment_meta, t_end, srtt_sec, is_decode_ready)
            return True

    def read_client_output(self, out, queue):
        for line in iter(out.readline, b''):
            #print(line)
            self.check_request_completion(line)
            queue.put(line)
        #out.close()

    # stdout reading thread started after first request (of mpd)
    def start_readThread(self, pipe):
        q = queue.Queue()
        t = threading.Thread(target=self.read_client_output, args=(pipe.stdout, q))
        t.daemon = False # thread dies with the program
        t.start()


################################
#Main                          #
################################

def main():
    Handler = RunHandler('nature')

if __name__ == "__main__":
    main()
