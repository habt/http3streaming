import subprocess
import os

def get_request(file_name, storage_path, host_ip, cca, log):
    cca = "bbr"
    program_name = "./team"
    hq_mode = "-mode=client"
    file_path = "--path=/" + file_name
    store = "-outdir=" + storage_path
    host = "--host=" + host_ip
    congestion = "-congestion=" + cca
    pacing = "-pacing=true" 
    log_level = "-v=1"
    print("Inside get request")
    subprocess.run([program_name, hq_mode, file_path, store, host, congestion, pacing, log_level],  stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
