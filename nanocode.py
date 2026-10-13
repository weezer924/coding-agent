from agent import Agent, AgentStop
from brain import ClaudeBrain


# Read: input() waits for a line.
# Eval: handle_input() does something with it.
# Print: print(output).
# Loop: while True goes back to Read.
def main():
    brain = ClaudeBrain()
    agent = Agent(brain)
    print("Nanocode v0.1")
    print("Type /q to quit.")

    while True:
        try:
            user_input = input("\n> ")
            output = agent.handle_input(user_input)

            if output:
                print(output)

        except (AgentStop, KeyboardInterrupt):
            print("\nExiting...")
            break


if __name__ == "__main__":
    main()
