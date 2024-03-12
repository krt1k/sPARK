floors = ['A', 'B', 'C']
count = [i for i in range(1, 11)]

for floor in floors:
    for i in count:
        print(f"{floor}{i}")