from Node import Node
import pandas as pd


def main(m=2):

    data = pd.read_csv("Play_Tennis_Data_Set.csv")
    data['Windy'] = data['Windy'].map({True: 'True', False: 'False'})

    data1 = list([val for d in data for val in data[d].unique()])

    root = Node()

    Node.total_records = len(data.values)
    Node.root = root

    # Initial pass to build Itemsets of size 1
    for i, d in enumerate(data1):
        root.add_child((d,))

    scan_num = 0
    while root.dashed_children_exist():
        # Pass over the dataset in m-sized chunks.
        for i, end in enumerate(range(m, len(data)+m, m)):
            for j, d in enumerate(data[i*m:end].iterrows()):
                root.increment(m*i+j, scan_num, d[1])
        scan_num += 1

    root.to_string(None)

    root.generate_rules()


if __name__ == '__main__':
    main()
