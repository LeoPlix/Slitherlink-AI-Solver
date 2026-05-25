#!/usr/bin/python3
# slitherlink.py: Template para implementação do projeto de Inteligência Artificial 2025/2026.
# Devem alterar as classes e funções neste ficheiro de acordo com as instruções do enunciado.
# Além das funções e classes sugeridas, podem acrescentar outras que considerem pertinentes.

# Grupo 62:
# 113396 Leonor Costa Guedes
# 113402 Manuel Francisco Santos Ramos Soares

import random, copy, sys
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

class SlitherlinkState:
    state_id = 0

    def __init__(self, board):
        self.board = board
        self.id = SlitherlinkState.state_id
        SlitherlinkState.state_id += 1
    
    def __lt__(self, other):
        return self.id < other.id

    def __eq__(self, other):
        return isinstance(other, SlitherlinkState) and self.board.signature() == other.board.signature()

    def __hash__(self):
        return hash(self.board.signature())


class Board:
    def __init__(self, hints, h_states=None, v_states=None):
        self.hints = [row[:] for row in hints]
        self.rows = len(self.hints)
        self.cols = len(self.hints[0]) if self.rows else 0
        # h_states and v_states keep track of horizontal and vertical edge statuses
        self.h_states = h_states if h_states is not None else [[UNKNOWN] * self.cols for _ in range(self.rows + 1)]
        self.v_states = v_states if v_states is not None else [[UNKNOWN] * (self.cols + 1) for _ in range(self.rows)]
        self.is_valid = True
        self.sync_views()

    def copy(self):
        new_board = Board(
            self.hints,
            [row[:] for row in self.h_states],
            [row[:] for row in self.v_states],
        )
        new_board.is_valid = self.is_valid
        return new_board

    def signature(self):
        return tuple(tuple(row) for row in self.h_states), tuple(tuple(row) for row in self.v_states)

    def sync_views(self):
        pass

    def edge_state(self, edge):
        kind, row, column = edge
        if kind == 'h': return self.h_states[row][column]
        return self.v_states[row][column]

    def set_edge_state(self, edge, value):
        kind, row, column = edge
        if kind == 'h':
            current = self.h_states[row][column]
            if current not in (UNKNOWN, value): return False
            self.h_states[row][column] = value
        else:
            current = self.v_states[row][column]
            if current not in (UNKNOWN, value): return False
            self.v_states[row][column] = value
        return True

    def edge_vertices(self, edge):
        kind, row, column = edge
        if kind == 'h': return (row, column), (row, column + 1)
        return (row, column), (row + 1, column)

    def _vertex_edges(self, row, column):
        edges = []
        if column > 0: edges.append(('h', row, column - 1))
        if column < self.cols: edges.append(('h', row, column))
        if row > 0: edges.append(('v', row - 1, column))
        if row < self.rows: edges.append(('v', row, column))
        return edges

    def unknown_edge_count(self):
        return sum(state == UNKNOWN for row in self.h_states for state in row) + sum(
            state == UNKNOWN for row in self.v_states for state in row
        )

    def get_cell_edges(self, row:int, column:int) -> list:
        return [
            ('h', row, column),
            ('v', row, column + 1),
            ('h', row + 1, column),
            ('v', row, column),
        ]

    def get_active_edges(self, row:int, column:int) -> int:
        return sum(self.edge_state(edge) == ACTIVE for edge in self.get_cell_edges(row, column))

    @staticmethod
    def parse_instance():
        grid = []
        for line in stdin:
            line = line.strip('\r\n')
            if not line: continue
            
            if '\t' in line:
                row = line.split('\t')
            else:
                row = line.split()
                
            parsed_row = []
            for token in row:
                token = token.strip()
                if token.isdigit(): 
                    parsed_row.append(int(token))
                else: 
                    parsed_row.append(-1)
            grid.append(parsed_row)
            
        if not grid: raise ValueError("Empty instance.")
        
        max_cols = max(len(r) for r in grid)
        for r in grid:
            while len(r) < max_cols:
                r.append(-1)
                
        return Board(grid)


class Slitherlink(Problem):
    def __init__(self, board: Board, gui=None):
        self.gui = gui
        initial_board = board.copy()
        
        # Initial deterministic propagation before search starts
        if not self._propagate(initial_board):
            initial_board.is_valid = False
            
        initial_board.sync_views()
        self.initial = SlitherlinkState(initial_board)
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
        if board.edge_state(edge) == value: return True, False
        if board.edge_state(edge) not in (UNKNOWN, value): return False, False
        if not board.set_edge_state(edge, value): return False, False
        return True, True

    def _propagate(self, board):
        # Fixed-point iteration loop for logical inference
        while True:
            changed = False

            # First: Cell-based local constraints propagation
            for row in range(board.rows):
                for column in range(board.cols):
                    hint, active, unknown_edges = self._cell_state(board, row, column)
                    if hint < 0: continue
                    if active > hint or active + len(unknown_edges) < hint: return False
                    
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

            # Second: Vertex-based continuity constraints propagation
            for row in range(board.rows + 1):
                for column in range(board.cols + 1):
                    active, unknown_edges = self._vertex_state(board, row, column)
                    if active > 2: return False
                    if active == 1 and len(unknown_edges) == 0: return False
                    
                    if active == 2:
                        for edge in unknown_edges:
                            ok, edge_changed = self._set_and_track(board, edge, FORBIDDEN)
                            if not ok: return False
                            changed = changed or edge_changed
                    elif active == 1 and len(unknown_edges) == 1:
                        ok, edge_changed = self._set_and_track(board, unknown_edges[0], ACTIVE)
                        if not ok: return False
                        changed = changed or edge_changed
                    elif active == 0 and len(unknown_edges) == 1:
                        ok, edge_changed = self._set_and_track(board, unknown_edges[0], FORBIDDEN)
                        if not ok: return False
                        changed = changed or edge_changed

            if not changed: break

        # Prune invalid states containing premature closed loops   
        if self._has_closed_cycle(board): return False
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

        for v, neighbors in adjacency.items():
            if len(neighbors) > 2: return True

        # Connected components extraction to identify isolated loops
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

        for comp in components:
            is_closed = all(len(adjacency[v]) == 2 for v in comp)
            if is_closed:
                if len(active_edges) > len(comp): return True
                
                for r in range(board.rows):
                    for c in range(board.cols):
                        hint = board.hints[r][c]
                        if hint >= 0 and board.get_active_edges(r, c) != hint: 
                            return True 
                
                for r in range(board.rows + 1):
                    for c in range(board.cols):
                        if board.h_states[r][c] == UNKNOWN:
                            board.h_states[r][c] = FORBIDDEN
                for r in range(board.rows):
                    for c in range(board.cols + 1):
                        if board.v_states[r][c] == UNKNOWN:
                            board.v_states[r][c] = FORBIDDEN
                            
                return False
        return False

    def _select_edge(self, board):
        best_edge = None
        best_score = float('inf')

        # Heuristic scoring to prioritize branching on the most constrained areas
        def get_edge_score(kind, row, column):
            score = 0
            v1, v2 = board.edge_vertices((kind, row, column))
            for v in (v1, v2):
                active = sum(1 for e in board._vertex_edges(*v) if board.edge_state(e) == ACTIVE)
                if active == 1:
                    score -= 1000 
            
            cells = []
            if kind == 'h':
                if row > 0: cells.append((row - 1, column))
                if row < board.rows: cells.append((row, column))
            else:
                if column > 0: cells.append((row, column - 1))
                if column < board.cols: cells.append((row, column))
            
            for r, c in cells:
                hint = board.hints[r][c]
                if hint >= 0:
                    unknowns = sum(1 for e in board.get_cell_edges(r, c) if board.edge_state(e) == UNKNOWN)
                    score += unknowns * 10
                    
                    if hint == 3: score -= 500
                    elif hint == 2: score -= 100
                    elif hint == 1: score -= 50
                else:
                    score += 100 
            return score

        for row in range(board.rows + 1):
            for column in range(board.cols):
                edge = ('h', row, column)
                if board.edge_state(edge) == UNKNOWN:
                    score = get_edge_score('h', row, column)
                    if score < best_score:
                        best_score = score
                        best_edge = edge

        for row in range(board.rows):
            for column in range(board.cols + 1):
                edge = ('v', row, column)
                if board.edge_state(edge) == UNKNOWN:
                    score = get_edge_score('v', row, column)
                    if score < best_score:
                        best_score = score
                        best_edge = edge

        return best_edge

    def actions(self, state: SlitherlinkState):
        board = state.board
        if not getattr(board, 'is_valid', True):
            return []
            
        edge = self._select_edge(board)
        if edge is None: return []

        return [
            (edge[0], edge[1], edge[2], FORBIDDEN),
            (edge[0], edge[1], edge[2], ACTIVE)
        ]

    def result(self, state: SlitherlinkState, action):
        kind, row, column, value = action
        board = state.board.copy()
        
        # Applies branching decision and triggers recursive logical propagation
        if not board.set_edge_state((kind, row, column), value):
            board.is_valid = False
        elif not self._propagate(board):
            board.is_valid = False
            
        next_state = SlitherlinkState(board)
        return next_state

    def goal_test(self, state: SlitherlinkState):
        board = state.board
        if not getattr(board, 'is_valid', True): return False
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
        # Heuristic cost function evaluating state penalizations and hints alignment
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

Slytherlink = Slitherlink

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
        rows.append("\t".join(current))
    return "\n".join(rows)

if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    
    board = Board.parse_instance()
    problem = Slitherlink(board)

    # Uses Depth-First Search strategy to locate the unique goal state efficiently
    goal_node = depth_first_tree_search(problem)

    if goal_node is not None:
        print(_format_solution(goal_node.state.board))