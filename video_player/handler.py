import os
from parser.parse_mpd import MPDParser
from mpegdash.nodes import MPEGDASH
from decoder.decoder_interface import decode_segment
from client.client_interface import request_file, request_movie_list
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

class RunHandler:

################################
#Init functions                #
################################

    def __init__(self, filename, host_ip, cca, log_level, naming_extra):
        self.filename = filename
        self.mpdPath = None
        self.Qbuf = None
        self.host_ip = host_ip
        self.cca = cca
        self.log_quic = log_level
        self.nextSegment = None
        self.newSegment = None
        self.rebuffCount = 0
        self.quality_changes = 0
        self.latest_quality = 0
        self.used_qualities = []
        self.ongoing_requests = [] #dictionary to keep track of ongoing segment downloads
        self.pause_cond = threading.Lock()
        self.thread = threading.Thread(target=self.queue_handler, daemon=True)
        self.stop = threading.Event()
        self.throughputList = []
        print(self.hitIt(filename, naming_extra))
        self.thread.start()
        print("Init done")

    def request_types():
        self.mpd = 'MPD'
        self.init = 'INIT'
        self.segment = 'SEGMENT'

    def hitIt(self,filename, extra):
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
        pipe = request_file(dash_path, dir_path, self.host_ip, self.cca, self.log_quic, self.mpd)
        mpdPath = f'{dir_path}/dash.mpd'
        mpdPath_isfile = os.path.isfile(mpdPath)
        print(f'{mpdPath_isfile}   file is   {mpdPath}')
        if(mpdPath_isfile):
            print("MPD path exists")
            start_readThread(pipe)
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
            request_file(f'{directory_name}/{init_base_name}{index}{file_ending}', f'{os.getcwd()}/vid/{directory_name}', self.host_ip, self.cca, self.log_quic, self.init)

    #PRE: Path to downloaded .mpd file
    #POST: parser object
    def init_Obj(self):
        try:
            self.parsObj = MPDParser(self.mpdPath)
            print("min buf time: ",self.parsObj.get_min_buffer_time())
            size = int(self.parsObj.get_min_buffer_time()/8) + 1 #TODO: here assuming max segment duration is 8 seconds
            if self.parsObj.amount_of_segments() < size:
                size = self.parsObj.amount_of_segments()
            self.Qbuf = queue.Queue(size)
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
            q = student_entrypoint(self.throughputList[-1]* 8, self.queue_time(), self.parsObj.get_qualities(), self.rebuffCount)
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
        segment_meta.append(segment[0])
        if(segment is not False):
            vidPath = self.mpdPath.replace("dash.mpd", "")
            segment_meta.append(vidPath)
            try:
                index = segment[0][-9:-4]
                quality = segment[0][-11:-10]
                segment_meta.append(index)
                segment_meta.append(quality)
            except:
                print("Failed to get index and quality")
            t1_start = perf_counter()
            segment_meta.append(t1_start)
            print(segment_meta)
            self.ongoing_requests['{self.title}/{segment[0]}'] = segment_meta #[ segment[0], vidPath, index, quality, t1_start ]
            request_file(f'{self.title}/{segment[0]}', vidPath, self.host_ip, self.cca, self.log_quic, self_segment)
            #t1_stop = perf_counter()
            request_file(f'{self.title}/{segment[1]}', vidPath, self.host_ip, self.cca, self.log_quic, self.segment)
            #calculated_throughput = round(os.path.getsize(vidPath + segment[0])/(t1_stop - t1_start))
            #self.throughputList.append(calculated_throughput)
            #self.log_message(f'THROUGHPUT {self.throughputList[-1]} B/s')
            #self.log_message(f'SEGMENTS IN BUFFER {len(self.Qbuf.queue)}')

            #self.nextSegment = self.decode_segments(vidPath, index, index, quality)
        else:
            self.nextSegment = False
            self.killthread()

        #self.Qbuf.put(self.nextSegment)

    #PRE: path to next chunks(dir), Index of start and end chunk, quality
    #POST: path to .mp4 file
    def decode_segments(self, path, si, ei, q):
        success,mp4Path = decode_segment(path, si, ei, q, self.title)#(bool, pathToMp4File)
        return mp4Path if success else [False, mp4Path]


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
                while not self.Qbuf.full():
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

# metadata: [ segment[0], vidPath, index, quality, t1_start ]
def update_metrics(self, metadata, t_end):
    segment = metadata[0]
    loc_path = metadata[1]
    index = metadata[2]
    quality = metadata[3]
    t_start = metadata[4]
    
    calculated_throughput = round(os.path.getsize(vidPath + segment)/(t_end - t_start))
    self.log_message(f'THROUGHPUT {self.throughputList[-1]} B/s')
    self.log_message(f'SEGMENTS IN BUFFER {len(self.Qbuf.queue)}')

    self.nextSegment = self.decode_segments(vidPath, index, index, quality)
    #lock queue mutex
    self.throughputList.append(calculated_throughput)
    self.Qbuf.put(self.nextSegment)
    #unlock queue mutex

def check_segment_completion(self, stdout_line):
    out_list = stdout_line.split(",")
    if out_list[0] = "EOM":
        t_end = perf_counter() # TODO: use first and last packet arrival time (through stdout stream or IPC)
        #lock ongoing dict mutex
        segment_meta = self.ongoig_requests[out_list[1]]
        print("Segment completed: ", out_list[1])
        del self.ongoig[out_list[1]]
        #release ongoing dict mutex
        update_metrics(segment_meta, t_end)

def enqueue_output(self, out, queue):
    for line in iter(out.readline, b''):
        print(line)
        check_segment_completion(line)
        queue.put(line)
    #out.close()

# stdout reading thread started after first request (of mpd)
def start_readThread(self, pipe):
    q = Queue()
    t = Thread(target=enqueue_output, args=(pipe.stdout, q))
    t.daemon = True # thread dies with the program
    t.start()


################################
#Main                          #
################################

def main():
    Handler = RunHandler('nature')

if __name__ == "__main__":
    main()
