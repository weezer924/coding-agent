# ------------------------------------------------------------
#  General → Binary Tree conversion (Left‑Child Right‑Sibling)
# ------------------------------------------------------------

class GeneralNode:
    """Node of a multi‑way (general) tree."""
    def __init__(self, value):
        self.value = value
        self.children = []          # list of GeneralNode objects

    def add_child(self, child_node):
        """Convenient helper to attach a child."""
        self.children.append(child_node)


class BinaryNode:
    """Node of the resulting binary tree."""
    def __init__(self, value):
        self.value = value
        self.left = None   # first (leftmost) child
        self.right = None  # next sibling to the right


def convert_general_to_binary(general_root):
    """
    Convert a general tree to a binary tree using the
    left‑child right‑sibling representation.
    Returns the root of the binary tree.
    """
    if general_root is None:
        return None

    # Create the binary node that mirrors the general node
    bin_root = BinaryNode(general_root.value)

    # Process the children list (if any)
    if general_root.children:
        # First child becomes the left child
        bin_root.left = convert_general_to_binary(general_root.children[0])

        # Remaining children are linked via right pointers (siblings)
        current = bin_root.left
        for child in general_root.children[1:]:
            current.right = convert_general_to_binary(child)
            current = current.right

    return bin_root


# ------------------------------------------------------------
# Helper functions for demonstration / testing
# ------------------------------------------------------------

def print_general(node, level=0):
    """Simple pretty‑print of a general tree."""
    if node is None:
        return
    print("  " * level + f"{node.value}")
    for child in node.children:
        print_general(child, level + 1)


def print_binary(node, prefix="", is_left=True):
    """Pretty‑print the binary tree (LCRS) sideways."""
    if node is None:
        return
    print(prefix + ("└── " if is_left else "├── ") + str(node.value))
    # left = first child, right = next sibling
    if node.left or node.right:
        # Print left (first child) first
        if node.left:
            print_binary(node.left, prefix + ("    " if is_left else "│   "), True)
        else:
            # placeholder for missing left child
            print(prefix + ("    " if is_left else "│   ") + "└── None")
        # Print right (next sibling)
        if node.right:
            print_binary(node.right, prefix + ("    " if is_left else "│   "), False)
        else:
            print(prefix + ("    " if is_left else "│   ") + "└── None")


# ------------------------------------------------------------
# Demo
# ------------------------------------------------------------
if __name__ == "__main__":
    # Build a sample general tree:
    #
    #          A
    #        / | \
    #       B  C  D
    #      / \    |
    #     E   F   G
    #
    root = GeneralNode('A')
    b = GeneralNode('B')
    c = GeneralNode('C')
    d = GeneralNode('D')
    e = GeneralNode('E')
    f = GeneralNode('F')
    g = GeneralNode('G')

    root.add_child(b)
    root.add_child(c)
    root.add_child(d)

    b.add_child(e)
    b.add_child(f)

    d.add_child(g)

    print("Original General Tree:")
    print_general(root)

    # Convert to binary
    binary_root = convert_general_to_binary(root)

    print("\nConverted Binary Tree (LCRS view):")
    print_binary(binary_root)