#!/usr/bin/env python3

import sge

from qgame import Game, Ball

PADDLE_LENGTH = 16


class SquashBall(Ball):
    def event_step(self, time_passed, delta_mult):
        # Bouncing off of the edges
        if self.bbox_bottom > sge.game.current_room.height:
            self.bbox_bottom = sge.game.current_room.height
            self.yvelocity = -abs(self.yvelocity)
        elif self.bbox_top < 0:
            self.bbox_top = 0
            self.yvelocity = abs(self.yvelocity)
        elif self.bbox_right > sge.game.current_room.width:
            self.bbox_right = sge.game.current_room.width
            self.xvelocity = -abs(self.xvelocity)


class Squash(Game):
    goals = 0

    def __init__(self, player1, width, height):
        super().__init__(width=width, height=height, fps=120, window_text="Pong")
        self.x_scalar = width / 160
        self.y_scalar = height / 120

        self.player1 = player1

        self.paddle_sprite = sge.gfx.Sprite(width=3 * self.x_scalar, height=PADDLE_LENGTH * self.y_scalar,
                                            origin_x=2 * self.x_scalar, origin_y=2 * self.y_scalar)
        self.ball_sprite = sge.gfx.Sprite(width=3 * self.x_scalar, height=4 * self.y_scalar, origin_x=2 * self.x_scalar,
                                          origin_y=4 * self.y_scalar)
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

        self.start_room = self.create_room()

    def create_room(self):
        # Create rooms
        self.ball = SquashBall(self)
        return sge.dsp.Room([self.player1, self.ball], background=self.background)

    def game_over_wait(self):
        game_in_progress = False

    def game_over(self):
        self.event_close()

    def check_game_over(self):
        if self.check_goalline() != 0:
            self.goals += 1
        if self.goals > self.points_to_win:
            return True
        else:
            return False
