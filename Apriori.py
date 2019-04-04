#! /local/bin/python3

import pandas as pd
import os
from itertools import combinations
import time

candidates = dict()
result = set()
D = None
L = None
min_sup = -1.0
min_conf = -1.0

# Anonymous functions that can be used for any support calculation (or average function).
generic_support_calculator = lambda total: lambda count: count-1 + (count-(count-1))/total
support_calculator = None


def timeit(method):
    def timed(*args, **kw):
        global min_conf
        global min_sup
        global L
        global candidates
        global result

        results = {"min_sup": [], "min_conf": [], "time": []}
        grid = kw.get('grid', False)
        if kw.get('grid', False):
            for ms in grid['min_sup']:
                for mc in grid['min_conf']:
                    min_conf = mc
                    min_sup = ms

                    ts = time.time()
                    method(*args, **kw)
                    te = time.time()

                    kw['log_time']['time'].append(int((te-ts)*1000))
                    kw['log_time']["min_sup"].append(min_sup)
                    kw['log_time']["min_conf"].append(min_conf)

                    L = None
                    candidates = dict()
                    result = set()

        return results

    return timed


@timeit
def main(**kwargs):
    global support_calculator
    global L
    support_calculator = generic_support_calculator(len(D.index))

    add_candidates()

    k = 1

    while len(candidates.get(k - 1, [-1])) != 0:

        """
        For transaction (row) in D, for each candidate set in Ck,
        if the candidate set is a subset of the transaction set, then 
        increment the support counter of the candidate.
        """
        for transaction in D.values:
            transaction = list(filter(lambda x: x != '-1', transaction))
            for candidate in candidates[k].keys():
                if candidate.issubset(transaction):
                    candidates[k][candidate] = support_calculator(candidates[k][candidate]+1)

        # Declare Lk to be an empty set
        L = set()

        # Filter all candidates whose support count does not meet the threshold.
        # For those that do, add them to the L.
        for candidate_set in tuple(filter(lambda d: candidates[k][d] > min_sup, candidates[k].keys())):
            candidate_set = frozenset(candidate_set)
            result.add(candidate_set)
            L.add(candidate_set)

        # Add new candidates for Ck+1
        add_candidates(k)

        # Increment k
        k += 1

    # Ensure no itemsets of size 1 are included. These are useless.
    frequent_sets = [itemset for itemset in result if len(itemset) > 1]

    report(frequent_sets)


def add_candidates(k=0):
    new_candidates = set()

    # The first pass should just add every possible item to C1

    """
    Otherwise we must find each possible k+1 superset for each candidate. We check each candidate against each
    row to see if such supersets exist. If they do, a CK+1 is formed and added to Ck+1.
    """

    if len(candidates) == 0:
        for d in D:
            for item in D[d].unique():
                if item != - 1:
                    new_candidates.add(frozenset({item}))

    else:
        for row in D.values:
            row = list(filter(lambda x: x != '-1', row))
            for frequent_set in L:
                if frequent_set.issubset(row):
                    expanded_itemsets = combine_items(frequent_set, row)
                    new_candidates.update(expanded_itemsets)

    candidates[k + 1] = dict()
    for candidate in new_candidates:
        candidates[k + 1][candidate] = 0


def find_subsets(s):
    """
    Splits s into 2 lists of sets, heads and tails. Used to generate rules.

    :param s: a set of items, e.g. {1, 2, 3}
    :return: heads, a set of heads, e.g. [{1}, {2},  {3}, {1, 2}, {1, 3}, {2, 3}]
             tails, a set of tails, e.g. [{2, 3}, {1, 3}, {1, 2}, {3}, {2}, {1}]
    """
    heads, tails = [], []
    for i in range(1, len(s)):
        sub_sets = [set(combo) for combo in combinations(s, i)]
        heads += sub_sets
        tails += [s.difference(head) for head in sub_sets]
    return heads, tails


def combine_items(frequent_set, row):
    """
    Combine row values and sets for candidate generation. It is assumed frequent_set and row
    have already been proved to have a super/subset relationship.

    :param frequent_set: A set or frozenset of items.
    :param row: An iterable containing items.
    :return: yields a frozenset containing the joined items. Resumes when next item is needed.
    """
    set_difference = frequent_set.symmetric_difference(row)
    for itemset in set_difference:
        expanded_itemset = set(frequent_set)
        expanded_itemset.add(itemset)
        yield frozenset(expanded_itemset)


def report(frequent_sets):
    global support_calculator

    with open('Rules.txt', 'a') as file:
        file.write("2. Rules:\n\n")

    count = 0

    """
    For each frequent itemset, split it into heads and tails. Then for each head and tail, calculate the 
    support of ht with a final pass through D. If h and t are a subset of a row, then the support can increase.
    
    For each h and t, calculate the confidence. If the confidence is sufficiently high, output the rules.
    """
    for freq in frequent_sets:
        head, tail = find_subsets(set(freq))
        for (h, t) in zip(head, tail):
            h = frozenset(h)
            t = frozenset(t)
            support_ht = 0

            for row in D.values:
                if h.issubset(row) and t.issubset(row):
                    support_ht = support_calculator(support_ht+1)

            support_a = candidates[len(h)][h]
            confidence = support_ht/support_a
            if confidence > min_conf:
                h = [format_item(item) for item in sorted(list(h))]
                t = [format_item(item) for item in sorted(list(t))]

                with open('a_Rules.txt', 'a') as file:
                    file.write("{} => {} (Support={:.2f}, Confidence={:.2f})\n"
                               .format(h, t, support_ht, confidence))

                count += 1
    print(count)


def format_item(item):
    # Format an item as per the ASN 4 appendix format.
    for d in D:
        if item in D[d].unique():
            return "{}={}".format(d, item)


if __name__ == "__main__":
    # D = pd.read_csv("league_cleaned2.csv")
    D = pd.read_csv("Play_Tennis_Data_Set.csv")
    # D = D.drop(columns=['caseid'])
    D['Windy'] = D['Windy'].map({True: 'True', False: 'False'})

    # while min_sup < 0.0 or min_sup > 1.0:
    #     min_sup = float(input("Input the minimum support threshold: "))
    #
    # while min_conf < 0.0 or min_conf > 1.0:
    #     min_conf = float(input("Input the minimum confidence threshold: "))

    try:
        os.remove("a_Rules.txt")
    except OSError:
        pass
    #
    # with open('Rules.txt', 'a') as file:
    #     file.write("1. User Input:\n\nSupport={}\nConfidence={}\n\n\n".format(min_sup, min_conf))

    time_data = {"time": [], "min_sup": [], "min_conf": []}

    grid = {
        # "min_sup": [.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35],
        "min_sup": [.05],
        "min_conf": [0.2]
    }

    main(log_time=time_data, grid=grid)
    results = pd.DataFrame.from_dict(time_data)
    results.to_csv("Apriori_Tennis_Results.csv", index=False)
