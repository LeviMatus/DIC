from StateEnum import State
from itertools import combinations
from typing import Dict


class Node:

    def __init__(self, root=None, items=(), tid=-1, min_sup=0.4):
        self.root: Node = root
        self.item = items if root else items
        self.children: Dict[tuple, Node] = dict()
        self.counter = 0
        self.marker = tid
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

    def add_child(self, key: tuple, tid=-1):
        self.children[key] = Node(self, self.get_item()+key, tid)

    def get_children(self):
        return self.children

    def get_child(self, target_key: tuple):
        return self.children.get(target_key, False)

    def get_item(self) -> tuple:
        return self.item

    def get_root_node(self):
        if self.root.root is None:
            return self.root
        return self.root.get_root_node()

    def find_node(self, S: tuple):
        if len(S) > 0 and self.children.get(S[0], False):
            return self.children[S[0]].find_node(S[1:])
        return None

    def dashed_children_exist(self):
        for child in self.children:
            if self.children[child].state == State.DASHED_CIRCLE or self.children[child].state == State.DASHED_BOX:
                return True
            return self.children[child].dashed_children_exist()
        return False

    def handle_supersets(self) -> bool:
        for child in self.children:
            transition_child = True
            paths = []

            for i in range(0, len(child)):
                if not transition_child:
                    break
                paths += combinations(self.children[child].item)
                root = self.get_root_node()

                for path in paths:
                    node: Node = root.find_node(path)
                    if node.state != State.SOLID_BOX and node.state != State.DASHED_BOX:
                        transition_child = False
                        break

            if transition_child:
                self.children[child].state = State.DASHED_CIRCLE

    def increment(self, tid, S=()):
        S = tuple(S)

        if self.state == State.DASHED_BOX or self.state == State.DASHED_CIRCLE:

            if tid == self.marker:
                self.state = State.SOLID_CIRCLE if self.state == State.DASHED_CIRCLE else State.SOLID_BOX
                return

            if self.counter == 0:
                self.marker = tid

            self.counter += 1

            if self.counter > self.min_sup and self.state == State.DASHED_CIRCLE:
                self.state = State.DASHED_BOX
                self.handle_supersets()

        for i, Si in enumerate(S):
            Si = (Si,)
            if self.children.get(Si, False):
                self.children[Si].increment(tid, S[i+1:])
            else:
                self.add_child(Si)
                self.children[Si].increment(tid, S[i+1:])

    def get_depth(self):
        return self.depth

    def count_parents(self):
        if self.root is None:
            return 0
        return 1 + self.root.get_depth()

    def to_string(self, name, base="",):
        print(
            base if base == "" else base[:-2] + '+--',
            name[0] if len(self.item) > 0 else "Root",
            ": ", self.item
        )
        for child in self.children:
            self.children[child].to_string(child, base + " |\t")
