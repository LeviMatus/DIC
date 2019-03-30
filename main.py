import os

from Node import Node
import pandas as pd
import time


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()

        if 'log_time' in kw:
            name = kw.get('log_name', method.__name__.upper())
            kw['log_time'][name] = int((te - ts) * 1000)
        else:
            print('%r  %2.2f ms' % \
                  (method.__name__, (te - ts) * 1000))
        return result

    return timed


@timeit
def DIC(data, root, m=2, **kwargs):
    # Initial pass to build Itemsets of size 1
    x = [val for d in data for val in data[d].unique()]
    for i, d in enumerate([val for d in data for val in data[d].unique()]):
        root.add_child((d,))

    scan_num = 0
    while root.dashed_children_exist():
        # Pass over the dataset in m-sized chunks.
        for i, end in enumerate(range(m, len(data) + m, m)):
            for j, d in enumerate(data[i * m:end].iterrows()):
                root.increment(m * i + j, sorted(d[1]))
        scan_num += 1
    print("Scanned D {} times".format(scan_num))
    root.generate_rules()
    return root


def main():

    data = pd.read_csv("league_cleaned2.csv")

    root = Node()

    Node.total_records = len(data.values)
    Node.root = root

    time_data = {}
    root = DIC(data, root, log_time=time_data)
    print(time_data)

    # root.to_string(None)

    for i, key in enumerate(Node.rules):
        rule = Node.rules[key]
        h = [format_item(item, data) for item in sorted(list(key[0]))]
        t = [format_item(item, data) for item in sorted(list(key[1]))]
        with open('Rules.txt', 'a') as file:
            file.write("{} => {} (Support={:.2f}, Confidence={:.2f})\n"
                       .format(h, t, rule['support'], rule['confidence']))


def format_item(item, D):
    # Format an item as per the ASN 4 appendix format.
    for d in D:
        if item in D[d].unique():
            return "{}={}".format(d, item)


if __name__ == '__main__':
    try:
        os.remove("Rules.txt")
    except OSError:
        pass
    main()
