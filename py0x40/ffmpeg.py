from io import BytesIO
import re
import sys

from pygame import image, surfarray

from plumbum.cmd import ffmpeg

class FFmpegWriter(object):

    def __init__(self, loop_filename, buildup_filename=None, scale=(1280, 720), frame_rate='24000/1001'):

        self.loop_filename = loop_filename
        self.buildup_filename = buildup_filename
        self.scale = scale
        self.frame_rate = frame_rate

        self.popen = ffmpeg[self._generate_ffmpeg_options()].popen() #stderr=sys.stderr)
    
    def write_frame(self, bytes):

        self.popen.stdin.write(bytes)
    
    def close(self):

        self.popen.stdin.close()
        self.popen.wait()
    
    def _generate_ffmpeg_options(self):

        video_input_settings = [
            '-f', 'rawvideo',
            '-pix_fmt', 'rgb32',
            '-s:v', '%dx%d' % self.scale,
            '-r', self.frame_rate,
            '-i', '-'
        ]

        if self.buildup_filename is not None:
            filter_settings = [
                '-filter_complex', '''
                    amovie=filename='%s',asetpts=N/(SR*TB) [abuildup] ;
                ''' % self.buildup_filename + '''
                    amovie=filename='%s':loop=0,asetpts=N/(SR*TB) [aloop] ;
                    [abuildup] [aloop] concat=n=2:v=0:a=1 [aout]
                ''' % self.loop_filename
            ]

        else:
            filter_settings = [
                '-filter_complex', '''
                    amovie=filename='%s':loop=0,asetpts=N/(SR*TB) [aout]
                ''' % self.loop_filename
            ]

        output_settings = [
            '-map', '0:v',
            '-map', '[aout]',
            '-shortest',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-crf', 22,
            '-c:a', 'aac',
            '-b:a', '160k',
            '-ac', 2,
            '-ar', 44100,
            '-f', 'flv',
            '-y', 'out.flv'
        ]

        settings = video_input_settings + filter_settings + output_settings

        return settings


def get_duration(filename):

    exit_code, stdout, stderr = ffmpeg.run(['-i', filename, '-f', 'null', '-'])

    m = re.search(r'time=(\d\d):(\d\d):(\d\d)\.(\d\d)', stderr)

    if m is not None:
        hours, minutes, seconds, fracs = [int(x) for x in m.groups()]
        return hours * 3600 + minutes * 60 + seconds + fracs / 100
    
    else:
        raise RuntimeError('Unable to determine duration of %s' % filename)
