import sys

from agent import Agent, AgentStop
from brain import ClaudeBrain
from memory import Memory
from tools import tools


# Read: input() waits for a line.
# Eval: handle_input() does something with it.
# Print: print(output).
# Loop: while True goes back to Read.
def main():
    memory = Memory(".nanocode/memory.md")
    mode = "act" if "--act" in sys.argv else "plan"
    brain = ClaudeBrain(tools=tools)
    agent = Agent(brain, tools=tools, memory=memory, mode=mode)
    print("Nanocode v0.3(Tool using)")
    print("Type /mode [plan|act] to switch plan")
    print("Type /q to quit.")

    while True:
        try:
            user_input = input(f"\n[{agent.brain_name}:{agent.mode}] > ")
            output = agent.handle_input(user_input)

            if output:
                print(f"\n{output}\n")

        except (AgentStop, KeyboardInterrupt):
            print("\nExiting...")
            break


if __name__ == "__main__":
    main()
