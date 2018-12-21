from itertools import repeat

import numpy as np

from pygame import image, Surface, surfarray, transform


class Image(object):

    def __init__(self, f, namehint=None, height=720):

        if namehint is None:
            self.surface = image.load(f).convert_alpha()
        else:
            self.surface = image.load(f, namehint).convert_alpha()

        old_width = self.surface.get_width()
        old_height = self.surface.get_height()

        # if image is black with transparency, this will safely convert to black and white
        new_surface = self.surface.convert()
        new_surface.fill((255, 255, 255))
        new_surface.blit(self.surface, (0, 0))
        self.surface = new_surface

        self.width = int(old_width * height / old_height)
        self.height = height
        if old_height < height:
            self.surface = transform.scale(transform.scale2x(self.surface), (self.width, self.height)).convert_alpha()
        else:
            self.surface = transform.scale(self.surface, (self.width, self.height)).convert_alpha()

        # set alpha channel to average of rgb
        arr_rgb = surfarray.pixels3d(self.surface)
        arr_rgb[:, :, :] = 255 - arr_rgb
        arr_alpha = surfarray.pixels_alpha(self.surface)
        arr_alpha[:, :] = arr_rgb[:, :, :3].sum(2) // 3
    
    def set_color(self, color):

        surfarray.pixels3d(self.surface)[:, :, :] = np.array(color)[None, None, :]
    
    def alpha_scale(self, alpha_scale=1.0):

        new_surface = self.surface.convert_alpha()

        arr_alpha = surfarray.pixels_alpha(new_surface)
        arr_alpha[:, :] = (alpha_scale * arr_alpha).astype(np.uint8)

        return new_surface


class AnimationManager(object):

    def __init__(self, image):

        self.image = image
    
    def draw(self, surface, dest, t=0):

        surface.blit(self.image.surface, dest)

    def set_color(self, color):

        self.image.set_color(color)


class BlurManager(AnimationManager):

    def __init__(self, image, amount=11, decay=16, horizontal=True):

        self.image = image
        self.amount = amount
        self.decay = decay
        self.horizontal = horizontal

        self.faint_image = image.alpha_scale(2 / self.amount)
    
    def draw(self, surface, dest, t=0):

        x, y = dest
        jitter = (5 * self.amount * np.exp(-self.decay * t) * np.linspace(-1, 1, self.amount)).astype(int)

        if self.horizontal:
            surface.blits(zip(repeat(self.faint_image), zip(x + jitter, repeat(y))))
        else:
            surface.blits(zip(repeat(self.faint_image), zip(repeat(x), y + jitter)))
    
    def set_color(self, color):

        super().set_color(color)
        surfarray.pixels3d(self.faint_image)[:, :, :] = np.array(color)[None, None, :]


class BlackoutWrapper(AnimationManager):

    def __init__(self, animation_manager):

        self.animation_manager = animation_manager
    
    def draw(self, surface, dest, t=0):

        self.animation_manager.draw(surface, dest, t=t)

        alpha = min(255, int(2550 * t))

        blackout = surface.convert()
        blackout.fill((0, 0, 0))
        blackout.set_alpha(alpha)

        surface.blit(blackout, (0, 0))
    
    def set_color(self, color):

        self.animation_manager.set_color(color)


class InstantBlackout(AnimationManager):

    def __init__(self):

        pass
    
    def draw(self, surface, dest, t=0):

        surface.fill((0, 0, 0))
    
    def set_color(self, color):

        pass


class ColorChangeWrapper(AnimationManager):

    def __init__(self, animation_manager, old_bg, old_fg, new_bg, new_fg, duration, t_delta=0):

        self.animation_manager = animation_manager

        self.old_bg, self.old_fg = old_bg, old_fg
        self.new_bg, self.new_fg = new_bg, new_fg

        self.duration = duration
        self.t_delta = t_delta
        self.done = False
    
    def draw(self, surface, dest, t=0):

        if self.done:

            self.animation_manager.draw(surface, dest, t + self.t_delta)

        else:

            s = t / self.duration

            bg = tuple((np.array(self.new_bg) * s + np.array(self.old_bg) * (1 - s)).astype(np.uint8))
            fg = tuple((np.array(self.new_fg) * s + np.array(self.old_fg) * (1 - s)).astype(np.uint8))

            surface.fill(bg)
            self.animation_manager.set_color(fg)
            self.animation_manager.draw(surface, dest, t + self.t_delta)

    def set_color(self, color):

        self.animation_manager.set_color(color)
        self.done = True