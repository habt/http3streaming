import subprocess
import os
import time

def select_executable(cca):
    if cca == "rbbr":
        proxygen_executable = "./team_rbbr"
    else:
        proxygen_executable = "./team_original_mvfst"
    return proxygen_executable

def blocking_request(file_name, storage_path, host_ip, cca, log):
    program_name = select_executable(cca)
    hq_mode = "-mode=client"
    file_path = "--path=/" + file_name
    store = "-outdir=" + storage_path
    host = "--host=" + host_ip
    congestion = "-congestion=" + cca
    pacing = "-pacing=true"
    vlog = "-v=0"
    print(program_name,file_name,storage_path)
    piped_request = subprocess.Popen([program_name, hq_mode, file_path, store, host, congestion, vlog],  stdout=subprocess.PIPE, stdin=subprocess.PIPE,stderr=subprocess.PIPE)
    print("after popen call")
    piped_request.stdin.write(b'exit\n')
    piped_request.stdin.flush
    print("after flushing stdin")
    time.sleep(1.0)
    piped_request.kill()
    #piped_request.wait()
    print("after popen wait")
    return True

def start_nonBlocking_request(file_name, storage_path, host_ip, cca, log):
    global piped_request
    program_name = select_executable(cca)
    hq_mode = "-mode=client"
    file_path = "--path=" + file_name
    store = "-outdir=" + storage_path
    host = "--host=" + host_ip
    congestion = "-congestion=" + cca
    pacing = "-pacing=true" 
    vlog = "-v=0"
    print(file_name,storage_path)
    piped_request = subprocess.Popen([program_name, hq_mode, file_path, store, host, congestion, vlog],  stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    print("non_blocking request started, after popen call")
    return piped_request

def get_request(piped,file_name):
    piped.stdin.write(file_name.encode('UTF-8') + b'\n')
    piped.stdin.flush()
