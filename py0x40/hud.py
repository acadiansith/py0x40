from itertools import chain, cycle, islice
import os

import numpy as np

from pygame import draw, freetype, gfxdraw, Surface, surfarray, transform

from ffmpeg import get_duration

import librosa

freetype.init()
font = freetype.Font(os.path.join('fonts', 'PetMe128.ttf'), size=10)
_, _, _, MAX_HEIGHT_10 = font.get_rect('xo-+¤|:*XO)(~=iIsSvV#@', size=10)

BOX_BORDER_COLOR = (0x33, 0x33, 0x33)
BOX_BACK_COLOR = (0xcc, 0xcc, 0xcc)
BOX_BAR_COLOR = (0, 0, 0)
BOX_ALPHA = 128

CIRCLE_OUT_COLOR = (0, 0, 0) 
CIRCLE_IN_COLOR = (0x55, 0x55, 0x55)

TEXT_COLOR = (255, 255, 255)

SPECTROGRAM_COLOR_0 = (20, 20, 20)
SPECTROGRAM_COLOR_1 = (255, 255, 255)
SPECTROGRAM_ALPHA = (155, 155, 155)

class BeatBar(object):

    def __init__(self, loop_rhythm, buildup_rhythm='', scale=(1000, 38), border_width=4):

        self.loop_rhythm = loop_rhythm
        self.buildup_rhythm = buildup_rhythm

        self.scale = self.width, self.height = scale
        self.border_width = border_width
    
    def draw(self, surface, dest, j_raw=0, buildup=False):

        self._draw_box(surface, dest)
        self._draw_circle(surface, dest)

        x, y = dest

        j = int(j_raw)

        if buildup:
            this_char = self.buildup_rhythm[j]
            next_sequence_generator = lambda: chain(self.buildup_rhythm[j+1:], cycle(self.loop_rhythm))
        else:
            this_char = self.loop_rhythm[j]
            next_sequence_generator = lambda: chain(self.loop_rhythm[j+1:], cycle(self.loop_rhythm))

        if this_char != '.':
            _, _, w, h = font.get_rect(this_char, size=18)
            font.render_to(surface, (x + 0.5 + (self.width - w) / 2, y + 0.5 + (self.height - h) / 2), None, TEXT_COLOR, size=18)
        
        scroll_width = (self.width - self.height) // 2 - self.border_width - 2

        n_chars = 40
        while True:

            scroll_chars = ''.join(islice(next_sequence_generator(), n_chars))
            x_off, y_off, w, h = font.get_rect(scroll_chars)

            if w >= scroll_width:
                break

            n_chars *= 2

        scroll_surface = Surface((scroll_width, MAX_HEIGHT_10)).convert_alpha()
        scroll_surface.fill((0, 0, 0))
        font.render_to(scroll_surface, (0, MAX_HEIGHT_10 - y_off), None, TEXT_COLOR)
        alphas = surfarray.pixels3d(scroll_surface)[:, :, :3].sum(2) // 3
        scroll_surface.fill(TEXT_COLOR)
        surfarray.pixels_alpha(scroll_surface)[:, :] = alphas
        
        surface.blit(scroll_surface, (x + self.border_width + scroll_width + self.height + 2, y + (self.height - MAX_HEIGHT_10) // 2))
        surface.blit(transform.flip(scroll_surface, True, False), (x + self.border_width, y + (self.height - MAX_HEIGHT_10) // 2))

    def _draw_box(self, surface, dest):

        x, y = dest

        box = Surface(self.scale).convert()
        box.fill(BOX_BORDER_COLOR)
        draw.rect(box, BOX_BACK_COLOR, (self.border_width, self.border_width, self.width - 2 * self.border_width, self.height - 2 * self.border_width))
        box.set_alpha(BOX_ALPHA)

        bar_height = 2 * (self.height - 2 * self.border_width) // 3
        bar_y = (self.height - bar_height) // 2
        draw.rect(box, BOX_BAR_COLOR, (self.border_width, bar_y, self.width - 2 * self.border_width, bar_height))

        surface.blit(box, dest)

    def _draw_circle(self, surface, dest):

        x, y = dest
        circ_x, circ_y = x + self.width // 2, y + self.height // 2

        for i in range(self.height // 2, 0, -1):

            t = np.exp(-i)
            color = tuple((np.array(CIRCLE_OUT_COLOR) * t + np.array(CIRCLE_IN_COLOR) * (1 - t)).astype(np.uint8))

            gfxdraw.aacircle(surface, circ_x, circ_y, (self.height // 2 - i), color)
            gfxdraw.filled_circle(surface, circ_x, circ_y, (self.height // 2 - i), color)


class InfoBox(object):

    def __init__(self, scale=(1000, 62)):

        self.scale = self.width, self.height = scale
    
    def draw(self, surface, dest, j_raw=0, t=0)


class SpectrumVisualizer(object):

    def __init__(self, loop_filename, buildup_filename=None, scale=(1000, 80), n_mels=512, rects=True):

        self.scale = self.width, self.height = scale

        self.loop, sr = librosa.load(loop_filename, mono=True)
        self.loop_spectrogram = np.maximum(0, -5 + librosa.power_to_db(librosa.feature.melspectrogram(self.loop, sr=sr, n_fft=8192, hop_length=512, n_mels=n_mels)))
        self.loop_duration = get_duration(loop_filename)
        self.power_max = np.max(self.loop_spectrogram)

        if buildup_filename is not None:
            self.buildup, sr = librosa.load(buildup_filename, mono=True)
            self.buildup_spectrogram = np.maximum(0, -5 + librosa.power_to_db(librosa.feature.melspectrogram(self.buildup, sr=sr, n_fft=4096, hop_length=512, n_mels=n_mels)))
            self.buildup_duration = get_duration(buildup_filename)
            self.power_max = max(self.power_max, np.max(self.loop_spectrogram))
        else:
            # self.buildup_spectrogram = None
            self.buildup_duration = None
        
        self.n_mels = n_mels
        self.rects = rects

    def draw(self, surface, dest, t=0, buildup=False):

        x, y = dest

        if buildup:
            spectrogram = self.buildup_spectrogram
            duration = self.buildup_duration
        else:
            spectrogram = self.loop_spectrogram
            duration = self.loop_duration
        
        j = int(t * spectrogram.shape[1] / duration)

        spectrum_surface = Surface((self.width // 2, self.height)).convert_alpha()
        spectrum_surface.fill((0, 0, 0))

        if self.rects:

            for x_off, power in zip(np.linspace(0, self.width // 2, self.n_mels + 1)[:-1], spectrogram[:, j]):

                gfxdraw.rectangle(spectrum_surface, (x_off, self.height * (1 - power / self.power_max), self.width // 2 / self.n_mels, self.height), SPECTROGRAM_ALPHA)

        else:

            points = [(0, self.height)] + [
                (x_off, self.height * (1 - power/self.power_max)) for x_off, power in zip(np.linspace(0, self.width // 2, self.n_mels + 2)[1:-1], spectrogram[:, j])
                ] + [(self.width // 2, self.height)]

            gfxdraw.aapolygon(spectrum_surface, points, SPECTROGRAM_ALPHA)
            gfxdraw.filled_polygon(spectrum_surface, points, SPECTROGRAM_ALPHA)

        alphas = surfarray.pixels3d(spectrum_surface)[:, :, :3].sum(2) // 3

        ts = (np.arange(self.height) / (self.height - 1))[:, None]
        gradient = (np.array(SPECTROGRAM_COLOR_0)[None, :] * ts + np.array(SPECTROGRAM_COLOR_1)[None, :] * (1 - ts)).astype(np.uint8)
        surfarray.pixels3d(spectrum_surface)[:, :, :] = gradient[None, :, :]

        surfarray.pixels_alpha(spectrum_surface)[:, :] = alphas


        surface.blit(spectrum_surface, (x + self.width // 2, y))
        surface.blit(transform.flip(spectrum_surface, True, False), dest)
