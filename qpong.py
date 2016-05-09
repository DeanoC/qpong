#!/usr/bin/env python3

# Pong Example
# Written in 2013-2016 by onpon4 <onpon4@riseup.net>
# modified 2016 by Deano Calver <deano@cloudpixies.com> to use machine learning
#
# To the extent possible under law, the author(s) have dedicated all
# copyright and related and neighboring rights to this software to the
# public domain worldwide. This software is distributed without any
# warranty.
#
# You should have received a copy of the CC0 Public Domain Dedication
# along with this software. If not, see
# <http://creativecommons.org/publicdomain/zero/1.0/>.

import os
import random
from enum import Enum

import sge
import pygame
import pygame.surfarray as surfarray

PADDLE_XOFFSET = 8
PADDLE_SPEED = 4
PADDLE_VERTICAL_FORCE = 1 / 12
PADDLE_LENGTH = 16
BALL_START_SPEED = 2
BALL_ACCELERATION = 0.2
BALL_MAX_SPEED = 15
POINTS_TO_WIN = 10
TEXT_OFFSET = 2
GAME_OVER_WAIT_FRAMES = 20

class Game(sge.dsp.Game):
    screen_r_prev = 0
    screen_r = 0
    width_scalar = 1
    height_scalar = 1
    game_over_flag = False
    wait_counter = 0
    game_in_progress = True

    def event_step(self, time_passed, delta_mult):
        self.project_sprite(self.hud_sprite, 0, self.width / 2, 0)
        self.observe_world()

        if self.game_over_flag == True:
            if self.wait_counter >= GAME_OVER_WAIT_FRAMES:
                self.game_over()
            else:
                self.game_over_wait()
                self.wait_counter+=1

    def _grab_screenshot(self):
        return pygame.surfarray.pixels_red(sge.gfx.Sprite.from_screenshot().rd["baseimages"][0] )

    def _observe(self):
        screen = self._grab_screenshot() * (1/255)
        return screen.reshape((1,-1))

    def observe_world(self):
        self.screen_r_prev = self.screen_r
        self.screen_r = self._observe()

    def event_key_press(self, key, char):

        if key == 'f8':
            sge.gfx.Sprite.from_screenshot().save('screenshot.jpg')
        elif key == 'f11':
            self.fullscreen = not self.fullscreen
        elif key == 'escape':
            self.event_close()
        elif key in ('p', 'enter'):
            if self.game_in_progress:
                self.pause()
            else:
                self.game_in_progress = True
                self.create_room().start()

    def event_close(self):
        self.end()

    def event_paused_key_press(self, key, char):
        if key == 'escape':
            # This allows the player to still exit while the game is
            # paused, rather than having to unpause first.
            self.event_close()
        else:
            self.unpause()

    def event_paused_close(self):
        # This allows the player to still exit while the game is paused,
        # rather than having to unpause first.
        self.event_close()

class PlayerActions(Enum):
    left = -1
    stay = 0
    right = 1

class Player(sge.dsp.Object):

    def __init__(self, playerNum):
        self.playerNum = playerNum

    def set_game(self, game):
        self.game = game
        y = self.game.height / 2

        if self.playerNum == 1:
            x = PADDLE_XOFFSET * self.game.x_scalar
            self.hit_direction = 1
        else:
            x = sge.game.width - PADDLE_XOFFSET * self.game.x_scalar
            self.hit_direction = -1

        super().__init__(x, y, sprite=game.paddle_sprite, checks_collisions=False)

    def event_create(self):
        self.score = 0
        self.y = self.game.height / 2

    def perform_action(self, action):
        self.yvelocity = action.value * PADDLE_SPEED

    def event_step(self, time_passed, delta_mult):
        # Keep the paddle inside the window
        if self.bbox_top < 0:
            self.bbox_top = 0
        elif self.bbox_bottom > sge.game.current_room.height:
            self.bbox_bottom = sge.game.current_room.height

    def scored(self, me):
        if me:
            self.score += 1

class HumanPlayer(Player):

    def __init__(self, playerNum):
        super().__init__(playerNum)

        if playerNum == 1:
            self.up_key = "w"
            self.down_key = "s"
        else:
            self.up_key = "up"
            self.down_key = "down"

    def event_step(self, time_passed, delta_mult):
        # Movement
        key_motion = (sge.keyboard.get_pressed(self.down_key) -
                      sge.keyboard.get_pressed(self.up_key))

        super().perform_action(PlayerActions(key_motion))

        super().event_step(time_passed, delta_mult)

class Ball(sge.dsp.Object):

    def __init__(self, game):
        self.game = game
        x = sge.game.width / 2
        y = sge.game.height / 2
        super(Ball, self).__init__(x, y, sprite=self.game.ball_sprite)

    def event_create(self):
        self.serve()

    def event_step(self, time_passed, delta_mult):
        # Scoring
        if self.bbox_right < 0:
            self.game.player1.scored(False)
            self.game.player2.scored(True)
            self.serve(-1)
        elif self.bbox_left > sge.game.current_room.width:
            self.game.player2.scored(False)
            self.game.player1.scored(True)
            self.serve(1)

        # Bouncing off of the edges
        if self.bbox_bottom > sge.game.current_room.height:
            self.bbox_bottom = sge.game.current_room.height
            self.yvelocity = -abs(self.yvelocity)
        elif self.bbox_top < 0:
            self.bbox_top = 0
            self.yvelocity = abs(self.yvelocity)

    def event_collision(self, other, xdirection, ydirection):
        if isinstance(other, Player):
            if other.hit_direction == 1:
                self.bbox_left = other.bbox_right + 1
            else:
                self.bbox_right = other.bbox_left - 1

            self.xvelocity = min(abs(self.xvelocity) + BALL_ACCELERATION,
                                 BALL_MAX_SPEED) * other.hit_direction
            self.yvelocity += (self.y - other.y) * PADDLE_VERTICAL_FORCE

    def serve(self, direction=None):
        self.game.refresh_hud()

        if direction is None:
            direction = random.choice([-1, 1])

        self.x = self.xstart
        self.y = self.ystart

        if (self.game.player1.score < POINTS_TO_WIN and
                self.game.player2.score < POINTS_TO_WIN):
            # Next round
            self.xvelocity = BALL_START_SPEED * direction
            self.yvelocity = 0
        else:
            # Game Over!
            self.xvelocity = 0
            self.yvelocity = 0
            self.game.hud_sprite.draw_clear()
            x = self.game.hud_sprite.width / 2
            self.game.game_over_flag = True


class Pong(Game):

    def __init__(self, player1, player2, width, height ):
        super().__init__(width=width, height=height, fps=120, window_text="Pong")
        self.x_scalar = width / 160
        self.y_scalar = height / 120

        self.player1 = player1
        self.player2 = player2

        self.paddle_sprite = sge.gfx.Sprite(width=3*self.x_scalar, height=PADDLE_LENGTH*self.y_scalar, origin_x=2*self.x_scalar, origin_y=2*self.y_scalar)
        self.ball_sprite = sge.gfx.Sprite(width=3*self.x_scalar, height=4*self.y_scalar, origin_x=2*self.x_scalar, origin_y=4*self.y_scalar)
        self.paddle_sprite.draw_rectangle(0, 0, self.paddle_sprite.width, self.paddle_sprite.height,
                                 fill=sge.gfx.Color("white"))
        self.ball_sprite.draw_rectangle(0, 0, self.ball_sprite.width, self.ball_sprite.height,
                               fill=sge.gfx.Color("white"))
        self.hud_sprite = sge.gfx.Sprite(width=160*self.x_scalar, height=20*self.y_scalar, origin_x=80*self.x_scalar, origin_y=0)

        # Load backgrounds
        layers = [sge.gfx.BackgroundLayer(self.paddle_sprite, sge.game.width / 2, 0, -10000,
                                      repeat_up=True, repeat_down=True)]
        self.background = sge.gfx.Background(layers, sge.gfx.Color("black"))

        # Load fonts
        self.hud_font = sge.gfx.Font("Droid Sans Mono", size=10)
        sge.game.mouse.visible = False

        self.player1.set_game(self)
        self.player2.set_game(self)

        self.start_room = self.create_room()

    def create_room(self):
        # Create rooms
        self.ball = Ball(self)
        return sge.dsp.Room([self.player1, self.player2, self.ball], background=self.background)

    def refresh_hud(self):
        pass
        # This fixes the HUD sprite so that it displays the correct score.
        self.hud_sprite.draw_clear()
        x = self.hud_sprite.width / 2
        self.hud_sprite.draw_text(self.hud_font, str(self.player1.score), x - TEXT_OFFSET,
                         0, color=sge.gfx.Color("white"),
                         halign="right", valign="top")
        self.hud_sprite.draw_text(self.hud_font, str(self.player2.score), x + TEXT_OFFSET,
                         0, color=sge.gfx.Color("white"),
                         halign="left", valign="top")
    def game_over_wait(self):
        pass
        p1text = "WIN" if self.player1.score > self.player2.score else "LOSE"
        p2text = "WIN" if self.player2.score > self.player1.score else "LOSE"
        self.hud_sprite.draw_text(self.hud_font, p1text, self.ball.x - TEXT_OFFSET,
                                       TEXT_OFFSET, color=sge.gfx.Color("white"),
                                       halign="right", valign="top")
        self.hud_sprite.draw_text(self.hud_font, p2text, self.ball.x + TEXT_OFFSET,
                                       TEXT_OFFSET, color=sge.gfx.Color("white"),
                                       halign="left", valign="top")
        game_in_progress = False

    def game_over(self):
        self.event_close()