#!/usr/bin/env python3

import os

# For multiplayer game use process (ZDoom's multiplayer sync mechanism prevents threads to work as expected).
from multiprocessing import Process, cpu_count
from random import choice, random
from time import sleep, time

import vizdoom as vzd


# For singleplayer games threads can also be used.
# from threading import Thread

# Config
episodes = 1
timelimit = 1  # minutes
players = 8  # number of players
win_x = 100
win_y = 100

skip = 4
mode = vzd.Mode.PLAYER  # or Mode.ASYNC_PLAYER
ticrate = 2 * vzd.DEFAULT_TICRATE  # for Mode.ASYNC_PLAYER
random_sleep = True
const_sleep_time = 0.005
window = True
resolution = vzd.ScreenResolution.RES_320X240

args = ""
console = False
config = os.path.join(vzd.scenarios_path, "cig.cfg")


def setup_player():
    game = vzd.DoomGame()

    game.load_config(config)
    game.set_mode(mode)
    game.add_game_args(args)
    game.set_screen_resolution(resolution)
    game.set_console_enabled(console)
    game.set_window_visible(window)
    game.set_ticrate(ticrate)

    actions = [
        [1, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 1, 0, 0, 0, 0, 0, 0],
    ]

    return game, actions


def player_action(game, player_sleep_time, actions, player_skip):
    if random_sleep:
        sleep(random() * 0.005 + 0.001)
    elif player_sleep_time > 0:
        sleep(player_sleep_time)

    game.make_action(choice(actions), player_skip)

    if game.is_player_dead():
        game.respawn_player()


def player_host(p):
    game, actions = setup_player()

    # Setup multiplayer deathmatch game for {p} players that will time out after {timelimit} minutes
    game.add_game_args(
        f"-host {p} -netmode 0 -deathmatch +timelimit {timelimit} +sv_spawnfarthest 1"
    )
    # Use additional arguments to set player name, color and window position
    game.add_game_args(f"+name Player0 +colorset 0 +win_x {win_x} +win_y {win_y}")
    # Add additional arguments
    game.add_game_args(args)

    game.init()

    action_count = 0
    player_sleep_time = const_sleep_time
    player_skip = skip

    for i in range(episodes):
        print(f"Episode #{i + 1}")
        episode_start_time = None

        while not game.is_episode_finished():
            if episode_start_time is None:
                episode_start_time = time()

            state = game.get_state()
            assert state is not None
            print("Player0:", state.number, action_count, game.get_episode_time())

            player_action(game, player_sleep_time, actions, player_skip)
            action_count += 1

        print("Player0 frags:", game.get_game_variable(vzd.GameVariable.FRAGCOUNT))

        print("Host: Episode finished!")
        player_count = int(game.get_game_variable(vzd.GameVariable.PLAYER_COUNT))
        for i in range(1, player_count + 1):
            print(
                f"Host: Player{i}:",
                game.get_game_variable(eval(f"vzd.GameVariable.PLAYER{i}_FRAGCOUNT")),
            )
        print("Host: Episode processing time:", time() - episode_start_time)

        # Starts a new episode. All players have to call new_episode() in multiplayer mode.
        game.new_episode()

    game.close()


def player_join(p):
    game, actions = setup_player()

    # Join existing game
    game.add_game_args("-join 127.0.0.1")
    # Use additional arguments to set player name, color and window position
    game.add_game_args(
        f"+name Player{p} +colorset 0 +win_x {win_x + p % 4 * game.get_screen_width()} +win_y {win_y + p // 4 * game.get_screen_height()} "
    )
    # Add additional arguments
    game.add_game_args(args)

    game.init()

    action_count = 0
    player_sleep_time = const_sleep_time
    player_skip = skip

    for i in range(episodes):

        while not game.is_episode_finished():
            state = game.get_state()
            assert state is not None
            print(
                f"Player{p}:",
                state.number,
                action_count,
                game.get_episode_time(),
            )
            player_action(game, player_sleep_time, actions, player_skip)
            action_count += 1

        print(
            f"Player{p} frags:",
            game.get_game_variable(vzd.GameVariable.FRAGCOUNT),
        )
        game.new_episode()

    game.close()


if __name__ == "__main__":
    print("Players:", players)
    print("CPUS:", cpu_count())

    processes = []
    for i in range(1, players):
        p_join = Process(target=player_join, args=(i,))
        p_join.start()
        processes.append(p_join)

    player_host(players)

    print("Done")
