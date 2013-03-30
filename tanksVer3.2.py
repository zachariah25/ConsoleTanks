"""
file: tanksVer3.2
author: Zach Lauzon (zrl3031@rit.edu)
description: console-based tank game. execute to play.
P1 controls: WASD to move, F to fire
P2 controls: OKL; to move, ' to fire

notes: lists that don't change (e.g. walls) changed to sets for O(1) access
disabled buffering of output stream to improve performance
"""

from colorama import init
init() #allows color printing
import os
import sys; sys.stdout = sys.stderr #avoids buffering output
import random
import threading

class Board():
    """
    Data structure that facilitates gameplay.
        size: length of rows/columns <- int
        maxHealth: total health players start with <- int

        p1: player 1's location <- (r,c) tuple
        p1d: player 1's direction  <- int (range 0-3)
        p1h: player 1's health <- int

        <player 2's stuff is obvious>

        b: location of bullet <- (r,c) tuple
        f: locations of fire <- [(r,c) * 9] set of tuples

        barrels: locations of barrels <- [(r,c) * any] set of tuples
        walls: locations of walls <- [(r,c) * any] set of tuples
        portals: locations of portals <- [(r,c) * any] set of tuples
        topLeftMirrors: locations of mirrors <- [(r,c) * any] set of tuples
        topRightMirrors: locations of mirrors <- [(r,c) * any] set of tuples

        curBarrels: locations of live barrels <- [(r,c) * any] set of tuples
        listOfPortals: locations of portals <- [(r,c) * any] list of tuples
        spawns: locations of spawn points <- [(r,c) * any] list of tuples
        (spawns and portals need indexing for randomization, so they're lists)
        self.barrelLimit: limit of barrrel placement (int)

        allOccupiedSpaces: used for printing <- [(r,c) * any] set of tuples
    """
    __slots__ = ('size', 'maxHealth', 'p1', 'p1d', 'p1h', 'p2', 'p2d', 'p2h', \
        'b', 'f', 'barrels', 'curBarrels', 'walls', 'portals', 'topLeftMirrors', 'topRightMirrors', \
        'listOfPortals', 'spawns', 'barrelLimit', 'allOccupiedSpaces')

    def __init__(self, filename):
        """
        Initializes the data structure. 
        """
        if filename == "":
            #Default map
            self.size = 15
            self.maxHealth = 10
            self.barrels = set(((5,5),(5,4),(9,5),(3,1),(3,4)))
            self.walls = set(((3,3),(4,3),(5,3),(3,8),(4,3),(5,7),(8,7),(3,6)))
            self.portals = set(((1,8),(3,7),(6,3),(5,4)))
            self.topLeftMirrors = set(((5,2),(1,2)))
            self.topRightMirrors = set(((4,6),(7,9)))
            self.spawns = []

        else:
            #builtin maps
            if filename == "w" or filename == "W":
                filename = "warzone.txt"
            elif filename == "b" or filename == "B":
                filename = "barricade.txt"
            elif filename == "f" or filename == "F":
                filename = "fortress.txt"
            elif filename == "p" or filename == "P":
                filename = "portals.txt"

            self.size = 15 # overwritten if indicated in map file
            self.maxHealth = 10 # also overwritten
            self.barrels = set()
            self.walls = set()
            self.portals = set()
            self.topLeftMirrors = set()
            self.topRightMirrors = set()
            self.spawns = []
            isMap = False #flag to determine if reading map
            r = 0 #current row in map
            c = 0 #current col in map

            for line in open(filename):
                    
                if isMap:
                    if len(line.split()) != 0:
                        c = 0
                        for char in line:
                            if char == "O":
                                self.barrels.add((r,c))
                            elif char == "#":
                                self.walls.add((r,c))
                            elif char == "?":
                                self.portals.add((r,c))
                            elif char == "/":
                                self.topLeftMirrors.add((r,c))
                            elif char == "\\":
                                self.topRightMirrors.add((r,c))
                            elif char == "S":
                                self.spawns.append((r,c)) #spawns are a list
                            c += 1
                    r += 1

                elif len(line.split()) != 0:
                    if line.split()[0] == "MAP":
                        isMap = True
                    elif line.split()[0] == "SIZE":
                        self.size = int(line.split()[1])
                    elif line.split()[0] == "MAXHEALTH":
                        self.maxHealth = int(line.split()[1])

        #applies to all boards     
        self.p1d = 0
        self.p2d = 0
        self.p1h = self.maxHealth
        self.p2h = self.maxHealth
        self.allOccupiedSpaces = self.barrels | self.walls | self.portals | self.topLeftMirrors | self.topRightMirrors
        self.listOfPortals = list(self.portals)
        self.curBarrels = set()
        self.f = set()
        self.b = (-1,-1)
        self.p1 = (-1,-1)
        self.p2 = (-1,-1)
        self.barrelLimit = 0
        # Above 3 structures are lists because they change during gameplay
        self.reset() # Sets f, b, curBarrels, and players to default

    def __str__(self):
        """
        Returns a printout of the board. Use board.refresh() for gameplay.
        """
        result = "##" + "##" * self.size  + "\n" #top border
        for r in range(self.size):
            result += "#" #left side border
            for c in range(self.size):

                if (r,c) == self.b:
                    result += "\033[1;33m*\033[1;0m"
                elif (r,c) in self.f:
                    result += "\033[1;31m%\033[1;0m"
                    
                elif (r,c) == self.p1:
                    if self.p1d == 0:
                        result += "\033[1;32m^\033[1;0m"
                    elif self.p1d == 1:
                        result += "\033[1;32m<\033[1;0m"
                    elif self.p1d == 2:
                        result += "\033[1;32mV\033[1;0m"
                    elif self.p1d == 3:
                        result += "\033[1;32m>\033[1;0m"

                elif (r,c) == self.p2:
                    if self.p2d == 0:
                        result += "\033[1;36m^\033[1;0m"
                    elif self.p2d == 1:
                        result += "\033[1;36m<\033[1;0m"
                    elif self.p2d == 2:
                        result += "\033[1;36mV\033[1;0m"
                    elif self.p2d == 3:
                        result += "\033[1;36m>\033[1;0m"

                elif (r,c) in self.curBarrels:
                    result += "\033[1;31mO\033[1;0m"

                elif (r,c) in self.allOccupiedSpaces:
                    if (r,c) in self.walls:
                        result += "#"
                    elif (r,c) in self.portals:
                        result += "\033[1;35m?\033[1;0m"
                    elif (r,c) in self.topLeftMirrors:
                        result += "\033[1;35m/\033[1;0m"
                    elif (r,c) in self.topRightMirrors:
                        result += "\033[1;35m\\\033[1;0m"
                    else:
                        result += " " # Barrel has already exploded

                else:
                    result += " "

                result += " " #widens board
            result += "#\n" #right side border
        result += "##" * self.size + "##" #bottom border

        result += "\n\n\033[1;32mPlayer 1: " + "\033[1;31m[]" * self.p1h + \
        "\n\n\033[1;36mPlayer 2: " + "\033[1;31m[]" * self.p2h + "\033[1;0m"

        return result

    def turn(self, char):
        """
        Updates the data structure based on the character used.
        Note: portals are checked with each movement so that one player moving
        does not cause the other player to teleport.

            char -> string of length 1 -> key pressed ('w' moves p1 up, etc.)
        """
        #PLAYER 1 MOVES
        if char == "w":#up
            self.p1d = 0
            newSpace = self.nextSpace(self.p1, self.p1d)
            if not self.isCollision(newSpace):
                self.p1 = newSpace
                if self.isPortal(self.p1):
                    self.p1 = self.teleport(self.p1)
        elif char == "a":#left
            self.p1d = 1
            newSpace = self.nextSpace(self.p1, self.p1d)
            if not self.isCollision(newSpace):
                self.p1 = newSpace
                if self.isPortal(self.p1):
                    self.p1 = self.teleport(self.p1)
        elif char == "s":#down
            self.p1d = 2
            newSpace = self.nextSpace(self.p1, self.p1d)
            if not self.isCollision(newSpace):
                self.p1 = newSpace
                if self.isPortal(self.p1):
                    self.p1 = self.teleport(self.p1)
        elif char == "d":#right
            self.p1d = 3
            newSpace = self.nextSpace(self.p1, self.p1d)
            if not self.isCollision(newSpace):
                self.p1 = newSpace
                if self.isPortal(self.p1):
                    self.p1 = self.teleport(self.p1)

        #PLAYER 2 MOVES
        elif char == "o":#up
            self.p2d = 0
            newSpace = self.nextSpace(self.p2, self.p2d)
            if not self.isCollision(newSpace):
                self.p2 = newSpace
                if self.isPortal(self.p2):
                    self.p2 = self.teleport(self.p2)
        elif char == "k":#left
            self.p2d = 1
            newSpace = self.nextSpace(self.p2, self.p2d)
            if not self.isCollision(newSpace):
                self.p2 = newSpace
                if self.isPortal(self.p2):
                    self.p2 = self.teleport(self.p2)
        elif char == "l":#down
            self.p2d = 2
            newSpace = self.nextSpace(self.p2, self.p2d)
            if not self.isCollision(newSpace):
                self.p2 = newSpace
                if self.isPortal(self.p2):
                    self.p2 = self.teleport(self.p2)
        elif char == ";":#right
            self.p2d = 3
            newSpace = self.nextSpace(self.p2, self.p2d)
            if not self.isCollision(newSpace):
                self.p2 = newSpace
                if self.isPortal(self.p2):
                    self.p2 = self.teleport(self.p2)

        #IF FIRE KEY PRESSED
        elif char == 'f':
            self.shoot(self.p1, self.p1d)
        elif char == "'":
            self.shoot(self.p2, self.p2d)

        #IF BARREL KEY PRESSED
        elif char == 'r':
            self.addBarrel(self.p1)
        elif char == '[':
            self.addBarrel(self.p2)

    def nextSpace(self, start, direction):
        """
        Returns the space that is one step in indicated direction.

            start -> (r,c) tuple -> starting location
            direction -> int -> direction of movement (N-W-S-E) = (0-1-2-3)
        """
        if start != (-1,-1):
            if direction == 0:
                return (start[0] - 1, start[1])
            elif direction == 1:
                return (start[0], start[1] - 1)
            elif direction == 2:
                return (start[0] + 1, start[1])
            elif direction == 3:
                return (start[0], start[1] + 1)
        return start

    def teleport(self, start):
        """
        Returns a portal location that is different from the start location.

            start -> (r,c) tuple -> location of starting portal
        """
        result = start
        if len(self.portals) > 1:
            while result == start:
                result = self.listOfPortals[int(random.random() \
                                            * len(self.portals))]
        return result

    def shoot(self, start, direction):
        """
        Shoots a bullet. If it hits a wall or the edge of the board, it stops.
        It if hits a barrel, the barrel explodes and the bullet stops.
        If it hits a player, the player gets hit and the bullet stops.

            start -> (r,c) tuple -> location of bullet's start point
            direction -> int -> direction of movement (N-E-W-S) = (0-1-2-3)
        """
        self.b = start
        timeToPrint = True

        while not self.isCollision(self.b):
            newSpace = self.nextSpace(self.b, direction)

            if not self.isCollision(self.b):
                self.b = newSpace

                if timeToPrint: #print half the time to lower lag
                    self.refresh()
                timeToPrint = not timeToPrint

                if self.isBarrel(self.b):
                    self.explode(self.b)
                    break

                if self.isPlayer1(self.b) or self.isPlayer2(self.b):
                    if self.isPlayer1(self.b) and self.isPlayer2(self.b):
                        self.hitBothPlayers()
                        break
                    if self.isPlayer1(self.b):
                        self.hit(1)
                        break
                    else:
                        self.isPlayer2(self.b)
                        self.hit(2)
                        break

                if self.isPortal(self.b): #teleporting bullets
                    self.b = self.teleport(self.b)

                if self.isMirror(self.b):
                    direction = self.reflect(direction, self.isTopLeftMirror(self.b))

        self.resetBullet()

    def reflect(self, direction, mirrorType):
        """
        Given a direction and mirrorType, produces a new direction.

            direction (int): current direction of movement (N-W-S-E) = (0-1-2-3)
            mirrorType (boolean): is this a topLeftMirror? (false = topRight)
        """
        if direction == 0:
            if mirrorType:
                return 3
            else:
                return 1
        elif direction == 1:
            if mirrorType:
                return 2
            else:
                return 0
        elif direction == 2:
            if mirrorType:
                return 1
            else:
                return 3
        elif direction == 3:
            if mirrorType:
                return 0
            else:
                return 2

    def explode(self, start):
        """
        Explodes a barrel. Flames behave in the same manner that bullets do,
        except there's 9 of them, spreading in a cross of length two.
        Note: queue structure avoid issues with recursion. 

            start -> (r,c) tuple -> location of original barrel/explosion
        """

        self.curBarrels.remove(start)
        explosions = list([start])

        while explosions != []:

            cur = explosions.pop(0)
            self.flameOut(cur)

            for f in self.f:
                if self.isBarrel(f):
                    explosions.append(f)
                    self.curBarrels.remove(f)

                if self.isPlayer1(f) or self.isPlayer2(f):
                    if self.isPlayer1(f) and self.isPlayer2(f):
                        self.hitBothPlayers()
                        explosions = []
                        break
                    elif self.isPlayer1(f):
                        self.hit(1)
                        explosions = []
                        break
                    else:
                        self.hit(2)
                        explosions = []
                        break

            self.refresh()
            self.resetFlames()
                    
    def flameOut(self, start):
        """
        Moves the position of the flames (for use in explode).

            start -> (r,c) tuple -> location of original barrel/explosion
        """
        self.f = [None] * 9

        self.f[0] = start
        self.f[1] = self.nextSpace(start, 0)
        self.f[2] = self.nextSpace(start, 1)
        self.f[3] = self.nextSpace(start, 2)
        self.f[4] = self.nextSpace(start, 3)
        
        for i in range(5):
            if self.isCollision(self.f[i]):
                self.f[i] = (-1,-1)

        self.f[5] = self.nextSpace(self.f[1], 0)
        self.f[6] = self.nextSpace(self.f[2], 1)
        self.f[7] = self.nextSpace(self.f[3], 2)
        self.f[8] = self.nextSpace(self.f[4], 3)
        
        for i in range(5,9):
            if self.isCollision(self.f[i]):
                self.f[i] = (-1,-1)

        self.f = set(self.f)
        
    def resetFlames(self):
        """
        Resets all flames to their default position.
        """
        self.f = [None] * 9
        for i in range(9):
            self.f[i] = (-1,-1)

    def resetBullet(self):
        """
        Resets the bullet to its default position.
        """
        self.b = [-1,-1]

    def resetPlayers(self):
        """
        Resets players to spawn points. If spawns are invalid, places randomly.
        """
        if len(self.spawns) >= 2:
            self.p1 = self.spawns[int(random.random() * len(self.spawns))]
            self.p2 = self.spawns[int(random.random() * len(self.spawns))]
            while self.p1 == self.p2:
                self.p2 = self.spawns[int(random.random() * len(self.spawns))]

        else: #Places in two random unoccupied spaces
            while True:
                self.p1 = (int(random.random() * self.size), \
                int(random.random() * self.size))
                self.p2 = (int(random.random() * self.size), \
                int(random.random() * self.size))
                
                if self.p1 not in self.allOccupiedSpaces and self.p2 not in \
                self.allOccupiedSpaces and not self.isPlayer1(self.p2):
                    break

    def resetBarrels(self):
        """
        Resets barrels to their original positions.
        """
        self.curBarrels = set(self.barrels)
        self.barrelLimit = 5

    def addBarrel(self, space):
        """
        Adds a barrel to a board space.
        """
        if self.barrelLimit > 0:
            if space not in self.allOccupiedSpaces:
                self.curBarrels.add(space)
                self.barrelLimit -= 1
        
    def isCollision(self, space):
        """
        Returns true if a space is not inside board and doesn't hit a wall.

            space -> (r,c) tuple -> location to investigate
        """
        return not (space[0] >= 0 and space[1] >= 0 and space[0] < self.size \
            and space[1] < self.size and not space in self.walls)

    def isPortal(self, space):
        """
        Returns true if a space is a portal.

            space -> (r,c) tuple -> location to investigate
        """
        return space in self.portals

    def isMirror(self, space):
        """
        Returns true if a space is a mirror.

            space -> (r,c) tuple -> location to investigate
        """
        return space in self.topLeftMirrors or space in self.topRightMirrors

    def isTopLeftMirror(self, space):
        """
        Returns true if a space is a topLeftMirror.

            space -> (r,c) tuple -> location to investigate
        """
        return space in self.topLeftMirrors

    def isBarrel(self, space):
        """
        Returns true if a space is an active barrel.

            space -> (r,c) tuple -> location to investigate
        """
        return space in self.curBarrels

    def isPlayer1(self, space):
        """
        Returns true if a space has player 1.

            space -> (r,c) tuple -> location to investigate
        """
        return space == self.p1

    def isPlayer2(self, space):
        """
        Returns true if a space has player 2.

            space -> (r,c) tuple -> location to investigate
        """
        return space == self.p2

    def gameOver(self):
        """
        Returns true if a player has won.
        """
        return self.p1h <= 0 or self.p2h <= 0

    def winner(self):
        """
        Returns the number of the player with more health
        """
        if self.p1h > self.p2h:
            return 1
        elif self.p1h < self.p2h:
            return 2
        else:
            return 0

    def hit(self, player):
        """
        Pauses the game to inform the players, updates health and resets board.

            player -> int -> number of player who was hit (1 or 2)
        """
        self.refresh()

        if player == 1:
            os.system("title " + "Tanks --- Player 1 sucks!")
            input("\nPlayer one hit!")
            self.p1h -= 1
        elif player == 2:
            os.system("title " + "Tanks --- Player 2 sucks!")
            input("\nPlayer two hit!")
            self.p2h -= 1

        self.reset()

    def hitBothPlayers(self):
        """
        Pauses the game to inform the players, updates health and resets board.
        """
        self.refresh()

        os.system("title " + "Tanks --- Both players suck!")
        input("\nBoth players hit!")
        self.p1h -= 1
        self.p2h -= 1
        self.reset()

    def reset(self):
        """
        Resets all aspect of the board.
        """
        self.resetPlayers()
        self.resetBullet()
        self.resetFlames()
        self.resetBarrels()

    def refresh(self):
        """
        Refreshes the game board. Call this after any movement.
        """
        os.system('cls')
        print(self)

class _Getch:
    """
    Gets a single character from standard input.  Does not echo to the
    screen.
    """
    def __init__(self):
        self.impl = _GetchWindows()

    def __call__(self): return self.impl()

class _GetchWindows:
    def __init__(self):
        import msvcrt

    def __call__(self):
        import msvcrt
        return msvcrt.getch()

class InputThread(threading.Thread):
    """
    Thread to receive input.
    Limits each player's input to prevent lag, and "filters" input, 
    preventing invalid keystrokes from causing refreshes.
    """
    __slots__ = ("get", "p1moves", "p2moves", "turn")

    def run(self):
        self.get = _Getch()
        self.p1moves = []
        self.p2moves = []
        self.turn = False
        if random.randrange(0,2) == 1: #picks initial turn randomly
            self.turn = True

        while True:
            char = str(self.get())[-2] #get char from user
            if char in "wasdfr": #p1 moveset
                if len(self.p1moves) < 2: #limits to 2 moves at a time
                    self.p1moves.append(char)
            elif char in "okl;'[": #p2 moveset
                if len(self.p2moves) < 3: #limits to 2 moves at a time
                    self.p2moves.append(char)

    def getMove(self):
        """
        Returns the next move. Turn variable alternates to promote fairness.
        """
        if self.turn: #checks p1 first if turn = true
            if self.p1moves != []:
                self.turn = False
                return self.p1moves.pop(0)
            elif self.p2moves != []:
                return self.p2moves.pop(0)
        else:
            if self.p2moves != []:
                self.turn = True
                return self.p2moves.pop(0)
            elif self.p1moves != []:
                return self.p1moves.pop(0)
        return None

def splash():
    print("Welcome to tanks! Open a map file?\n")
    print("\033[1;33mF for <fortress>")
    print("\033[1;32mB for <barricade>")
    print("\033[1;35mP for <portals>")
    print("\033[1;31mW for <warzone>\033[1;0m")
    print("\nOr, enter a custom map file name: (leave blank for default)\n")

def main():
    """
    Call this to run the game.
    """
    os.system("title " + "Tanks")
    splash()

    filename = input()
    board = Board(filename)

    board.refresh()

    charGetter = InputThread()
    charGetter.daemon = True 
    charGetter.start()

    keepGoing = True
    while keepGoing:

        move = charGetter.getMove()

        if move != None:
            board.turn(move)
            board.refresh()

            if board.gameOver():
                keepGoing = False

    if board.winner() == 1:
        os.system("title " + "Player 1 wins!")
        print("\nPlayer 1 wins!")
    elif board.winner() == 2:
        os.system("title " + "Player 2 wins!")
        print("\nPlayer 2 wins!")
    else:
        os.system("title " + "Nobody wins!")
        print("\nNobody wins!")

    input("\nEnter to close...")

main()
