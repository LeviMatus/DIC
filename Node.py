from StateEnum import State


class Node:

    def __init__(self, root=None, items=(), min_sup=0.2):
        self.root = root
        self.item = {items} if type(items) == str else set(tuple(items))
        self.children = dict()
        self.counter = 0
        self.marker = 0
        self.depth = self.count_parents()
        self.state = self.mark_node()
        self.min_sup = min_sup

    def mark_node(self):
        if self.root is None:
            return State.SOLID_BOX
        elif self.depth == 1:
            return State.DASHED_CIRCLE
        return State.UNMARKED

    def set_root(self, node):
        self.root = node

    def get_root(self):
        return self.root

    def add_child(self, key, itemset):
        self.children[key] = Node(self, itemset)

    def get_children(self):
        return self.children

    def get_child(self, target_key):
        return self.children.get(target_key, False)

    def get_item(self):
        return self.item

    def increment(self, S=()):
        tuple(S)

        self.counter += 1
        if self.counter > self.min_sup:
            self.state = State.DASHED_BOX

        for i, Si in enumerate(S):
            Si = (Si,)
            if self.children.get(Si, False):
                self.children[Si].increment(S[i+1:])
            else:
                self.add_child(Si, S)
                self.children[Si].increment(S[i+1:])

    def count_parents(self):
        if self.root is None:
            return 0
        return 1 + self.root.count_parents()

    def to_string(self, name, base="",):
        print(
            base if base == "" else base[:-2] + '+--',
            name[0] if len(self.item) > 0 else "Root"
        )
        for child in self.children:
            self.children[child].to_string(child, base + " |\t")
