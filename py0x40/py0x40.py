from itertools import chain, count, islice
import time
import sys

import numpy as np

import pygame
from pygame import display, image, transform, draw, Surface, surfarray

from draw import Image, AnimationManager, BlurManager, BlackoutWrapper, ColorChangeWrapper, InstantBlackout
from ffmpeg import FFmpegWriter, get_duration
from hud import BeatBar, SpectrumVisualizer
from respack import Resources

display.set_mode((1, 1), pygame.NOFRAME)

class Hues0x40(object):

    def __init__(self, respack_filenames=None, scale=(1280, 720), fps=24000/1001):

        self.resources = Resources(respack_filenames)

        self.scale = self.width, self.height = scale
        self.fps = fps

        self.loop_filename, self.buildup_filename, self.song_info = self.resources.open_song('loop_LoveOnHaightStreet')
        self.loop_rhythm = self.song_info.rhythm
        self.loop_duration = get_duration(self.loop_filename)

        if self.buildup_filename is not None:
            self.buildup_rhythm = self.song_info.buildup_rhythm
            self.buildup_duration = get_duration(self.buildup_filename)
        else:
            self.buildup_rhythm = ''
            self.buildup_duration = 0.0

        self.writer = FFmpegWriter(self.loop_filename, self.buildup_filename, scale=self.scale, frame_rate=self.fps)

        self.beat_bar = BeatBar(self.loop_rhythm, buildup_rhythm=self.buildup_rhythm)
        self.spectrum_visualizer = SpectrumVisualizer(self.loop_filename, self.buildup_filename)

        self.bg = (255, 255, 255)
        self.fg = (0, 0, 0)
        self._pick_new_image()
        self.animation_manager = AnimationManager(self.image)
        self.i = None
        self.am_i = None

        self.buildup = False
    
    def play(self, seconds):

        self.surface = Surface(self.scale)

        total_frames = int(seconds * self.fps)

        for frame in range(total_frames):

            t = frame / self.fps

            if t < self.buildup_duration:
                self.buildup = True
                self.duration = self.buildup_duration
                self.rhythm = self.buildup_rhythm

            else:
                t -= self.buildup_duration
                self.buildup = False
                self.duration = self.loop_duration
                self.rhythm = self.loop_rhythm

            j_raw = ((t / self.duration) % 1.0) * len(self.rhythm)
            j = int(j_raw)

            self._set_beat(j)
            beat_t = ((j_raw - self.am_i) % len(self.rhythm)) / len(self.rhythm) * self.duration

            self.surface.fill(self.bg)
            self.animation_manager.draw(self.surface, self.dest, beat_t)

            self.beat_bar.draw(self.surface, ((self.width - self.beat_bar.width) // 2, -4), j_raw, self.buildup)
            self.spectrum_visualizer.draw(self.surface, ((self.width - self.beat_bar.width) // 2, self.height - self.spectrum_visualizer.height), t % self.loop_duration, buildup=self.buildup)

            self.writer.write_frame(self.surface.get_buffer().raw)
    
    def close(self):

        self.writer.close()
    
    def _set_beat(self, j):

        if self.i is None:

            self.i = j
            self.am_i = j
            changed = True

        else:
            changed = False
        
        if j < self.i:
            j += len(self.rhythm)
        
        for k, s in zip(range(self.i + 1, j + 1), islice(chain(self.rhythm, self.rhythm), self.i + 1, j + 1)):

            if s != '.':
                self.i = k % len(self.rhythm)
                changed = True
        
        if changed:
            print('0x%04x' % self.i)
            self._set_anim(self.rhythm[self.i])
    
    def _set_anim(self, beat):

        beat = beat.lower()

        if beat == 'o':

            self._pick_new_colors()
            self._pick_new_image()
            self.am_i = self.i
            self.animation_manager = BlurManager(self.image, horizontal=True)
        
        elif beat == 'x':

            self._pick_new_colors()
            self._pick_new_image()
            self.am_i = self.i
            self.animation_manager = BlurManager(self.image, horizontal=False)
        
        elif beat == ':':

            self._pick_new_colors()
            self.animation_manager.set_color(self.fg)
        
        elif beat == '-':

            self._pick_new_colors()
            self._pick_new_image()
            self.am_i = self.i
            self.animation_manager = AnimationManager(self.image)

        elif beat == '+':

            self.am_i = self.i
            self.animation_manager = BlackoutWrapper(BlurManager(self.image, horizontal=True))
        
        elif beat == '|':

            self.am_i = self.i
            self.animation_manager = InstantBlackout()
        
        elif beat == '~':
            new_bg, new_fg = self._gen_new_colors()
            t_delta = self.duration * (self.i - self.am_i) / len(self.rhythm)
            self.am_i = self.i
            duration = self.duration * self._get_beat_length(self.i) / len(self.rhythm)
            self.animation_manager = ColorChangeWrapper(self.animation_manager, self.bg, self.fg, new_bg, new_fg, duration, t_delta)
        
        elif beat == '=':
            self._pick_new_image()
            new_bg, new_fg = self._gen_new_colors()
            self.am_i = self.i
            duration = self.duration * self._get_beat_length(self.i) / len(self.rhythm)
            self.animation_manager = ColorChangeWrapper(AnimationManager(self.image), self.bg, self.fg, new_bg, new_fg, duration)

        
    def _pick_new_colors(self):

        self.bg, self.fg = self._gen_new_colors()
        self.image.set_color(self.fg)
    
    def _gen_new_colors(self):

        bg = tuple(np.random.randint(160, 256) for _ in range(3))
        fg = tuple(np.random.randint(96) for _ in range(3))
        return bg, fg
    
    def _pick_new_image(self):

        self.image, self.image_info = self.resources.open_random_image()
        self.image.set_color(self.fg)

        if self.image_info.align == 'left':
            self.dest = (0, 0)

        elif self.image_info.align == 'right':
            self.dest = (self.width - self.image.width, 0)

        else: # default to center
            self.dest = ((self.width - self.image.width) // 2, 0)

    def _get_beat_length(self, i, buildup=False):

        if buildup:
            rhythm = chain(self.buildup_rhythm[(i + 1):], self.loop_rhythm)
        else:
            rhythm = chain(self.loop_rhythm[(i + 1):], self.loop_rhythm)
        
        for k, c in zip(count(1), rhythm):

            if c != '.':
                return k
        
        return None


if __name__ == '__main__':

    hues = Hues0x40()

    hues.play(5)

    hues.close()