import json
from os import path

import numpy as np
import sge
from keras.layers.core import Dense
from keras.models import Sequential
from keras.optimizers import sgd

from qgame import Player, PlayerActions
from qsquash import Squash


class ExperienceReplay(object):
    def __init__(self, max_memory=30, discount=.9):
        self.max_memory = max_memory
        self.memory = list()
        self.discount = discount

    def remember(self, frame_index, action, reward, game_over):
        # memory[i] = [state_t, action, reward, state_t+1, game_over]
        nidx = frame_index
        cidx = nidx - 1

        self.memory.append([cidx, action, reward, nidx, game_over])
        if len(self.memory) > self.max_memory:
            del self.memory[0]

    def get_batch(self, model, batch_size=10):
        len_memory = len(self.memory)
        num_actions = model.output_shape[-1]
        env_dim = game.shared_visual_memory[0].shape[1]
        inputs = np.zeros((min(len_memory, batch_size), env_dim)).astype(np.float32)
        targets = np.zeros((inputs.shape[0], num_actions)).astype(np.float32)

        for i, idx in enumerate(np.random.randint(0, len_memory,
                                                  size=inputs.shape[0])):
            cidx, action_t, reward_t, nidx, game_over = self.memory[idx]
            state_t = game.shared_visual_memory[cidx]
            state_tp1 = game.shared_visual_memory[nidx]

            inputs[i:i + 1] = state_t
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
        self.loss = 0
        self.exp_replay = ExperienceReplay(max_memory=max_memory)

    def decide_action(self):
        # we need a few frames to get some visual history
        if game.shared_visual_memory.frame_index() <= 1:
            return PlayerActions.stay
        else:
            # explore the action space with an epsilon random move every now and again
            if np.random.rand() <= epsilon:
                action = np.random.randint(-1, 2, size=1)
                return PlayerActions(action[0])
            else:
                q = model.predict(game.shared_visual_memory[game.shared_visual_memory.frame_index()])
                action = np.argmax(q[0]) - 1

                return PlayerActions(action)

    def event_step(self, time_passed, delta_mult):
        action = self.decide_action()

        super().perform_action(action)

        frame_index = game.shared_visual_memory.frame_index()

        if (game.shared_visual_memory.frame_index() >= 2):
            # store experience
            self.exp_replay.remember(frame_index, (action.value) + 1, self.score / 10, self.game.game_over_flag)
            self.scored_this_frame = 0

            inputs, targets = self.exp_replay.get_batch(model, batch_size=batch_size)

            self.loss += model.train_on_batch(inputs, targets)

        super().event_step(time_passed, delta_mult)

    def scored(self, me=True):
        # single player game, i can only lose points :(
        self.scored_this_frame = -1
        self.score -= 1

    def collide_with_ball(self):
        self.score += 5


if __name__ == '__main__':
    # parameters
    epsilon = .2  # exploration
    num_actions = 3  # [move_left, stay, move_right]
    epoch = 100
    max_memory = 100
    batch_size = 20

    game_width = 80
    game_height = 60
    hidden_size = 500
    total_score = 0

    model = Sequential()
    model.add(Dense(hidden_size, input_dim=game_width * game_height, activation='relu', init='uniform'))
    model.add(Dense(hidden_size, activation='relu', init='uniform'))
    model.add(Dense(num_actions, init='uniform'))
    model.compile(sgd(lr=.2), "mse")

    # If you want to continue training from a previous model, just uncomment the line bellow
    if path.isfile("qsquash_ai.h5"):
        model.load_weights("qsquash_ai.h5")

    p1 = AIPlayer(1)

    for e in range(epoch):
        game = Squash(p1, game_width, game_height)
        game.fullscreen = False

        sge.game.start()
        if isinstance(p1, AIPlayer):
            print("Epoch {:03d}/99 | Loss P1 {:.4f} Score {}".format(e, game.player1.loss, game.player1.score))
            total_score += game.player1.score
        print("Mean Score {}".format(total_score / (e + 1)))
        if p1 is AIPlayer:
            p1.reset()

    # Save trained model weights and architecture, this will be used by the visualization code
    model.save_weights("qsquash_ai.h5", overwrite=True)
    with open("qsquash_ai.json", "w") as outfile:
        json.dump(model.to_json(), outfile)
