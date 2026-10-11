## Making NetHack Faster

NetHack looks like it should be cheap to simulate. The screen is mostly letters, the game is turn-based, and it ran on computers far slower than anything we use today. But running hundreds of games for billions of training steps is a different workload from one person playing in a terminal.

I built fast-nle around three things: parallelism, faster game logic, and less wasted work.

Stock NLE already supports independent games by loading a separate copy of the game library for each environment. Each copy isolates NetHack's global variables. In fast-nle, each game instead owns a state structure, allowing a shared engine to step many games through a native thread pool. The C interface also makes it straightforward to plug into PufferLib's native trainer, which calls the engine directly during training.

Inside the game, I optimised frequently used routines: compact terrain data for movement checks, and fewer repeated searches through object piles. I also reduced unnecessary terminal output and observation copying. During training, structured engine exports provide selected player-visible information directly, avoiding repeated farlook commands and menu parsing. Getting that information boundary right deserves its own debugging story!

In a replay benchmark with **512 games on eight CPU cores**, fast-nle processed **720,000 keystrokes per second**, versus **90,000 through Python's NetHack Challenge interface: 8× faster**. Stock called directly from C reached 110,000, so most of the advantage remained without Python. At 1,024 games, the advantage over Python narrowed to 5.4×.

These are short, repeated early-game workloads with matching observations, excluding policy inference, learning and PufferLib's own packing and rewards. They don't measure the direct-export savings or imply an 8× training speedup. In practice, our **4B-step policies each trained in about 19 hours**, using one RTX 4090 and CPU workers. [Measurements and methodology](benchmark/PYTHON_CHALLENGE.md).
