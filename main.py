from Node import Node
import pandas as pd


def main():

    data = pd.read_csv("Play_Tennis_Data_Set.csv")
    data['Windy'] = data['Windy'].map({True: 'True', False: 'False'})

    data1 = list([val for d in data for val in data[d].unique()])

    data2 = data.values

    root = Node()

    for d in data1:
        root.add_child((d,), d)

    for d in data2:
        root.increment(d)

    root.to_string(None)

if __name__ == '__main__':
    main()