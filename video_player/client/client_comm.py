import subprocess
import os

def get_first_request(file_name, storage_path, host_ip, cca, log):
    global piped_request
    program_name = "./team"
    hq_mode = "-mode=client"
    file_path = "--path=/" + file_name
    store = "-outdir=" + storage_path
    host = "--host=" + host_ip
    congestion = "-congestion=" + cca
    pacing = "-pacing=true" 
    vlog = "-v=1"
    print(file_name,storage_path)
    piped_request = subprocess.Popen([program_name, hq_mode, file_path, store, host, congestion, vlog],  stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    print("after popen call")
    return piped_request

def get_request(file_name, storage_path, host_ip, cca, log):
    piped_request.communicate(input=file_name)
