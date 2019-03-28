from StateEnum import State
from itertools import combinations
from termcolor import colored
from collections import Counter


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
    min_sup = 0.3
    min_conf = 0.4

    def __init__(self, root=None, items=(), tid=-1, scan_id=-1):
        self.root: Node = root
        self.item = items if root else items
        self.children = dict()
        self.marker = tid
        self.scan_id = scan_id
        self.depth = self.__count_parents()
        self.state = self.mark_node()
        self.support = 0

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
        for child in self.children:
            if self.children[child].state == State.DASHED_CIRCLE or self.children[child].state == State.DASHED_BOX:
                return True
            return self.children[child].dashed_children_exist()
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

    def increment(self, tid, scan_id, S=()):
        """
        For every element of S, traverse root over all combinations of remaining elements of S.
        Section 3 of DIC.

        Parameters
        ----------
        tid : transaction-id of the row being observed.
            
        scan_id : Dataset pass number.
            
        S : Tuple of values being observed.
             (Default value = ())

        """
        S = tuple(S)  # Ensure that S is indeed a tuple.

        # Nodes are only counted if they are suspected of being a large itemset.
        if self.state == State.DASHED_BOX or self.state == State.DASHED_CIRCLE:

            # If an entire scan over the dataset has completed we must stop counting.
            # For scenarios where the same item can appear in a single transaction, we avoid errant
            # state transitions to Solid by ensuring the tid is the same while scan ids are different.
            if tid == self.marker and scan_id != self.scan_id:
                self.state = State.SOLID_CIRCLE if self.state == State.DASHED_CIRCLE else State.SOLID_BOX

            # If the full scan for this itemset is not compelte, count this transaction.
            else:
                # If this is the first increment for this node, initialize its marker and scan_id.
                if self.support == 0:
                    self.marker = tid
                    self.scan_id = scan_id

                self.support = Node.calculate_support(self.support)

                # If the itemset is a candidate to be suspected of being large, transition and check its supersets
                # for the possibility of being small.
                if self.support > Node.min_sup and self.state == State.DASHED_CIRCLE:
                    self.state = State.DASHED_BOX
                    self.handle_supersets()

        # For every item in the observation, traverse the Node's children and increment and add as needed.
        for i, Si in enumerate(S):
            Si = (Si,)
            if self.children.get(Si, False):
                self.children[Si].increment(tid, scan_id, S[i+1:])
            else:
                self.add_child(Si)
                self.children[Si].increment(tid, scan_id, S[i+1:])

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

    def generate_consequent(self, child):
        """
        Given a child, generate the consequent itemsets from this Node's itemset as the antecedant.

        Parameters
        ----------
        child : Node that is child of self for which to generate consequent itemset.
            

        Returns
        -------
        set of items of the child that do not overlap with this nodes itemset.
        
        """
        antecedent_count = Counter(self.item)
        consequent_count = Counter(self.children[child].item)

        non_repeating_antecedents = list([e for e, v in antecedent_count.items() if v == 1])
        non_repeating_consequents = list([e for e, v in consequent_count.items() if v == 1])
        repeating_antecedents = {e: v for e, v in antecedent_count.items() if v > 1}
        repeating_consequents = {e: v for e, v in consequent_count.items() if v > 1}

        consequent = set(non_repeating_consequents).difference(non_repeating_antecedents)

        for item, count in repeating_consequents.items():
            if repeating_antecedents.get(item, -1) != count:
                consequent.add(item)

        return consequent

    def generate_rules(self):
        """
        For nodes with itemsets larger than 1, get the children of each node.
        For each child whose confirmed to be large, calculate the support and confidence of the antecedant U consequent.

        Continue through all nodes that are confirmed as large.
        """
        if self.root is None:
            for child in self.children:
                self.children[child].generate_rules()
        else:
            for child in self.children:
                child_state = self.children[child].state
                if child_state == State.SOLID_BOX:

                    # Generate consequent from child's itemset. Antecedent is this items itemset.
                    consequent = self.generate_consequent(child)
                    confidence = self.children[child].support/self.support

                    if confidence > Node.min_conf:
                        print("\n\nRule: {} ==> {}\nSupport={:.2f}, Confidence={:.2f}"
                              .format(self.item, consequent, self.children[child].support, confidence))

                    # For the bi-directional rule, the antecedent is the previous consequent. The new
                    # consequent is this node's itemset. To find the appropriate support, Prefix search from root
                    # for the node represented by the antecedent.
                    antecedent = consequent
                    consequent = {item for item in self.item}

                    consequent_node = Node.root.find_node(tuple(antecedent))
                    confidence = self.children[child].support/consequent_node.support

                    if confidence > Node.min_conf:
                        print("\n\nRule: {} ==> {}\nSupport={:.2f}, Confidence={:.2f}"
                              .format(antecedent, consequent, self.children[child].support, confidence))

                    self.children[child].generate_rules()

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
