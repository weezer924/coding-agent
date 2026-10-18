from agent import Agent, AgentStop
from brain import ClaudeBrain
from tools import tools


# Read: input() waits for a line.
# Eval: handle_input() does something with it.
# Print: print(output).
# Loop: while True goes back to Read.
def main():
    brain = ClaudeBrain(tools=tools)
    agent = Agent(brain, tools=tools)
    print("Nanocode v0.3(Tool using)")
    print("Type /q to quit.")

    while True:
        try:
            user_input = input("\n> ")
            output = agent.handle_input(user_input)

            if output:
                print(f"\n{output}\n")

        except (AgentStop, KeyboardInterrupt):
            print("\nExiting...")
            break


if __name__ == "__main__":
    main()
