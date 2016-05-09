import sge
import json
import math
import numpy as np
from keras.models import Sequential
from keras.layers.core import Dense
from keras.optimizers import sgd

from qpong import Pong, Game, Player, Ball, HumanPlayer, Player,PlayerActions

class ExperienceReplay(object):
    def __init__(self, max_memory=30, discount=.9):
        self.max_memory = max_memory
        self.memory = list()
        self.discount = discount

    def remember(self, states, game_over):
        # memory[i] = [[state_t, action_t, reward_t, state_t+1], game_over?]
        self.memory.append( [states, game_over] )
        if len(self.memory) > self.max_memory:
            del self.memory[0]

    def get_batch(self, model, batch_size=10):
        len_memory = len(self.memory)
        num_actions = model.output_shape[-1]
        env_dim = self.memory[0][0][0].shape[1]
        inputs = np.zeros((min(len_memory, batch_size), env_dim)).astype(np.float32)
        targets = np.zeros((inputs.shape[0], num_actions)).astype(np.float32)

        for i, idx in enumerate(np.random.randint(0, len_memory,
                                                  size=inputs.shape[0])):
            state_t, action_t, reward_t, state_tp1 = self.memory[idx][0]
            game_over = self.memory[idx][1]

            inputs[i:i+1] = state_t
            # There should be no target values for actions not taken.
            # Thou shalt not correct actions not taken #deep
            last_predict = model.predict(state_t)[0]
            curr_predict = model.predict(state_tp1)[0]
            targets[i] = last_predict
            Q_sa = np.max(curr_predict)

            if game_over:  # if game_over is True
                targets[i, action_t] = reward_t
            else:
                # reward_t + gamma * max_a' Q(s', a')
                targets[i, action_t] = reward_t + self.discount * Q_sa

        return inputs, targets


class AIPlayer(Player):
    scored_this_frame = 0
    loss = 0

    def __init__(self, playerNum):
        super().__init__(playerNum)
        # Initialize experience replay object
        self.exp_replay = ExperienceReplay(max_memory=max_memory)

    def reset(self):
        loss = 0
        self.exp_replay = ExperienceReplay(max_memory=max_memory)

    def decide_action(self):
        # we need a few frames to get some visual history
        if type(game.screen_r_prev) is int:
            return PlayerActions.stay
        else:
            # explore the action space with an epsilon random move every now and again
            if np.random.rand() <= epsilon:
                action = np.random.randint(-1, 2, size=1)
                return PlayerActions(action[0])
            else:
                q = model.predict(game.screen_r_prev)
                action = np.argmax(q[0])-1

                return PlayerActions(action)

    def event_step(self, time_passed, delta_mult):
        action = self.decide_action()

        if self.game.game_in_progress:
           super().perform_action(action)

        if type(game.screen_r_prev) is not int:
            # store experience
            self.exp_replay.remember([game.screen_r_prev, action.value+1, self.scored_this_frame, game.screen_r], self.game.game_over_flag)
            self.scored_this_frame = 0

            inputs, targets = self.exp_replay.get_batch(model, batch_size=batch_size)

            self.loss += model.train_on_batch(inputs, targets)

        super().event_step(time_passed, delta_mult)

    def scored(self, me = True):
        if me:
            self.scored_this_frame = 1
        else:
            self.scored_this_frame = -1

        super().scored(me)

if __name__ == '__main__':
    # parameters
    epsilon = .1  # exploration
    num_actions = 3  # [move_left, stay, move_right]
    epoch = 1000
    max_memory = 20
    batch_size = 10

    game_width = 80
    game_height = 60
    hidden_size = 100

    model = Sequential()
    model.add(Dense(hidden_size, input_dim = game_width*game_height, activation = 'relu', init = 'uniform'))
    model.add(Dense(hidden_size, activation = 'relu',init = 'uniform'))
    model.add(Dense(num_actions, init = 'uniform'))
    model.compile(sgd(lr=.2), "mse")

    # If you want to continue training from a previous model, just uncomment the line bellow
    # model.load_weights("qpong_model.h5")

    p1 = AIPlayer(1)
    p2 = AIPlayer(2)

    for e in range(epoch):
        game = Pong(p1, p2, game_width, game_height)
        game.fullscreen = False

        sge.game.start()
        # game is over
        print( "P1 Score {} P2 Score {}".format(game.player1.score, game.player2.score))
        print("Epoch {:03d}/999 | Loss P1 {:.4f} | Loss P2 {:.4f}".format(e, game.player1.loss, game.player2.loss))
        p1.reset()
        p2.reset()


    print('exit')
