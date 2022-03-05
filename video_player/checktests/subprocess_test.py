import subprocess
from threading  import Thread
from queue import Queue, Empty
import time

def get_first_request(file_name, storage_path, host_ip, cca):
    global piped_request
    program_name = "./team"
    hq_mode = "-mode=client"
    file_path = "--path=/" + file_name
    store = "-outdir=" + storage_path
    host = "--host=" + host_ip
    congestion = "-congestion=" + cca
    pacing = "-pacing=true"
    vlog = "-v=0"
    print(file_name,storage_path)
    piped_request = subprocess.Popen([program_name, hq_mode, file_path, store, host, congestion, vlog],  stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    #piped_request = subprocess.Popen(["./checktests/test_shell.sh", hq_mode, file_path, store, host, congestion, vlog],  stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    print("after popen call")
    return piped_request

def get_request(piped, filename):
    print("before stdin write")
    piped.stdin.write(filename)
    piped.stdin.flush()
    print("after stdin write")

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        print(line)
        queue.put(line)
    #out.close()

def start_readThread(p):
    q = Queue()
    t = Thread(target=enqueue_output, args=(p.stdout, q))
    t.daemon = True # thread dies with the program
    t.start()

def main():
    print("Hello World!")
    filename = "/test_50MB.txt"
    store = '/local/http3streaming/video_player/vid/'
    host = '10.10.2.1'
    cca = 'cubic'
    pp = get_first_request(filename, store, host, cca)
    start_readThread(pp)
    time.sleep(1)
    print("after sleep")
    get_request(pp,b'/test_25MB.txt\n')
    print("after get_request")
    time.sleep(1)
    get_request(pp,b'/test_50MB.txt\n')
    time.sleep(1)
    get_request(pp,b'exit\n')

    pp.wait()

if __name__ == "__main__":
    main()
