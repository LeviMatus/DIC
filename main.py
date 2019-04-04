import os

import gc

from Node import Node
import pandas as pd
import time


def timeit(method):
    def timed(*args, **kw):
        results = {"m": [], "min_sup": [], "min_conf": [], "time": []}
        grid = kw.get('grid', False)
        if kw.get('grid', False):
            for m in grid['m']:
                for min_sup in grid['min_sup']:
                    for min_conf in grid['min_conf']:
                        root = Node()

                        Node.total_records = len(args[0].values)
                        Node.root = root
                        Node.min_conf = min_conf
                        Node.min_sup = min_sup

                        ts = time.time()
                        result = method(*args, root=root, **kw)
                        te = time.time()

                        kw['log_time']['time'].append(int((te-ts)*1000))
                        kw['log_time']['m'].append(m)
                        kw['log_time']["min_sup"].append(min_sup)
                        kw['log_time']["min_conf"].append(min_conf)

                        del root
                        gc.collect()

        return results

    return timed


@timeit
def DIC(data, root, m=2, **kwargs):
    # Initial pass to build Itemsets of size 1
    x = [val for d in data for val in data[d].unique()]
    for i, d in enumerate([val for d in data for val in data[d].unique()]):
        root.add_child((d,), tid=0)

    scan_num = 0
    while root.dashed_children_exist():
        # Pass over the dataset in m-sized chunks.
        for i, end in enumerate(range(m, len(data) + m, m)):
            for j, d in enumerate(data[i * m:end].iterrows()):
                root.increment(m * i + j, sorted(d[1]))
        for executable in Node.to_transition:
            executable()
        for executable in Node.to_finalize:
            executable()
        Node.to_transition = set()
        Node.to_finalize = set()
        scan_num += 1
    print("Scanned D {} times".format(scan_num))
    root.generate_rules()
    print(len(Node.rules), "Rules found.")
    for i, key in enumerate(Node.rules):
        rule = Node.rules[key]
        h = [format_item(item, data) for item in sorted(list(key[0]))]
        t = [format_item(item, data) for item in sorted(list(key[1]))]
        with open('Rules.txt', 'a') as file:
            file.write("{} => {} (Support={:.2f}, Confidence={:.2f})\n"
                       .format(h, t, rule['support'], rule['confidence']))
    return root


def main():

    data = pd.read_csv("Play_Tennis_Data_Set.csv")
    # data = data.drop(columns=['caseid'])
    data['Windy'] = data['Windy'].map({True: 'True', False: 'False'})

    time_data = {"time": [], "m": [], "min_sup": [], "min_conf": []}

    grid = {
        "m": [2],
        "min_sup": [.05],
        "min_conf": [0.2]
    }

    root = DIC(data, grid=grid, log_time=time_data)
    results = pd.DataFrame.from_dict(time_data)
    results.to_csv("DIC_Results.csv", index=False)
    # print(time_data)
    #
    # # root.to_string(None)
    #
    # for i, key in enumerate(Node.rules):
    #     rule = Node.rules[key]
    #     h = [format_item(item, data) for item in sorted(list(key[0]))]
    #     t = [format_item(item, data) for item in sorted(list(key[1]))]
    #     with open('Rules.txt', 'a') as file:
    #         file.write("{} => {} (Support={:.2f}, Confidence={:.2f})\n"
    #                    .format(h, t, rule['support'], rule['confidence']))


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
