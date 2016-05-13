import random
from enum import Enum

import pygame
import sge


class SharedVisualMemory:
    """To save memory multiple AI share the visual memory system
    """

    def __init__(self, max_memory: int = 30):
        self.max_memory = max_memory
        self.memory = list()
        self.start_index = 0
        self.curr_index = 0

    def frame_index(self):
        return self.curr_index

    def remember(self, viz):
        self.memory.append(viz)
        self.curr_index += 1

        if (len(self.memory) > self.max_memory):
            del self.memory[0]
            self.start_index += 1

        return self.curr_index

    def __getitem__(self, item):
        if item >= self.start_index:
            return self.memory[item - self.start_index - 1]
        else:
            return self.memory[0]


class Game(sge.dsp.Game):
    width_scalar = 1
    height_scalar = 1
    game_over_flag = False
    wait_counter = 0
    ball_in_play = False
    points_to_win = 4
    game_over_wait_frames = 20
    game_in_progress = False
    ball = 0  # ball should set this to a pointer to itself
    player1 = 0  # should always be set to player 1 object
    player2 = 0  # should be set to player 2 object if 2 player game

    shared_visual_memory = SharedVisualMemory(max_memory=30)

    def event_step(self, time_passed, delta_mult):
        self.observe_world()
        self.check_scored_goal()

        if self.game_over_flag == True:
            if self.wait_counter >= self.game_over_wait_frames:
                self.game_over()
            else:
                self.game_over_wait()
                self.wait_counter += 1

    def _grab_screenshot(self):
        return pygame.surfarray.pixels_red(sge.gfx.Sprite.from_screenshot().rd["baseimages"][0])

    def _observe(self):
        screen = self._grab_screenshot() * (1 / 255)
        return screen.reshape((1, -1))

    def observe_world(self):
        self.shared_visual_memory.remember(self._observe())

    def event_key_press(self, key, char):
        if key == 'f8':
            sge.gfx.Sprite.from_screenshot().save('screenshot.jpg')
        elif key == 'f11':
            self.fullscreen = not self.fullscreen

    def event_close(self):
        self.end()

    def check_game_over(self):
        if self.player1.score >= self.points_to_win:
            return True
        elif type(self.player2) != int:
            if self.player2.score >= self.points_to_win:
                return True
        return False

    def check_goalline(self):
        # Scoring
        if self.ball.bbox_right < 0:
            return -1
        elif self.ball.bbox_left > self.current_room.width:
            return 1
        else:
            return 0

    def check_scored_goal(self):
        if self.check_game_over() == True:
            # Game Over!
            self.ball_in_play = False
            self.ball.xvelocity = 0
            self.ball.yvelocity = 0
            self.game_over_flag = True
            self.game_over()
        else:
            score = self.check_goalline()
            if (score != 0):
                self.player1.scored(score == 1)
                if type(self.player2) != int: self.player2.scored(score == -1)
                self.ball.serve(score)


class PlayerActions(Enum):
    left = -1
    stay = 0
    right = 1


class Player(sge.dsp.Object):
    def __init__(self, playerNum, paddle_x_offset=8, paddle_speed=4, paddle_vertical_force=1 / 12):
        self.playerNum = playerNum
        self.paddle_x_offset = paddle_x_offset
        self.paddle_speed = paddle_speed
        self.paddle_vertical_force = paddle_vertical_force
        self.score = 0

    def set_game(self, game):
        self.game = game
        self.score = 0
        y = self.game.height / 2

        if self.playerNum == 1:
            x = self.paddle_x_offset * self.game.x_scalar
            self.hit_direction = 1
        else:
            x = sge.game.width - self.paddle_x_offset * self.game.x_scalar
            self.hit_direction = -1

        super().__init__(x, y, sprite=game.paddle_sprite, checks_collisions=False)

    def event_create(self):
        self.score = 0
        self.y = self.game.height / 2

    def perform_action(self, action):
        self.yvelocity = action.value * self.paddle_speed

    def event_step(self, time_passed, delta_mult):
        # Keep the paddle inside the window
        if self.bbox_top < 0:
            self.bbox_top = 0
        elif self.bbox_bottom > sge.game.current_room.height:
            self.bbox_bottom = sge.game.current_room.height

    def scored(self, me):
        if me == True:
            self.score += 1

    def collide_with_ball(self):
        self.game.bounce_count += 1
        self.score += 5


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
    def __init__(self, game, start_speed=2, acceleration=0.2, max_speed=15):
        self.game = game
        self.game.ball = self
        self.start_speed = start_speed
        self.acceleration = acceleration
        self.max_speed = max_speed
        x = sge.game.width / 2
        y = sge.game.height / 2
        super(Ball, self).__init__(x, y, sprite=self.game.ball_sprite)

    def event_create(self):
        self.serve()

    def event_step(self, time_passed, delta_mult):
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

            self.xvelocity = min(abs(self.xvelocity) + self.acceleration,
                                 self.max_speed) * other.hit_direction
            self.yvelocity += (self.y - other.y) * other.paddle_vertical_force

            other.collide_with_ball()

    def serve(self, direction=None):
        if direction is None:
            direction = random.choice([-1, 1])

        self.x = self.xstart
        self.y = self.ystart
        self.game.bounce_count = 0
        self.xvelocity = self.start_speed * direction
        self.yvelocity = 0
        self.game.ball_in_play = True
