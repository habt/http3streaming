import os
from parser.parse_mpd import MPDParser
from mpegdash.nodes import MPEGDASH
from decoder.decoder_interface import decode_segment
from client.client_interface import *
from time import perf_counter
from quality.quality_handler import student_entrypoint
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
        self.host_ip = host_ip
        self.cca = cca
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
        self.pause_cond = threading.Lock()
        self.thread = threading.Thread(target=self.queue_handler, daemon=True)
        self.stop = threading.Event()
        self.throughputList = []
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
        try:
            self.parsObj = MPDParser(self.mpdPath)
            print("min buf time: ",self.parsObj.get_min_buffer_time())
            self.qSize = int(self.parsObj.get_min_buffer_time()/8) + 3 #TODO: here assuming max segment duration is 8 seconds
            if self.parsObj.amount_of_segments() < self.qSize:
                self.qSize = self.parsObj.amount_of_segments()
            self.Qbuf = queue.Queue(self.qSize)
            self.initialized = True
            print("Queue Size: ", size)
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
            q = 0 #student_entrypoint(self.throughputList[-1]* 8, self.queue_time(), self.parsObj.get_qualities(), self.rebuffCount)
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
                print("before meta quality is:", quality)
            except:
                print("Failed to get index and quality")
            t1_start = perf_counter()
            segment_meta.append(t1_start) #5
            video_segment = f'/{self.title}/{segment[0]}'
            audio_segment = f'/{self.title}/{segment[1]}'
            print("video: ", video_segment)
            print("audio: ", audio_segment)
            segment_meta.append(False) #6 iscompleted?

            #TODO: put segment meta construction in a function
            segment_urls = video_segment + "," + audio_segment 
            print(segment_meta)
            # TODO: change meta from list to two-level dictionary
            # Metadata order[ segment[0], vidPath, index, quality, t1_start, iscompleted, associated video/audio ]
            self.ongoing_requests[video_segment] = ["VIDEO"] + segment_meta.append(audio_segment)
            self.ongoing_requests[audio_segment] = ["AUDIO"] + segment_meta.append(video_segment)
            print(segment_meta)
            #TODO: request all segments from multipleadaptation sets (i.e. video, audio...) in a single call 
            if self.is_first_segment:
                print("retrieving first segment")
                #self.pipe = request_first_segment(segment_urls, vidPath, self.host_ip, self.cca, self.log_quic, self.segment)
                self.pipe = request_first_segment(f'/{self.title}/{segment[0]}', vidPath, self.host_ip, self.cca, self.log_quic, self.segment)
                request_new_segment(self.pipe, b'/{self.title}/{segment[1]}')
                #request_first_segment(f'{self.title}/{segment[1]}', vidPath, self.host_ip, self.cca, self.log_quic, self.segment)
                self.is_first_segment = False
                self.start_readThread(self.pipe)
            else:
                print("before requesting new segment")
                #request_new_segment(self.pipe, segment_urls)
                request_new_segment(self.pipe, b'/{self.title}/{segment[0]}')
                request_new_segment(self.pipe, b'/{self.title}/{segment[1]}')

            #calculated_throughput = round(os.path.getsize(vidPath + segment[0])/(t1_stop - t1_start))
            #self.throughputList.append(calculated_throughput)
            #self.log_message(f'THROUGHPUT {self.throughputList[-1]} B/s')
            #self.log_message(f'SEGMENTS IN BUFFER {len(self.Qbuf.queue)}')
            print("Inside parse segment : ", vidPath, index, index, quality)
            #self.nextSegment = self.decode_segments(vidPath, index, index, quality)
        else:
            self.nextSegment = False
            self.killthread()

        #self.Qbuf.put(self.nextSegment)

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
                while self.acquired_segments_count < self.parsObj.amount_of_segments():
                    # Divide by 2 because ongoing requests includes both audio and video
                    if len(self.Qbuf.queue) + len(self.ongoing_requests)/2 < self.qSize:
                        print("called for new segment")
                        print("num queued segs: ", len(self.Qbuf.queue))
                        print("num ongoing: ", len(self.ongoing_requests))
                        print("queue capacity: ", self.qSize)
                        time.sleep(2)
                        self.parse_segment()
                        if not self.newSegment:
                            break
            self.pause_cond.acquire()
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
    
    # Metadata order[ segment[0], vidPath, index, quality, t1_start, iscompleted, associated video/audio ]
    def update_metrics(self, metadata, t_end, decode_ready):
        adaptation_type = metadata[0] #video, audio or other
        segment_id = metadata[1]
        vidPath = metadata[2]
        index = metadata[3]
        quality = metadata[4]
        t_start = metadata[5]
        is_completed = metadata[6]
        associated_media = metadata[7]
        
        print("update_metrics: segment meta = ", metadata)
        print(vidPath, index,index,quality)
        if adaptation_type == "VIDEO":
            calculated_throughput = round(os.path.getsize(vidPath + segment_id)/(t_end - t_start))
            self.acquired_segments_count = self.acquired_segments_count + 1
        #decoder needs both audio and video files to be completed
        #if metadata.video_completed = True and metadata.audio_completed = True
        if decode_ready:
            self.nextSegment = self.decode_segments(vidPath, index, index, quality)
            self.Qbuf.put(self.nextSegment)
        self.throughputList.append(calculated_throughput)
        self.log_message(f'THROUGHPUT {self.throughputList[-1]} B/s')
        self.log_message(f'SEGMENTS IN BUFFER {len(self.Qbuf.queue)}')

    def is_associated_media_completed(self, metadata):
        associated_media = metadata[6] # #TODO: change to metadata['associated']
        if self.ongoing_requests[associated_media]:
            return self.ongoing_requests[associated_media][5] #TODO: change to ['iscompleted'] instead of [5]
        else:
            return False

    def check_associated_completion(self, metadata):
        if is_associated_media_completed(metadata):
            del self.ongoing_requests[seg]
            associated = segment_meta[7] # change this to a get function that returns a list of media adaptations
            del self.ongoing_requests[associated]
            return True
        else:
            return False
            self.ongoing_requests[seg][5] = True #TODO: change [5] to is completed
    
    def check_request_completion(self, stdout_line):
        out_list = stdout_line.split(b',')
        print(len(out_list), out_list)
        if len(out_list) < 2:
            return False
        if b'EOM' in out_list[1]:
            t_end = perf_counter() # TODO: use first and last packet arrival time (through stdout stream or IPC)
            seg = out_list[0].decode("utf-8")
            print("Segment completed: ", seg)
            #TODO: lock ongoing dict mutex
            self.ongoing_requests[seg][5] = True #TODO: change [5] to is completed
            segment_meta = self.ongoing_requests[seg]
            is_decode_ready = self.check_associated_completion(segment_meta)
            #release ongoing dict mutex
            self.update_metrics(segment_meta, t_end, is_decode_ready)
            return True

    def enqueue_output(self, out, queue):
        for line in iter(out.readline, b''):
            print(line)
            self.check_request_completion(line)
            queue.put(line)
        #out.close()

    # stdout reading thread started after first request (of mpd)
    def start_readThread(self, pipe):
        q = queue.Queue()
        t = threading.Thread(target=self.enqueue_output, args=(pipe.stdout, q))
        t.daemon = False # thread dies with the program
        t.start()


################################
#Main                          #
################################

def main():
    Handler = RunHandler('nature')

if __name__ == "__main__":
    main()
