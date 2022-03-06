from client.client_comm import *
import os

#Usage:
#import interface.py and use one of these functions, do not import client_comm
#Requires that you move ./hq from proxygen httpserver samples into the /python_interface/ folder

#Pre: a file name, e.g. "hello.txt"
#Post: For mpd and init :True or false if the file was able to be downloaded or not
#Post: For segement handler to the pipe
#the interface should have the same return regardless of requested file type
#TODO: modify proxygens HQClient so that request_mpd starts non-blocking request 
#and returns pipe handler so all other subsequent request on call get_request(file_name)

def request_mpd(file_name, storage_path, host, cca, log, request_type):
    blocking_request(file_name, storage_path, host, cca, log)
    return True

def request_init(file_name, storage_path, host, cca, log, request_type):
    blocking_request(file_name, storage_path, host, cca, log)
    return True

def request_first_segment(file_name, storage_path, host, cca, log, request_type):
    pipe = start_nonBlocking_request(file_name, storage_path, host, cca, log)
    print("request_first_segment: before returning file")
    return pipe

def request_new_segment(pipe,file_name):
    get_request(pipe,file_name)
    return True

#Post: List of all available movies
def request_movie_list(storage_path, host, cca, log):
    get_request("list_movies", storage_path, host, cca, log)
