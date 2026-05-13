#!/usr/bin/env python3
# slitherlink.py: Template implementation for the Artificial Intelligence 2025/2026 project.
# Update the classes and functions in this file according to the assignment instructions.
# In addition to the suggested classes and functions, you may add others you find relevant.

# Group 62:
# 113396 Leonor Costa Guedes
# 113402 Manuel Francisco Santos Ramos Soares

import sys
from sys import stdin

import utils
from utils import *

from search import (
    Problem,
    Node,
    astar_search,
    breadth_first_tree_search,
    depth_first_tree_search,
    greedy_search,
    recursive_best_first_search,
)

UNKNOWN = 0
ACTIVE = 1
FORBIDDEN = 2


class SlytherlinkState:
    state_id = 0

    def __init__(self, board):
        self.board = board
        self.id = SlytherlinkState.state_id
        SlytherlinkState.state_id += 1

    def __lt__(self, other):
        return self.id < other.id

    def __eq__(self, other):
        return isinstance(other, SlytherlinkState) and self.board.signature() == other.board.signature()

    def __hash__(self):
        return hash(self.board.signature())


class Board:
    """Internal representation of a Slitherlink board."""

    def __init__(self, hints, h_states=None, v_states=None):
        self.hints = [row[:] for row in hints]
        self.rows = len(self.hints)
        self.cols = len(self.hints[0]) if self.rows else 0
        self.h_states = h_states if h_states is not None else [[UNKNOWN] * self.cols for _ in range(self.rows + 1)]
        self.v_states = v_states if v_states is not None else [[UNKNOWN] * (self.cols + 1) for _ in range(self.rows)]
        self.sync_views()

    def copy(self):
        return Board(
            self.hints,
            [row[:] for row in self.h_states],
            [row[:] for row in self.v_states],
        )

    def signature(self):
        return tuple(tuple(row) for row in self.h_states), tuple(tuple(row) for row in self.v_states)

    def sync_views(self):
        self.horizontal_walls = [[state == ACTIVE for state in row] for row in self.h_states]
        self.vertical_walls = [[state == ACTIVE for state in row] for row in self.v_states]

    def edge_state(self, edge):
        kind, row, column = edge
        if kind == 'h':
            return self.h_states[row][column]
        return self.v_states[row][column]

    def set_edge_state(self, edge, value):
        kind, row, column = edge
        if kind == 'h':
            current = self.h_states[row][column]
            if current not in (UNKNOWN, value):
                return False
            self.h_states[row][column] = value
        else:
            current = self.v_states[row][column]
            if current not in (UNKNOWN, value):
                return False
            self.v_states[row][column] = value
        return True

    def get_cell_edges(self, row: int, column: int) -> list:
        """Return the four edges of the given cell."""
        return [
            ('h', row, column),
            ('v', row, column + 1),
            ('h', row + 1, column),
            ('v', row, column),
        ]

    def get_active_edges(self, row: int, column: int) -> int:
        """Return the number of active edges in a cell."""
        return sum(self.edge_state(edge) == ACTIVE for edge in self.get_cell_edges(row, column))

    def edge_vertices(self, edge):
        kind, row, column = edge
        if kind == 'h':
            return (row, column), (row, column + 1)
        return (row, column), (row + 1, column)

    @staticmethod
    def parse_instance():
        """Read a board from standard input and return a Board instance."""
        grid = []
        for line in stdin:
            row = line.strip().split()
            if not row:
                continue
            grid.append([int(token) if token.isdigit() else -1 for token in row])
        if not grid:
            raise ValueError("Empty instance.")
        row_length = len(grid[0])
        if any(len(row) != row_length for row in grid):
            raise ValueError("Inconsistent row lengths in the input instance.")
        return Board(grid)

    def _vertex_edges(self, row, column):
        edges = []
        if row > 0:
            edges.append(('h', row - 1, column))
        if row < self.rows:
            edges.append(('h', row, column))
        if column > 0:
            edges.append(('v', row, column - 1))
        if column < self.cols:
            edges.append(('v', row, column))
        return edges

    def unknown_edge_count(self):
        return sum(state == UNKNOWN for row in self.h_states for state in row) + sum(
            state == UNKNOWN for row in self.v_states for state in row
        )


class Slytherlink(Problem):
    def __init__(self, board: Board, gui=None):
        """Initialize the problem with its initial state."""
        self.gui = gui
        initial_board = board.copy()
        
        # Garante que o estado inicial está totalmente propagado
        self._propagate(initial_board)
        initial_board.sync_views()
        
        self.initial = SlytherlinkState(initial_board)
        super().__init__(self.initial)

    def _cell_state(self, board, row, column):
        hint = board.hints[row][column]
        edges = board.get_cell_edges(row, column)
        states = [board.edge_state(edge) for edge in edges]
        active = states.count(ACTIVE)
        unknown_edges = [edge for edge, state in zip(edges, states) if state == UNKNOWN]
        return hint, active, unknown_edges

    def _vertex_state(self, board, row, column):
        edges = board._vertex_edges(row, column)
        states = [board.edge_state(edge) for edge in edges]
        active = states.count(ACTIVE)
        unknown_edges = [edge for edge, state in zip(edges, states) if state == UNKNOWN]
        return active, unknown_edges

    def _set_and_track(self, board, edge, value):
        if board.edge_state(edge) == value:
            return True, False
        if board.edge_state(edge) not in (UNKNOWN, value):
            return False, False
        if not board.set_edge_state(edge, value):
            return False, False
        return True, True

    def _propagate(self, board):
        while True:
            changed = False

            for row in range(board.rows):
                for column in range(board.cols):
                    hint, active, unknown_edges = self._cell_state(board, row, column)
                    if hint < 0:
                        continue
                    if active > hint or active + len(unknown_edges) < hint:
                        return False
                    if active == hint:
                        for edge in unknown_edges:
                            ok, edge_changed = self._set_and_track(board, edge, FORBIDDEN)
                            if not ok: return False
                            changed = changed or edge_changed
                    elif active + len(unknown_edges) == hint:
                        for edge in unknown_edges:
                            ok, edge_changed = self._set_and_track(board, edge, ACTIVE)
                            if not ok: return False
                            changed = changed or edge_changed

            for row in range(board.rows + 1):
                for column in range(board.cols + 1):
                    active, unknown_edges = self._vertex_state(board, row, column)
                    if active > 2:
                        return False
                    if active == 1 and len(unknown_edges) == 0:
                        return False
                    if active == 0 and len(unknown_edges) == 1:
                        return False
                    if active == 2:
                        for edge in unknown_edges:
                            ok, edge_changed = self._set_and_track(board, edge, FORBIDDEN)
                            if not ok: return False
                            changed = changed or edge_changed
                    elif active == 1 and len(unknown_edges) == 1:
                        ok, edge_changed = self._set_and_track(board, unknown_edges[0], ACTIVE)
                        if not ok: return False
                        changed = changed or edge_changed
                    elif active == 0 and len(unknown_edges) == 2:
                        for edge in unknown_edges:
                            ok, edge_changed = self._set_and_track(board, edge, ACTIVE)
                            if not ok: return False
                            changed = changed or edge_changed

            board.sync_views()
            if self._has_closed_cycle(board):
                return False

            if not changed:
                return True

    def _has_closed_cycle(self, board):
        active_edges = []
        for r in range(board.rows + 1):
            for c in range(board.cols):
                if board.h_states[r][c] == ACTIVE: active_edges.append(('h', r, c))
        for r in range(board.rows):
            for c in range(board.cols + 1):
                if board.v_states[r][c] == ACTIVE: active_edges.append(('v', r, c))

        if not active_edges: return False

        adjacency = {}
        for edge in active_edges:
            a, b = board.edge_vertices(edge)
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)

        visited = set()
        components = []
        for start in adjacency:
            if start in visited: continue
            comp = set()
            stack = [start]
            while stack:
                curr = stack.pop()
                if curr in comp: continue
                comp.add(curr)
                visited.add(curr)
                for n in adjacency.get(curr, []):
                    if n not in comp: stack.append(n)
            components.append(comp)

        # Interseções inválidas (vértices com > 2 arestas ativas)
        for v, neighbors in adjacency.items():
            if len(neighbors) > 2:
                return True

        # Verifica componentes cíclicos
        for comp in components:
            is_closed = all(len(adjacency[v]) == 2 for v in comp)
            if is_closed:
                # O ciclo fechou. É este o ciclo final?
                if len(active_edges) > len(comp): 
                    return True # Não, tem pedaços ativos a mais
                
                # Valida se ainda existem hints por cumprir
                for r in range(board.rows):
                    for c in range(board.cols):
                        hint = board.hints[r][c]
                        if hint > 0 and board.get_active_edges(r, c) < hint:
                            return True
                
                # Se não há mais arestas ativas nem obrigações, o puzzle está resolvido!
                # Marca o restante do tabuleiro como FORBIDDEN.
                for r in range(board.rows + 1):
                    for c in range(board.cols):
                        if board.h_states[r][c] == UNKNOWN:
                            board.h_states[r][c] = FORBIDDEN
                for r in range(board.rows):
                    for c in range(board.cols + 1):
                        if board.v_states[r][c] == UNKNOWN:
                            board.v_states[r][c] = FORBIDDEN
                
                board.sync_views()
                return False # Não é um ciclo prematuro, é a solução final.
        return False

    def _select_edge(self, board):
        best_edge = None
        best_score = -1

        for row in range(board.rows + 1):
            for column in range(board.cols):
                edge = ('h', row, column)
                if board.edge_state(edge) != UNKNOWN: continue
                score = 0
                if row > 0 and board.hints[row - 1][column] >= 0: score += 1
                if row < board.rows and board.hints[row][column] >= 0: score += 1
                if score > best_score:
                    best_score = score
                    best_edge = edge

        for row in range(board.rows):
            for column in range(board.cols + 1):
                edge = ('v', row, column)
                if board.edge_state(edge) != UNKNOWN: continue
                score = 0
                if column > 0 and board.hints[row][column - 1] >= 0: score += 1
                if column < board.cols and board.hints[row][column] >= 0: score += 1
                if score > best_score:
                    best_score = score
                    best_edge = edge

        return best_edge

    def actions(self, state: SlytherlinkState):
        """Return actions that can be executed from the given state."""
        board = state.board
        edge = self._select_edge(board)
        if edge is None: return []

        valid_actions = []
        for value in [ACTIVE, FORBIDDEN]:
            probe = board.copy()
            if probe.set_edge_state(edge, value):
                if self._propagate(probe):
                    valid_actions.append((edge[0], edge[1], edge[2], value))
        return valid_actions

    def result(self, state: SlytherlinkState, action):
        """Return the state resulting from applying an action to a state."""
        kind, row, column, value = action
        board = state.board.copy()
        
        # Estas chamadas já foram pré-validadas em actions() e não darão erro
        board.set_edge_state((kind, row, column), value)
        self._propagate(board)
        board.sync_views()
        
        next_state = SlytherlinkState(board)
        if self.gui is not None:
            try:
                self.gui.update_from_state(next_state.board)
            except Exception:
                pass
        return next_state

    def goal_test(self, state: SlytherlinkState):
        """Return True if and only if the given state is a goal state."""
        board = state.board
        if board.unknown_edge_count() != 0: return False

        for row in range(board.rows):
            for column in range(board.cols):
                hint = board.hints[row][column]
                if hint < 0: continue
                if board.get_active_edges(row, column) != hint: return False

        for row in range(board.rows + 1):
            for column in range(board.cols + 1):
                active = sum(board.edge_state(edge) == ACTIVE for edge in board._vertex_edges(row, column))
                if active not in (0, 2): return False

        # Verifica componente gráfica (ciclo único)
        active_edges = []
        for row in range(board.rows + 1):
            for column in range(board.cols):
                if board.h_states[row][column] == ACTIVE: active_edges.append(('h', row, column))
        for row in range(board.rows):
            for column in range(board.cols + 1):
                if board.v_states[row][column] == ACTIVE: active_edges.append(('v', row, column))

        if not active_edges: return False

        adjacency = {}
        for edge in active_edges:
            a, b = board.edge_vertices(edge)
            adjacency.setdefault(a, []).append(b)
            adjacency.setdefault(b, []).append(a)

        visited = set()
        start = next(iter(adjacency))
        stack = [start]
        while stack:
            vertex = stack.pop()
            if vertex in visited: continue
            visited.add(vertex)
            for neighbor in adjacency.get(vertex, []):
                if neighbor not in visited: stack.append(neighbor)

        return len(visited) == len(adjacency)

    def h(self, node: Node):
        """Heuristic function used by A* search."""
        board = node.state.board
        penalty = board.unknown_edge_count()
        for row in range(board.rows):
            for column in range(board.cols):
                hint = board.hints[row][column]
                if hint < 0: continue
                active = board.get_active_edges(row, column)
                if active > hint: penalty += 10
                else: penalty += abs(hint - active)
        return penalty


def _format_solution(board):
    rows = []
    for row in range(board.rows):
        current = []
        for column in range(board.cols):
            top = 1 if board.h_states[row][column] == ACTIVE else 0
            right = 1 if board.v_states[row][column + 1] == ACTIVE else 0
            bottom = 1 if board.h_states[row + 1][column] == ACTIVE else 0
            left = 1 if board.v_states[row][column] == ACTIVE else 0
            current.append(f"{top}{right}{bottom}{left}")
        # A formatação típica é com tabs, o que se enquadra nos outputs de teste
        rows.append("\t".join(current))
    return "\n".join(rows)


if __name__ == "__main__":
    sys.setrecursionlimit(2000)
    board = Board.parse_instance()
    problem = Slytherlink(board)
    
    # Resolvido utilizando uma procura do search.py tal como requisitado
    goal_node = depth_first_tree_search(problem)
    
    if goal_node is not None:
        print(_format_solution(goal_node.state.board))