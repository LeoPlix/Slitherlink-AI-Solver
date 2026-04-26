# slitherlink_gui.py: Visual interface for the Slitherlink board.
#
# Each cell has four edges (top, right, bottom, left).
# Click an edge to cycle through states: unknown → active → forbidden → unknown.
# Use the toolbar to load boards/solutions and validate constraints.

import tkinter as tk
from tkinter import filedialog, messagebox
import os

# ── Visual constants ────────────────────────────────────────────────────────
CELL_SIZE    = 72        # pixels per cell
PADDING      = 44        # canvas border padding
DOT_RADIUS   = 5
EDGE_HIT     = 13        # click tolerance in pixels

BG           = "#f8fafc"
CANVAS_BG    = "#ffffff"
DOT_COLOR    = "#1e293b"
CELL_FILL    = "#f1f5f9"

UNKNOWN_COLOR   = "#cbd5e1"   # light gray dashed  – state 0
ACTIVE_COLOR    = "#2563eb"   # solid blue          – state 1 (part of loop)
FORBIDDEN_COLOR = "#ef4444"   # red cross           – state 2 (not in loop)

HINT_FONT    = ("Helvetica", 17, "bold")
HINT_COLOR   = "#0f172a"

# Edge state constants
UNKNOWN   = 0
ACTIVE    = 1
FORBIDDEN = 2


class SlitherlinkGUI:
    """Tkinter-based visual board for Slitherlink."""

    def __init__(self, root: tk.Tk, board_grid: list[list[int]]):
        self.root = root
        self.root.title("Slitherlink")
        self.root.configure(bg=BG)
        self.root.resizable(False, False)

        self._load_grid(board_grid)
        self._build_ui()
        self._draw_board()

    # ── Data helpers ────────────────────────────────────────────────────────

    def _load_grid(self, board_grid: list[list[int]]):
        self.hints  = board_grid
        self.rows   = len(board_grid)
        self.cols   = len(board_grid[0]) if self.rows > 0 else 0
        # Horizontal edges: (rows+1) rows × cols cols
        self.h_edges = [[UNKNOWN] * self.cols for _ in range(self.rows + 1)]
        # Vertical edges: rows rows × (cols+1) cols
        self.v_edges = [[UNKNOWN] * (self.cols + 1) for _ in range(self.rows)]

    def _reset_edges(self):
        self.h_edges = [[UNKNOWN] * self.cols for _ in range(self.rows + 1)]
        self.v_edges = [[UNKNOWN] * (self.cols + 1) for _ in range(self.rows)]

    # ── UI construction ─────────────────────────────────────────────────────

    def _build_ui(self):
        # Toolbar
        bar = tk.Frame(self.root, bg=BG, pady=8)
        bar.pack(side=tk.TOP, fill=tk.X, padx=14)

        btn_style = dict(bg="#e2e8f0", relief=tk.FLAT, padx=12, pady=4,
                         font=("Helvetica", 11), cursor="hand2")

        tk.Button(bar, text="Load Board",    command=self._load_board,    **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="Load Solution", command=self._load_solution, **btn_style).pack(side=tk.LEFT, padx=4)
        tk.Button(bar, text="Clear Edges",   command=self._clear_edges,   **btn_style).pack(side=tk.LEFT, padx=4)

        validate_style = {**btn_style, "bg": "#dbeafe"}
        tk.Button(bar, text="Validate", command=self._validate, **validate_style).pack(side=tk.LEFT, padx=4)

        # Legend
        legend = tk.Frame(self.root, bg=BG)
        legend.pack(side=tk.TOP, fill=tk.X, padx=18, pady=(0, 4))
        self._legend_item(legend, ACTIVE_COLOR,    "Active edge")
        self._legend_item(legend, FORBIDDEN_COLOR, "Forbidden edge")
        self._legend_item(legend, UNKNOWN_COLOR,   "Unknown edge")
        tk.Label(legend, text="(click edge to cycle state)",
                 bg=BG, fg="#94a3b8", font=("Helvetica", 10)).pack(side=tk.LEFT, padx=8)

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width  = self.cols * CELL_SIZE + 2 * PADDING,
            height = self.rows * CELL_SIZE + 2 * PADDING,
            bg=CANVAS_BG, highlightthickness=1, highlightbackground="#e2e8f0"
        )
        self.canvas.pack(padx=20, pady=(0, 6))
        self.canvas.bind("<Button-1>", self._on_click)

        # Status bar
        self.status = tk.StringVar(value="Click an edge to toggle it.")
        tk.Label(self.root, textvariable=self.status, bg=BG, fg="#64748b",
                 anchor="w", font=("Helvetica", 10), padx=20).pack(
            side=tk.BOTTOM, fill=tk.X, pady=(0, 8))

    @staticmethod
    def _legend_item(parent, color, label):
        f = tk.Frame(parent, bg=BG)
        f.pack(side=tk.LEFT, padx=6)
        tk.Canvas(f, width=28, height=4, bg=color,
                  highlightthickness=0).pack(side=tk.LEFT, padx=(0, 4))
        tk.Label(f, text=label, bg=BG, fg="#475569",
                 font=("Helvetica", 10)).pack(side=tk.LEFT)

    def _resize_canvas(self):
        self.canvas.config(
            width  = self.cols * CELL_SIZE + 2 * PADDING,
            height = self.rows * CELL_SIZE + 2 * PADDING,
        )

    # ── Coordinate helpers ───────────────────────────────────────────────────

    def _dot(self, row: int, col: int) -> tuple[int, int]:
        """Canvas (x, y) for grid dot at (row, col)."""
        return PADDING + col * CELL_SIZE, PADDING + row * CELL_SIZE

    # ── Drawing ──────────────────────────────────────────────────────────────

    def _draw_board(self):
        self.canvas.delete("all")
        self._draw_cells()
        self._draw_edges()
        self._draw_dots()
        self._draw_hints()

    def _draw_cells(self):
        for r in range(self.rows):
            for c in range(self.cols):
                x0, y0 = self._dot(r, c)
                x1, y1 = self._dot(r + 1, c + 1)
                self.canvas.create_rectangle(x0, y0, x1, y1,
                                             fill=CELL_FILL, outline="")

    def _draw_edges(self):
        # Horizontal edges
        for r in range(self.rows + 1):
            for c in range(self.cols):
                x0, y0 = self._dot(r, c)
                x1, _  = self._dot(r, c + 1)
                self._draw_single_edge(x0, y0, x1, y0, self.h_edges[r][c])

        # Vertical edges
        for r in range(self.rows):
            for c in range(self.cols + 1):
                x0, y0 = self._dot(r, c)
                _,  y1 = self._dot(r + 1, c)
                self._draw_single_edge(x0, y0, x0, y1, self.v_edges[r][c])

    def _draw_single_edge(self, x0, y0, x1, y1, state: int):
        if state == ACTIVE:
            self.canvas.create_line(x0, y0, x1, y1,
                                    fill=ACTIVE_COLOR, width=4)
        elif state == FORBIDDEN:
            # Faint line + small X at midpoint
            mx, my = (x0 + x1) // 2, (y0 + y1) // 2
            self.canvas.create_line(x0, y0, x1, y1,
                                    fill="#fca5a5", width=2, dash=(3, 5))
            d = 6
            self.canvas.create_line(mx - d, my - d, mx + d, my + d,
                                    fill=FORBIDDEN_COLOR, width=2)
            self.canvas.create_line(mx + d, my - d, mx - d, my + d,
                                    fill=FORBIDDEN_COLOR, width=2)
        else:  # UNKNOWN
            self.canvas.create_line(x0, y0, x1, y1,
                                    fill=UNKNOWN_COLOR, width=2, dash=(4, 5))

    def _draw_dots(self):
        for r in range(self.rows + 1):
            for c in range(self.cols + 1):
                x, y = self._dot(r, c)
                self.canvas.create_oval(
                    x - DOT_RADIUS, y - DOT_RADIUS,
                    x + DOT_RADIUS, y + DOT_RADIUS,
                    fill=DOT_COLOR, outline=""
                )

    def _draw_hints(self):
        for r in range(self.rows):
            for c in range(self.cols):
                hint = self.hints[r][c]
                if hint >= 0:
                    cx = PADDING + c * CELL_SIZE + CELL_SIZE // 2
                    cy = PADDING + r * CELL_SIZE + CELL_SIZE // 2
                    self.canvas.create_text(cx, cy, text=str(hint),
                                            font=HINT_FONT, fill=HINT_COLOR)

    # ── Click handling ────────────────────────────────────────────────────────

    def _on_click(self, event):
        px, py = event.x, event.y
        best_dist  = None
        best_kind  = None
        best_r = best_c = 0

        # Check horizontal edges
        for r in range(self.rows + 1):
            for c in range(self.cols):
                x0, ey = self._dot(r, c)
                x1, _  = self._dot(r, c + 1)
                if x0 <= px <= x1:
                    dist = abs(py - ey)
                else:
                    dx = min(abs(px - x0), abs(px - x1))
                    dist = (dx ** 2 + (py - ey) ** 2) ** 0.5
                if dist < EDGE_HIT and (best_dist is None or dist < best_dist):
                    best_dist, best_kind, best_r, best_c = dist, 'h', r, c

        # Check vertical edges
        for r in range(self.rows):
            for c in range(self.cols + 1):
                ex, y0 = self._dot(r, c)
                _,  y1 = self._dot(r + 1, c)
                if y0 <= py <= y1:
                    dist = abs(px - ex)
                else:
                    dy = min(abs(py - y0), abs(py - y1))
                    dist = ((px - ex) ** 2 + dy ** 2) ** 0.5
                if dist < EDGE_HIT and (best_dist is None or dist < best_dist):
                    best_dist, best_kind, best_r, best_c = dist, 'v', r, c

        if best_kind == 'h':
            self.h_edges[best_r][best_c] = (self.h_edges[best_r][best_c] + 1) % 3
            self._draw_board()
            self.status.set(
                f"Horizontal edge ({best_r},{best_c}) → "
                f"{['unknown','active','forbidden'][self.h_edges[best_r][best_c - 1 if best_c > 0 else 0]]}"
            )
        elif best_kind == 'v':
            self.v_edges[best_r][best_c] = (self.v_edges[best_r][best_c] + 1) % 3
            self._draw_board()

    # ── Solution loading ──────────────────────────────────────────────────────

    def load_solution(self, sol_grid: list[list[str]]):
        """Apply a solution grid of 4-char strings (index 0=top,1=right,2=bottom,3=left)."""
        self._reset_edges()
        for r in range(min(self.rows, len(sol_grid))):
            for c in range(min(self.cols, len(sol_grid[r]))):
                bits = sol_grid[r][c]
                if len(bits) != 4:
                    continue
                top, right, bottom, left = (int(b) for b in bits)
                if top:    self.h_edges[r][c]      = ACTIVE
                if bottom: self.h_edges[r + 1][c]  = ACTIVE
                if left:   self.v_edges[r][c]       = ACTIVE
                if right:  self.v_edges[r][c + 1]   = ACTIVE
        self._draw_board()

    # ── Toolbar actions ───────────────────────────────────────────────────────

    def _load_board(self):
        path = filedialog.askopenfilename(
            title="Open Board File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            grid = _parse_board_file(path)
            self._load_grid(grid)
            self._resize_canvas()
            self._draw_board()
            self.status.set(f"Board loaded: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load board:\n{exc}")

    def _load_solution(self):
        path = filedialog.askopenfilename(
            title="Open Solution File",
            filetypes=[("All files", "*.*"), ("Text files", "*.txt *.out")],
        )
        if not path:
            return
        try:
            sol_grid = []
            with open(path) as f:
                for line in f:
                    row = line.strip().split()
                    if row:
                        sol_grid.append(row)
            self.load_solution(sol_grid)
            self.status.set(f"Solution loaded: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load solution:\n{exc}")

    def update_from_state(self, state):
        """Sync the board display with a SlitherlinkState produced by result()."""
        for r in range(self.rows + 1):
            for c in range(self.cols):
                self.h_edges[r][c] = ACTIVE if state.horizontal_walls[r][c] else UNKNOWN
        for r in range(self.rows):
            for c in range(self.cols + 1):
                self.v_edges[r][c] = ACTIVE if state.vertical_walls[r][c] else UNKNOWN
        self._draw_board()
        self.root.update()          # flush tkinter event queue → immediate redraw

    def _clear_edges(self):
        self._reset_edges()
        self._draw_board()
        self.status.set("All edges cleared.")

    def _validate(self):
        errors = []
        for r in range(self.rows):
            for c in range(self.cols):
                hint = self.hints[r][c]
                if hint < 0:
                    continue
                active = (
                    (self.h_edges[r][c]     == ACTIVE) +   # top
                    (self.h_edges[r + 1][c] == ACTIVE) +   # bottom
                    (self.v_edges[r][c]     == ACTIVE) +   # left
                    (self.v_edges[r][c + 1] == ACTIVE)     # right
                )
                if active != hint:
                    errors.append(f"Cell ({r},{c}): constraint {hint}, "
                                  f"but {active} active edge(s)")

        if errors:
            messagebox.showwarning("Constraint violations",
                                   "\n".join(errors[:15]) +
                                   ("\n…" if len(errors) > 15 else ""))
            self.status.set(f"{len(errors)} constraint violation(s) found.")
        else:
            messagebox.showinfo("Validation", "All cell constraints satisfied ✓")
            self.status.set("Valid — all constraints satisfied.")


# ── File parsers ──────────────────────────────────────────────────────────────

def _parse_board_file(path: str) -> list[list[int]]:
    grid = []
    with open(path) as f:
        for line in f:
            row = line.strip().split()
            if row:
                grid.append([int(c) if c.isdigit() else -1 for c in row])
    if not grid:
        raise ValueError("File is empty or contains no valid rows.")
    return grid


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    board_path = os.path.join(base, "slitherlink-boards-public", "test01.txt")
    sol_path   = os.path.join(base, "slitherlink-boards-public", "test01.out")

    # Fallback default board (matches test01.txt)
    board_grid = [
        [ 0, -1,  2, -1],
        [-1, -1,  0, -1],
        [-1,  0, -1, -1],
        [-1,  3, -1,  0],
    ]
    if os.path.exists(board_path):
        board_grid = _parse_board_file(board_path)

    root = tk.Tk()
    app  = SlitherlinkGUI(root, board_grid)

    # Auto-load solution if present
    if os.path.exists(sol_path):
        sol_grid = []
        with open(sol_path) as f:
            for line in f:
                row = line.strip().split()
                if row:
                    sol_grid.append(row)
        #app.load_solution(sol_grid)
        app.status.set("test01 loaded with solution — click edges to explore.")

    root.mainloop()

# Integration with slitherlink.py
# When your solver produces a solution, call app.load_solution(sol_grid) passing the same 4-char-per-cell grid that the .out file uses (index 0=top, 1=right, 2=bottom, 3=left).



if __name__ == "__main__":
    main()