from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, QSlider, QStyle, QSizePolicy, QFileDialog, QListWidget, QGridLayout
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtCore import Qt, QUrl
from client.client_interface import request_movie_list, request_file
from handler import RunHandler
#import threading
import sys
from time import perf_counter
import os, shutil
import time
from os.path import exists

class Window(QWidget):

    def __init__(self):
        self.full_movie_list = []
        super().__init__()
        self.temp_start_time = 0
        self.temp_stop_time = 0
        self.total_playback_time = 0
        
        #IP of streaming server
        self.ip = next((x for x in sys.argv if x.startswith("-host=")), None)
        if(self.ip is None):
            self.ip = "130.243.27.204"
        else:
            self.ip = self.ip.split("-host=")[1]

        # CCA input
        self.cca = next((x for x in sys.argv if x.startswith("-cca=")), None)
        if(self.cca is None):
            self.cca = "cubic"
        else:
            self.cca = self.cca.split("-cca=")[1]

        # Name of video to be steamed
        self.video_name = next((x for x in sys.argv if x.startswith("-video=")), None)
        if(self.video_name is None):
            pass
            #self.video_name = "long"
        else:
            self.video_name = self.video_name.split("-video=")[1]
        
         # extra string for naming experiment log file
        self.extra = next((x for x in sys.argv if x.startswith("-extra=")), None)
        if(self.extra is None):
            pass
            #self.extra = "const_rate"
        else:
            self.extra = self.extra.split("-extra=")[1]
            print(self.extra)
        self.vlog = "1"
        self.setWindowTitle("Media Player")
        self.setGeometry(350, 100, 700, 500)
        self.movie_handler = None
        
        if(self.video_name is None):
            self.init_ui()
            self.show()
        else:
            self.request_movie() # this replaces init_ui() and show() when we request video through cli
            #self.simulate_videoplayer();

    def init_ui(self):
        # Create media player object
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.mediaPlaylist = QMediaPlaylist(self.mediaPlayer)
        self.mediaPlaylist.setPlaybackMode(3)
        self.mediaPlayer.setPlaylist(self.mediaPlaylist)

        # Create video widget object
        self.videoWidget = QVideoWidget()

        # Create 'Refresh' button
        self.refreshBtn = QPushButton("Refresh list")
        self.refreshBtn.clicked.connect(self.refresh_movie_list)

        # Create 'Select Video' button
        self.selectMovieBtn = QPushButton("Select movie")
        self.selectMovieBtn.clicked.connect(self.request_movie)

        # Create 'Play' button
        self.playBtn = QPushButton()
        self.playBtn.setEnabled(False)
        self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
        self.playBtn.clicked.connect(self.play_video)

        # Create 'Slider'
        self.slider = QSlider(Qt.Horizontal)
        self.slider.sliderMoved.connect(self.set_position)

        # Create Listbox
        self.listwidget = QListWidget()
        self.refresh_movie_list()



        layout = QGridLayout()

        layout.addWidget(self.listwidget, 0, 0, 1, 2)
        layout.addWidget(self.videoWidget, 0, 3, 1, 7)
        #layout.addWidget(self.label, 1, 0)
        layout.addWidget(self.playBtn, 1, 3)
        layout.addWidget(self.slider, 1, 4,)
        layout.addWidget(self.refreshBtn, 1, 0)
        layout.addWidget(self.selectMovieBtn, 1, 1)


        self.setLayout(layout)
        self.mediaPlayer.setVideoOutput(self.videoWidget)

        # Media player signals
        self.mediaPlayer.stateChanged.connect(self.state_changed)
        self.mediaPlayer.positionChanged.connect(self.position_changed)
        self.mediaPlayer.durationChanged.connect(self.duration_changed)
        self.mediaPlayer.mediaChanged.connect(self.clear_playlist)

        # Media playlist signals
        self.mediaPlaylist.currentIndexChanged.connect(self.index_changed)


    def remove_folders(self):
        folder = os.getcwd() + '/vid/'
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))


    def request_movie(self):
        if(self.video_name is None):
            item = self.listwidget.currentItem()
            if item is None:
                print("You must choose a movie from the list")
            else:
                self.remove_folders()
                path = item.text()
                self.movie_handler = RunHandler(path.split("/")[-1], self.ip, self.cca, self.vlog, self.extra)
        else:
            self.remove_folders()
            self.movie_handler = RunHandler(self.video_name, self.ip, self.cca, self.vlog,self.extra)
        
        self.movie_handler.log_message(f'MOVIE LOADED server at {self.ip}')
        self.temp_start_time = perf_counter()
        self.check=0
        if(self.video_name is None):
            self.open_file()
        else:
            self.simulate_videoplayer()

    def update_list_widget(self):
        self.listwidget.clear()
        for i, movie in enumerate(self.full_movie_list):
            self.listwidget.insertItem(i, movie)


    def refresh_movie_list(self):
        pathy = os.getcwd() + "/list_movies"
        request_movie_list(os.getcwd(), self.ip, self.cca, self.vlog)
        if(os.path.isfile(pathy)):
            if(exists(pathy)):
                if(os.stat("list_movies").st_size != 0):
                    with open(pathy) as f:
                        lines = f.read().splitlines()
                    self.full_movie_list = lines
            self.update_list_widget()
            os.remove(pathy)


    def open_file(self):
        self.fill_playlist()
        self.mediaPlayer.setMedia(QMediaContent(self.mediaPlaylist))
        self.mediaPlaylist.setCurrentIndex(0)
        self.playBtn.setEnabled(True)


    def play_video(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.mediaPlayer.pause()
            self.temp_stop_time = perf_counter()
            sum_of_playtime = self.temp_stop_time - self.temp_start_time
            self.total_playback_time += sum_of_playtime
        else:
            self.mediaPlayer.play()
            self.temp_start_time = perf_counter()
   
    # A simple simulated player for automatic testing. Dequeues a segment from the buffer 
    # And sleeps for the duration of the segment before retrieving the next one 
    def simulate_videoplayer(self):
        segment = True
        is_first_segment = True
        video_length = 0
        while(segment):
            segment,duration = self.movie_handler.get_next_segment()
            video_length += duration #TODO: for now only. this should not be done here
            if is_first_segment:
                play_start_time = time.time()
                is_first_segment = False
            print(segment,duration)
            if(segment):
                time.sleep(duration)
        play_duration = time.time() - play_start_time
        self.movie_handler.log_message(f'PLAY_DURATION {play_duration}')
        self.movie_handler.log_message(f'VIDEO_LENGTH {video_length}')
        print("Simulated player finished")
        sys.exit()


    def state_changed(self):
        if self.mediaPlayer.state() == QMediaPlayer.PlayingState:
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else:
            self.playBtn.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))


    def position_changed(self, time):
        self.slider.setValue(time)


    def duration_changed(self, duration):
        self.slider.setRange(0, duration)


    def index_changed(self):
        if self.check == -1 :
            self.mediaPlaylist.setPlaybackMode(2)
            self.mediaPlaylist.clear()
            self.mediaPlayer.stop()
            self.temp_stop_time = perf_counter()
            sum_of_playtime = self.temp_stop_time - self.temp_start_time
            self.total_playback_time += sum_of_playtime
            self.movie_handler.log_message(f'TOTAL PLAYTIME {sum_of_playtime}')
            return
        if self.mediaPlaylist.nextIndex() == 0:
            if self.check==0:
                self.check = 1
            if self.insert_media(self.mediaPlaylist.previousIndex()) is False:
                self.check = -1
            else:
                self.mediaPlaylist.removeMedia(self.mediaPlaylist.currentIndex())
        elif self.check == 1:
            if self.insert_media(self.mediaPlaylist.nextIndex()) is False:
                self.check = -1
            else:
                self.mediaPlaylist.removeMedia(self.mediaPlaylist.nextIndex()+1)

        print(self.check)


    def set_position(self, position):
        self.mediaPlayer.setPosition(position)


    def fill_playlist(self, slots = 2):
        for _ in range(slots):
            segment = self.movie_handler.get_next_segment()[0]
            if segment is not False:
                media_content = QMediaContent(QUrl.fromLocalFile(os.getcwd() + "/" + segment))
                self.mediaPlaylist.addMedia(media_content)
                print("In fill_playlist: media_content added")


    def clear_playlist(self):
        self.mediaPlayer.pause()
        self.mediaPlaylist.clear()


    def add_media(self):
        segment = self.movie_handler.get_next_segment()[0]
        if segment is not False:
            print("In add_media: media_content added")
            media_content = QMediaContent(QUrl.fromLocalFile(os.getcwd() + "/" + segment))
            return self.mediaPlaylist.addMedia(media_content)
        else:
            return segment

    def insert_media(self,pos):
        print("Current video index = ", self.mediaPlaylist.currentIndex())
        segment = self.movie_handler.get_next_segment()[0]
        if segment is not False:
            print("In insert_media: media_content added")
            media_content = QMediaContent(QUrl.fromLocalFile(os.getcwd() + "/" + segment))
            return self.mediaPlaylist.insertMedia(pos, media_content)
        else:
            return segment


if __name__ == "__main__":
    app = QApplication(sys.argv)
    player = Window()
    player.remove_folders()
    sys.exit(app.exec_())
