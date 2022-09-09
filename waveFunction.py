import random
from pprint import pprint
import time
DIM: int = 8
tiles = {0: ["   ",
             "   ",
             "   "],
         1: [" # ",
             "###",
             "   "],
         2: ["   ",
             "###",
             " # "],
         3: [" # ",
             "## ",
             " # "],
         4: [" # ",
             " ##",
             " # "],
         5: [" # ",
             " # ",
             " # "],
         6: ["   ",
             "###",
             "   "],
         7: [" # ",
             " # ",
             "   "],
         8: ["   ",
             " # ",
             " # "],
         9: ["   ",
             "## ",
             "   "],
         10:["   ",
             " ##",
             "   "]
         }

vOpt = {  # up, down, left, right => [[], [], [], []]
    0: [[0, 1, 6], [0, 2, 6], [0, 3, 5], [0, 4, 5]],
    1: [[2, 3, 4, 5], [0, 2, 6], [1, 2, 4, 6], [1, 2, 3, 6]],
    2: [[0, 1, 6], [1, 3, 4, 5], [1, 2, 4, 6], [1, 2, 3, 6]],
    3: [[2, 3, 4, 5], [1, 3, 4, 5], [1, 2, 4, 6], [0, 4, 5]],
    4: [[2, 3, 4, 5], [1, 3, 4, 5], [0, 3, 5], [1, 2, 4, 6]],
    5: [[2, 3, 4, 5], [1, 3, 4, 5], [0, 3, 5], [0, 4, 5]],
    6: [[0, 1, 6], [0, 2, 6], [1, 2, 4, 6], [1, 2, 3, 6]],
    
    }


def initGrid(grid):
    for i in range(DIM):
        grid.append([0 for i in range(DIM)])


def printGrid(grid):
    for i in range(len(grid)):
        print(grid[i])


def pprintGrid(grid):
    print("|"+"---|"*len(grid[0]))
    for y in grid:
        for image in range(3):
            print(" ", end="")
            for x in y:
                print(tiles[x][image]+" ", end="")
            print("")
        print("|"+"---|"*len(y))


grid = []
initGrid(grid)
newgrid = []
initGrid(newgrid)
collapsedGrid = []
initGrid(collapsedGrid)


def collapse(grid, y, x, value):
    grid[y][x] = value
    collapsedGrid[y][x] = 1


for y in range(DIM):
    for x in range(DIM):
        newgrid[x][y] = random.randint(0, len(tiles.keys())-1)


def randint():
    return random.randint(1, len(tiles.keys())-1)


def randim():
    return random.randint(0, DIM-1)


collapse(grid, randim(), randim(), randint())
print("grid")
printGrid(grid)
print("collapsed")
printGrid(collapsedGrid)


# entropy
def evaluateEntropy(ingrid):
    possibleMoves = []
    entropy = []
    initGrid(possibleMoves)
    initGrid(entropy)
    for y in range(0, len(possibleMoves)):
        for x in range(0, len(possibleMoves[y])):
            adjTiles = [ingrid[y-1][x], 0, ingrid[y][x-1], 0]  # adjacent tiles
            if (y+1) >= len(ingrid):
                adjTiles[1] = ingrid[0][x]
            else:
                adjTiles[1] = ingrid[y+1][x]
            if (x+1) >= len(ingrid[y]):
                adjTiles[3] = ingrid[y][0]
            else:
                adjTiles[3] = ingrid[y][x+1]
            invT = [adjTiles[1], adjTiles[0], adjTiles[3], adjTiles[2]]
            tOpt = [vOpt[invT[i]][i] for i in range(len(invT)) if invT[i] != 0]
            allOpt = [item for subs in tOpt for item in subs]
            newOpt = []
            for a in tOpt:
                for b in a:
                    if allOpt.count(b) == len(tOpt):
                        newOpt.append(b)
            newOpt = list(set(newOpt))
            if len(newOpt) > 0:
                entropy[y][x] = len(newOpt)
            else:
                entropy[y][x] = 5
            if collapsedGrid[y][x] == 1:
                entropy[y][x] = 0
            possibleMoves[y][x] = newOpt
            # print((y, x), grid[y][x], adjT, invT, newoptions)
            # nextStep = {i: nextEntropy.count(i) for i in nextEntropy} # get count of duplicates
    return [entropy, possibleMoves]


def iterateCollapse(ingrid, collapsedGrid, possibleMoves):

    newGrid = []
    for y in range(len(ingrid)):
        for x in range(len(ingrid[y])):
            if collapsedGrid[y][x] != 1:
                newGrid.append([len(possibleMoves[y][x]),
                               possibleMoves[y][x], (y, x)])
            # [2, [0, 4], (0, 0)]
    newGrid.sort()
    newGrid = [newGrid[i] for i in range(len(newGrid)) if newGrid[i][1] != []]

    newGrid = {i[0]: [f for f in newGrid if f[0] == i[0]] for i in newGrid}
    minSel = sorted(newGrid.keys())[0]
    randSel1 = random.randint(0, len(newGrid[minSel])-1)
    randSel2 = random.randint(0, len(newGrid[minSel][randSel1][1])-1)
    # printGrid(newGrid[minSel])
    # print(newGrid[minSel][randSel1][2])
    # print(newGrid[minSel][randSel1][1][randSel2])
    coord = newGrid[minSel][randSel1][2]
    collapse(ingrid, coord[0], coord[1],
             newGrid[minSel][randSel1][1][randSel2])
    # print(newGrid[minselection][0][1][randomselection])
    # print(newGrid, [newGrid.keys()])
    # printGrid(ingrid)
    # printGrid(entropy)
    # printGrid(possibleMoves)


entropy = []
initGrid(entropy)
# printGrid(possibleMoves)
# pprintGrid(grid)
pprintGrid(grid)
while sum([item for subs in collapsedGrid for item in subs]) != DIM**2:
    try:
        try:
            entropy, possibleMoves = evaluateEntropy(grid)
            iterateCollapse(grid, collapsedGrid, possibleMoves)
            print("\n\n\n")
            printGrid(grid)
            print()
            printGrid(collapsedGrid)
            print()
            printGrid(entropy)
            print()
            pprintGrid(grid)
            time.sleep(0.1)
        except KeyboardInterrupt:       
            break
    except:
        initGrid(grid)
entropy, possibleMoves = evaluateEntropy(grid)
printGrid(entropy)
print()
# print(sum([item for subs in collapsedGrid for item in subs]))
# printGrid(entropy)
# pprintGrid(grid)
