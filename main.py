import random
from typing import Optional

import htinter as ht

type Grid = list[list[int]]


def print_grid(grid: Grid) -> None:
    for row in grid:
        print(' '.join(str(num) if num != 0 else '.' for num in row))


def is_valid(grid: Grid, row: int, col: int, num: int) -> bool:
    for i in range(9):
        if grid[row][i] == num or grid[i][col] == num:
            return False

    box_row_start = (row // 3) * 3
    box_col_start = (col // 3) * 3
    for i in range(3):
        for j in range(3):
            if grid[box_row_start + i][box_col_start + j] == num:
                return False

    return True


def solve_sudoku(grid: Grid) -> bool:
    empty = find_empty_location(grid)
    if not empty:
        return True
    row, col = empty

    for num in range(1, 10):
        if is_valid(grid, row, col, num):
            grid[row][col] = num
            if solve_sudoku(grid):
                return True
            grid[row][col] = 0

    return False


def find_empty_location(grid: Grid) -> Optional[tuple[int, int]]:
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                return (i, j)
    return None


def fill_grid(grid: Grid) -> bool:
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                random_nums = list(range(1, 10))
                random.shuffle(random_nums)
                for num in random_nums:
                    if is_valid(grid, i, j, num):
                        grid[i][j] = num
                        if fill_grid(grid):
                            return True
                        grid[i][j] = 0
                return False
    return True


def remove_numbers(grid: Grid, attempts: int) -> None:
    while attempts > 0:
        row = random.randint(0, 8)
        col = random.randint(0, 8)
        while grid[row][col] == 0:
            row = random.randint(0, 8)
            col = random.randint(0, 8)
        grid[row][col] = 0
        attempts -= 1


def generate_sudoku() -> Grid:
    grid = [[0 for _ in range(9)] for _ in range(9)]
    fill_grid(grid)
    remove_numbers(grid, attempts=40)
    return grid


def main() -> None:
    sudoku_grid = generate_sudoku()
    print('Generated Sudoku Puzzle:')
    print_grid(sudoku_grid)

    if solve_sudoku(sudoku_grid):
        print('\nSolved Sudoku Puzzle:')
        print_grid(sudoku_grid)
    else:
        print('No solution exists.')


if __name__ == '__main__':
    main()
