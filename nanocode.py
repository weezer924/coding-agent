class AgentStop(Exception):
    """Agent stop."""


class Agent:
    def __init__(self) -> None:
        pass

    def handle_input(self, user_input: str) -> str:
        input = user_input.strip()

        if not input:
            return ""

        if input == "/q":
            raise AgentStop

        return input


# Read: input() waits for a line.
# Eval: handle_input() does something with it.
# Print: print(output).
# Loop: while True goes back to Read.
def main():
    agent = Agent()
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
