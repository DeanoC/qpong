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

import sge

from qgame import Game, Ball

PADDLE_LENGTH = 16

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

        # Load backgrounds
        layers = [sge.gfx.BackgroundLayer(self.paddle_sprite, sge.game.width / 2, 0, -10000,
                                      repeat_up=True, repeat_down=True)]
        self.background = sge.gfx.Background(layers, sge.gfx.Color("black"))

        sge.game.mouse.visible = False

        self.bounce_count = 0

        self.player1.set_game(self)
        self.player2.set_game(self)

        self.start_room = self.create_room()

    def create_room(self):
        # Create rooms
        self.ball = Ball(self)
        return sge.dsp.Room([self.player1, self.player2, self.ball], background=self.background)

    def game_over_wait(self):
        game_in_progress = False

    def game_over(self):
        self.event_close()