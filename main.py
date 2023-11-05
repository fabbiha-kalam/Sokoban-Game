from typing import *
from enum import Enum
from copy import deepcopy
import sys
import pygame


class Tile(Enum):
    EMPTY = 0
    PLAYER = 1
    WALL = 2
    BOX = 3

    def name(self):
        match self:
            case Tile.EMPTY:
                return '.'
            case Tile.PLAYER:
                return 'p'
            case Tile.WALL:
                return '#'
            case Tile.BOX:
                return 'x'
            case _:
                raise Exception("Invalid tile")


def parse_tile(c):
    match c:
        case '.':
            return Tile.EMPTY
        case 'p':
            return Tile.PLAYER
        case '#':
            return Tile.WALL
        case 'x':
            return Tile.BOX
        case _:
            raise Exception("Invalid tile character: " + c)


class BackgroundTile(Enum):
    EMPTY = 0
    TARGET = 1

    def name(self):
        match self:
            case BackgroundTile.EMPTY:
                return '.'
            case BackgroundTile.TARGET:
                return 'o'
            case _:
                raise Exception("Invalid background tile")


def parse_background_tile(c):
    match c:
        case '.':
            return BackgroundTile.EMPTY
        case 'o':
            return BackgroundTile.TARGET
        case _:
            raise Exception("Invalid background tile character: " + c)


class Vector2:
    x: int
    y: int

    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    def access(self, a):
        return a[self.x][self.y]

    def set(self, a, val):
        a[self.x][self.y] = val

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)


def zip2(xs, ys):
    return map(zip, xs, ys)


class State:
    length: int
    width: int
    tiles: List[List[Tile]]
    background: List[List[BackgroundTile]]

    def __init__(self, tiles: List[List[Tile]], background: List[List[BackgroundTile]]):
        self.tiles = tiles
        self.background = background
        self.length = len(tiles)
        self.width = len(tiles[0])

    def move_player(self, player_pos: Vector2, direction: Vector2) -> bool:
        target = player_pos + direction
        if not self.is_inbounds(target):
            return False
        if target.access(self.tiles) == Tile.WALL:
            return False
        if target.access(self.tiles) == Tile.BOX:
            if not self.move_box(target, direction):
                return False
        player_pos.set(self.tiles, Tile.EMPTY)
        target.set(self.tiles, Tile.PLAYER)
        return True

    def move_box(self, box_pos: Vector2, direction: Vector2) -> bool:
        target = box_pos + direction
        if not self.is_inbounds(target):
            return False
        if target.access(self.tiles) == Tile.WALL:
            return False
        if target.access(self.tiles) == Tile.BOX:
            if not CAN_MULTIPUSH or not self.move_box(target, direction):
                return False
        box_pos.set(self.tiles, Tile.EMPTY)
        target.set(self.tiles, Tile.BOX)
        return True

    def win(self) -> bool:
        for i in range(self.length):
            for j in range(self.width):
                if self.tiles[i][j] == Tile.BOX and self.background[i][j] != BackgroundTile.TARGET:
                    return False
        return True

    def is_inbounds(self, p: Vector2) -> bool:
        return 0 <= p.x < self.length and 0 <= p.y < self.width

    def positions(self) -> Iterable[Vector2]:
        for i in range(self.length):
            for j in range(self.width):
                yield Vector2(i, j)

    @staticmethod
    def print_tile(tile: Tile, background_tile: BackgroundTile) -> str:
        if tile == Tile.EMPTY:
            return background_tile.name()
        return tile.name()

    def __str__(self) -> str:
        return "\n".join(map(lambda row: "".join(map(lambda xs: State.print_tile(*xs), row)), zip2(self.tiles, self.background)))


UP = Vector2(-1, 0)
DOWN = Vector2(1, 0)
LEFT = Vector2(0, -1)
RIGHT = Vector2(0, 1)

CAN_MULTIPUSH = False


class Game:
    state: List[State]

    def __init__(self, initial_state: State):
        self.state = [initial_state]

    def move(self, direction: Vector2) -> bool:
        state_copy = deepcopy(self.state[-1])
        for p in state_copy.positions():
            if p.access(state_copy.tiles) == Tile.PLAYER:
                if state_copy.move_player(p, direction):
                    self.state.append(state_copy)
                    return True
        return False

    def undo(self) -> bool:
        if len(self.state) > 1:
            self.state.pop()
            return True
        return False


class Renderer:
    cell_size: int = 80

    groundImg = pygame.image.load("assets/ground.png")
    crateImg = pygame.image.load("assets/crate.png")
    playerImg = pygame.image.load("assets/player.png")
    wallImg = pygame.image.load("assets/wall.png")
    targetImg = pygame.image.load("assets/target.png")
    solvedImg = pygame.image.load("assets/solved_crate.png")

    def __init__(self, state: State):
        pygame.init()
        self.screen_y = Renderer.cell_size * state.length
        self.screen_x = Renderer.cell_size * state.width
        self.display = pygame.display.set_mode((self.screen_x, self.screen_y))
        pygame.display.set_caption("Sokoban Game")

    def update_state(self, state: State):
        self.display.fill((50, 50, 50))

        for p in state.positions():
            py, px = Renderer.cell_size * p.x, Renderer.cell_size * p.y
            if p.access(state.tiles) == Tile.WALL:
                self.display.blit(Renderer.wallImg, (px, py))
            elif p.access(state.tiles) == Tile.EMPTY:
                self.display.blit(Renderer.groundImg, (px, py))
                if p.access(state.background) == BackgroundTile.TARGET:
                    self.display.blit(Renderer.targetImg, (px, py))
            elif p.access(state.tiles) == Tile.BOX:
                if p.access(state.background) == BackgroundTile.EMPTY:
                    self.display.blit(Renderer.crateImg, (px, py))
                if p.access(state.background) == BackgroundTile.TARGET:
                    self.display.blit(Renderer.solvedImg, (px, py))
            elif p.access(state.tiles) == Tile.PLAYER:
                self.display.blit(Renderer.playerImg, (px, py))

        pygame.display.update()

    def close(self):
        pygame.quit()


def parse_level(level_str) -> Optional[State]:
    try:
        lines = level_str.splitlines()
        length, width = map(int, lines[0].split())
        tiles = map(lambda ln: list(map(parse_tile, ln)), lines[1:length+1])
        background_tiles = map(lambda ln: list(map(parse_background_tile, ln)), lines[length+1:(length*2)+1])
        return State(list(tiles), list(background_tiles))
    except Exception as e:
        print(e)
        return None


if __name__ == "__main__":
    # Choose a level number from the command line
    args = sys.argv[1:]
    level_no = int(args[0]) if len(args) >= 1 else 1

    # Load an initial state of a level
    try:
        with open(f"levels/{level_no}.txt") as f:
            level_str = f.read()
    except:
        print("The requested level doesn't exist!")
        print("Playing level 0 as default")
        with open("levels/0.txt") as f:
            level_str = f.read()

    level = parse_level(level_str)
    if level is None:
        print("Invalid level")
        exit(1)
    game = Game(level)

    # Renderer
    renderer = Renderer(game.state[-1])
    renderer.update_state(game.state[-1])

    # While the game is not over, read events
    while not game.state[-1].win():
        for event in pygame.event.get():
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_UP:
                    game.move(UP)
                elif event.key == pygame.K_DOWN:
                    game.move(DOWN)
                elif event.key == pygame.K_LEFT:
                    game.move(LEFT)
                elif event.key == pygame.K_RIGHT:
                    game.move(RIGHT)
                elif event.key == pygame.K_BACKSPACE:
                    game.undo()

                renderer.update_state(game.state[-1])

            elif event.type == pygame.QUIT:
                renderer.close()
                quit()

    print("You win! :D")
    renderer.close()