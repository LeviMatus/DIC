import itertools

from StateEnum import State
from itertools import combinations
from termcolor import colored


class Node:
    """

    Static Parameters
    -----------------

    total_records : The total number or records in the dataset being analyzed.

    root : The absolute root node of the tree for fast prefix search.

    min_sup : The minimum support threshold needed for an itemset to be large.

    min_conf : The minimum confidence level needed for rule to be considered.

    """

    total_records = None
    root = None
    min_sup = 0.02
    min_conf = 0.5
    rule_count = 0
    rules = dict()

    to_transition = set()
    to_finalize = set()

    def __init__(self, root=None, items=(), tid=-1):
        self.root: Node = root
        self.item = items if root else items
        self.children = dict()
        self.marker = tid
        self.depth = self.__count_parents()
        self.state = self.mark_node()
        self.support = 0
        self.pending = False
        self.indices = []

    @staticmethod
    def calculate_support(curr_support):
        """
        Performs a constant time calculation of support given a new observation.

        Parameters
        ----------
        curr_support : The support currently observed by the calling node. One is added to this in order to calculate
        a running aggregate average of support.


        Returns
        -------
        The new observed support. The ratio of observed instances of an itemset to the number of records in the dataset.

        """
        curr_support += 1

        return curr_support - 1 + (curr_support - (curr_support - 1)) / Node.total_records

    @staticmethod
    def consequent_finder(*possible_paths):
        """
        Given a list of possible paths, find the first one which yields a valid Trie Node.

        Parameters
        ----------
        possible_paths : A generator friendly record of possible paths from the root node to a node representing
        a particular itemset.

        Returns
        -------
        A node if successful. None otherwise.
        """
        for path in possible_paths[0]:
            path = list(path)
            node = Node.root.find_node(path)
            if node is not None:
                return node
        return None

    @staticmethod
    def create_rule_set(lhs, rhs):
        """
        Given the LHS and RHS of an association rule, create the LHS and create a RHS in which
        all elements of the LHS are absent.

        Parameters
        ----------
        lhs : LHS is tuple which corresponds to the "(A B C) =>" portion of an association rule.

        rhs : RHS is tuple which corresponds to the "=> (D E)" portion of an association rule.

        Returns
        -------
        a tuple containing the lhs and rhs tuples in the form (lhs, rhs).
        """
        antecedent = tuple(lhs)
        consequent = tuple(set(rhs).difference(antecedent))
        return tuple([antecedent, consequent])

    def mark_node(self):
        """
        Initialization of node states.
        DIC starts with a SB root, DC itemsets of size 1, and all other itemset nodes as unmarked.
        """
        if self.root is None:
            return State.SOLID_BOX
        elif self.depth == 1:
            return State.DASHED_CIRCLE
        return State.UNMARKED

    def add_child(self, key, tid=-1):
        """
        Add a child node to the current node.

        Parameters
        ----------
        key: A tuple to serve as the child key. Key should be of length 1 and represent the element-wise difference
        between this node's itemset and the child's itemset.

        tid : The transation-id or index at which the child will initially be counted at. Once a full pass over the
        dataset has completed, when we observed this tid at the child again, we will close off the node for counting.
             (Default value = -1)

        Returns
        -------
        This function has no return value.

        """
        self.children[key] = Node(self, self.item+key, tid)

    def find_node(self, S):
        """
        Prefix search using elements of S.

        Parameters
        ----------
        S: tuple of items to sequentially search the root node by.


        Returns
        -------
        Node which represents itemset S if it exists, else None.

        """
        if len(S) > 0 and self.children.get((S[0],), False):
            return self.children[(S[0],)].find_node(S[1:])
        elif len(S) == 0:
            return self
        return None

    def dashed_children_exist(self):
        """
        Traverse the tree and determine if there exists a node that is dashed.

        Returns
        -------
        True if such a node exists, else False
        """
        for child in self.children.values():
            if child.state == State.DASHED_CIRCLE or child.state == State.DASHED_BOX:
                return True
            if len(child.children) == 0 or not child.dashed_children_exist():
                continue
            return True
        return False

    def handle_supersets(self):
        """
        Check to see if any children of the Node are suspected of being small.
        To do this, iterate over each of the Node's children. For each child, consider all possible combinations
        of the child's itemsets and attempt to traverse to those nodes. If the child's subset Nodes are all Boxes, then
        the child is suspected of being small and is transitioned to DC,

        """
        for child in self.children:
            transition_child = True

            # Generate all sized combinations of the child itemset from 1 to the max length of the child itemset.
            for i in range(1, len(child)):
                if not transition_child:
                    break
                paths = combinations(self.children[child].item, r=i)

                for path in paths:
                    node = Node.root.find_node(path)
                    if node.state != State.SOLID_BOX and node.state != State.DASHED_BOX:
                        transition_child = False
                        break

            if transition_child:
                self.children[child].state = State.DASHED_CIRCLE

    def increment(self, tid, S=()):
        """
        For every element of S, traverse root over all combinations of remaining elements of S.
        Section 3 of DIC.

        Parameters
        ----------
        tid : transaction-id of the row being observed.

         : Dataset pass number.

        S : Tuple of values being observed.
             (Default value = ())

        """
        S = tuple(S)  # Ensure that S is indeed a tuple.

        # Nodes are only counted if they are suspected of being a large itemset.
        if self.state == State.DASHED_BOX or self.state == State.DASHED_CIRCLE:

            # If an entire scan over the dataset has completed we must stop counting.
            # For scenarios where the same item can appear in a single transaction, we avoid errant
            # state transitions to Solid by ensuring the tid is the same while scan ids are different.
            if tid in self.indices:

                def finalize_state(node):
                    def execute():
                        node.state = State.SOLID_CIRCLE if self.state == State.DASHED_CIRCLE else State.SOLID_BOX
                    return execute
                Node.to_finalize.add(finalize_state(self))

            # If the full scan for this itemset is not compelte, count this transaction.
            else:
                # If this is the first increment for this node, initialize its marker and .
                if self.support == 0:
                    self.marker = tid

                self.indices.append(tid)
                self.support = Node.calculate_support(self.support)

                # If the itemset is a candidate to be suspected of being large, transition and check its supersets
                # for the possibility of being small.
            if self.support > Node.min_sup:
                def transition_state(node):
                    def execute():
                        if node.state == State.DASHED_CIRCLE:
                            node.state = State.DASHED_BOX
                        node.handle_supersets()
                    return execute
                Node.to_transition.add(transition_state(self))

        # For every item in the observation, traverse the Node's children and increment and add as needed.
        # If an item has been encountered before, do not double count it. Skip to the next iteration.
        # encountered = set()
        for i, Si in enumerate(S):
            if Si == '-1':
                continue
            # if Si in encountered:
                # continue
            # encountered.add(Si)
            Si = (Si,)
            if self.children.get(Si, False):
                self.children[Si].increment(tid, S[i+1:])
            else:
                self.add_child(Si)
                self.children[Si].increment(tid, S[i+1:])

    def get_depth(self):
        """
        Returns
        -------
        The levels of depth this Node is from root.
        """
        return self.depth

    def __count_parents(self):
        """
        Returns
        -------
        Calculate the number of parents this node has.
        """
        if self.root is None:
            return 0
        return 1 + self.root.get_depth()

    def generate_rules(self):
        """
        For nodes with itemsets larger than 1, get the children of each node.
        For each child whose confirmed to be large, calculate the support and confidence of the antecedant U consequent.

        Continue through all nodes that are confirmed as large.
        """
        if not self.root or len(self.children) > 0:
            for child in self.children:
                self.children[child].generate_rules()

        elif self.support > 0 and len(self.item) > 1:
            enumerated_rules = []       # All possible rules derivable from the maximal itemset. May contain duplicates.
            rules = set()               # Set of rules derived. Eliminates duplicates by nature of set structure.

            # Add all possible combinations to the list of possible rules.
            for i in range(1, len(self.item)):
                [enumerated_rules.append(subset) for subset in combinations(self.item, r=i)]

            # Maintain a possible Left Hand Side and Right Hand Side of a association rule by iterating twice
            # Over rules. For each non-equal LHS and RHS, create a rule and add it to the rules set.
            [rules.add(Node.create_rule_set(lhs, rhs)) for lhs in enumerated_rules for rhs in enumerated_rules if lhs != rhs]

            # Filter rules with () in the RHS or LHS.
            rules = filter(lambda rule: rule[0] and rule[1], rules)

            for antecedent, consequent in rules:
                antecedent = sorted(antecedent)
                consequent = sorted(consequent)

                antecedent_node = Node.root.find_node(antecedent)

                # RHS might be along another path. Permutation generator will efficiently provide each possible path
                # permutation as it is needed as opposed to forcing the entire evaluation of all permutations.
                consequent_paths = itertools.permutations(antecedent+consequent)

                consequent_node = Node.consequent_finder(consequent_paths)
                if antecedent_node.support > 0:
                    confidence = consequent_node.support/antecedent_node.support

                    if confidence > Node.min_conf and consequent_node.support > Node.min_sup:
                        Node.rules[tuple([tuple(antecedent), tuple(consequent)])] = {
                            'support': consequent_node.support,
                            'confidence': confidence
                        }
                        Node.rule_count += 1

    def to_string(self, name, base="",):
        """
        Prints a tree representation of the Hash Trie.

        Parameters
        ----------
        name : Name of the node to print
            
        base : base symbol to print on the tree. |\t if not empty string.
             (Default value = "")

        """
        node_name = name[0] if len(self.item) > 0 else "Root"
        print(
            base if base == "" else base[:-2] + '+-- {}: {} --- {} {}'.format(node_name,
                                                                              colored('{:.2f}'.format(self.support)
                                                                                      , 'red'),
                                                                              colored('{}'.format(self.state)
                                                                                      , 'cyan'),
                                                                              self.item)
        )
        for child in self.children:
            self.children[child].to_string(child, base + " |\t")
