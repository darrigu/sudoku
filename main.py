import copy
import random
from typing import Any, Optional

import htinter as ht


type Grid = list[list[int]]


def is_valid(grid: Grid, row: int, col: int, num: int) -> bool:
    if any(grid[row][i] == num or grid[i][col] == num for i in range(9)):
        return False

    box_row, box_col = (row // 3) * 3, (col // 3) * 3
    return all(
        grid[r][c] != num
        for r in range(box_row, box_row + 3)
        for c in range(box_col, box_col + 3)
    )


def find_empty_location(grid: Grid) -> Optional[tuple[int, int]]:
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                return i, j
    return None


def solve_sudoku(grid: Grid) -> bool:
    loc = find_empty_location(grid)
    if not loc:
        return True

    row, col = loc
    for num in range(1, 10):
        if is_valid(grid, row, col, num):
            grid[row][col] = num
            if solve_sudoku(grid):
                return True
            grid[row][col] = 0
    return False


def fill_grid(grid: Grid) -> bool:
    for i in range(9):
        for j in range(9):
            if grid[i][j] == 0:
                nums = list(range(1, 10))
                random.shuffle(nums)
                for num in nums:
                    if is_valid(grid, i, j, num):
                        grid[i][j] = num
                        if fill_grid(grid):
                            return True
                        grid[i][j] = 0
                return False
    return True


def remove_numbers(grid: Grid, attempts: int) -> None:
    while attempts > 0:
        row, col = random.randint(0, 8), random.randint(0, 8)
        while grid[row][col] == 0:
            row, col = random.randint(0, 8), random.randint(0, 8)
        grid[row][col] = 0
        attempts -= 1


def generate_sudoku() -> Grid:
    grid = [[0] * 9 for _ in range(9)]
    fill_grid(grid)
    remove_numbers(grid, attempts=40)
    return grid


def is_valid_row(grid: Grid, row: int) -> bool:
    seen = set()
    for num in grid[row]:
        if num == 0:
            continue
        if num in seen:
            return False
        seen.add(num)
    return True


def is_valid_col(grid: Grid, col: int) -> bool:
    seen = set()
    for i in range(9):
        num = grid[i][col]
        if num == 0:
            continue
        if num in seen:
            return False
        seen.add(num)
    return True


def is_valid_subgrid(grid: Grid, start_row: int, start_col: int) -> bool:
    seen = set()
    for r in range(start_row, start_row + 3):
        for c in range(start_col, start_col + 3):
            num = grid[r][c]
            if num == 0:
                continue
            if num in seen:
                return False
            seen.add(num)
    return True


def generate_grid_dom(grid: Grid) -> None:
    html = ('<colgroup>' + '<col>' * 3 + '</colgroup>') * 3
    for y, row in enumerate(grid):
        if y % 3 == 0:
            html += '<tbody>'
        html += '<tr>'
        for x, num in enumerate(row):
            cls = 'cell disabled' if num != 0 else 'cell'
            val = str(num) if num != 0 else ''
            html += f'<td class="{cls}" y="{y}" x="{x}">{val}</td>'
        html += '</tr>'
        if y % 3 == 2:
            html += '</tbody>'
    ht.contenu('#grid', html)


sudoku_grid: Grid
solved_grid: Grid
clicked_cell: Optional[dict[str, str]] = None


def cell_click(c: Any, p: Any) -> None:
    global clicked_cell
    if clicked_cell:
        prev_selector = f'.cell[x="{clicked_cell["x"]}"][y="{clicked_cell["y"]}"]'
        ht.classes(prev_selector, 'cell')
    clicked_cell = p
    new_selector = f'.cell[x="{p["x"]}"][y="{p["y"]}"]'
    ht.classes(new_selector, 'cell active')


def change_cell_value(c: Any, p: Any) -> None:
    global sudoku_grid, clicked_cell
    if not clicked_cell:
        return
    x, y = int(clicked_cell['x']), int(clicked_cell['y'])
    cell_sel = f'.cell[x="{x}"][y="{y}"]'

    if p['touche'].isdigit():
        sudoku_grid[y][x] = int(p['touche'])
        ht.contenu(cell_sel, p['touche'])
    elif p['touche'] == 'Backspace':
        sudoku_grid[y][x] = 0
        ht.contenu(cell_sel, '')

    ht.classes(cell_sel, 'cell')
    clicked_cell = None

    if not find_empty_location(sudoku_grid):
        ht.classes('.validate', 'validate')


def validate_click(c: Any, p: Any) -> None:
    print(sudoku_grid == solved_grid)


def main(c: Any, p: Any) -> None:
    global sudoku_grid, solved_grid
    sudoku_grid = generate_sudoku()

    while True:
        solved_grid = copy.deepcopy(sudoku_grid)
        if solve_sudoku(solved_grid):
            break

    print(solved_grid)

    generate_grid_dom(sudoku_grid)
    ht.capture_clic('.cell', fnct=cell_click)
    ht.écouter_touches(fnct=change_cell_value)
    ht.capture_clic('.validate', fnct=validate_click)


if __name__ == '__main__':
    ht.init_page(main)
    ht.servir()
