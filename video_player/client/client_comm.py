import subprocess
import os

def get_request(file_name, storage_path, host_ip, cca, log):
    program_name = "./team"
    hq_mode = "-mode=client"
    file_path = "--path=/" + file_name
    store = "-outdir=" + storage_path
    host = "--host=" + host_ip
    congestion = "-congestion=" + cca
    pacing = "-pacing=true" 
    vlog = "-v=1"
    #./team -mode=client --path=/test_25MB.txt,/test_25MB.txt,/test_25MB.txt --host=130.243.26.11 -v=2 -congestion=bbr -pacing=true
    subprocess.run([program_name, hq_mode, file_path, store, host, congestion, vlog],  stdout=subprocess.DEVNULL,stderr=subprocess.STDOUT)
