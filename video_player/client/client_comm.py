import subprocess
import os

def get_request(file_name, storage_path, host_ip, congestion_alg):
    program_name = "./team"
    hq_mode = "-mode=client"
    file_path = "--path=/" + file_name
    store = "-outdir=" + storage_path
    host = "--host=" + host_ip
    congestion = "-congestion=" + congestion_alg 
    vlog = "-v=2" 
    print(file_path, store)
    subprocess.run([program_name, hq_mode, file_path, store, host, congestion, vlog], stdin=subprocess.PIPE,stderr=subprocess.STDOUT)
