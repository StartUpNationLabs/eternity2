from pathlib import Path

import gradio as gr

from eternitylib.board import Board
from statiscticslib.grapher import Grapher
from statiscticslib.runner import Runner


def board_to_image(text, file) -> (str, Path):
    if not text and not file:
        raise ValueError("No input provided")

    if text and file:
        raise ValueError("Both text and file provided, please provide only one")

    board = Board()

    if text:
        board.read_csv(text)

    if file:
        board.read_file(Path(file))

    return f"Board: {board.size}x{board.size}, {board.pattern_count} patterns", board.image


def generate_board(size: int, pattern_count: int) -> (str, Path, Path):
    board = Board()
    board.generate(size, pattern_count)
    unsorted_board = board.image
    board.generate_hints()
    board.shuffle()
    return board.to_csv(), unsorted_board, board.image


def generate_statistics(start_size: int, end_size: int, start_pattern_count: int, end_pattern_count: int, timeout: float = 4, progress=gr.Progress(track_tqdm=True)) -> Path:
    runner = Runner((start_size, end_size), (start_pattern_count, end_pattern_count), timeout=timeout)

    results = runner.solve_boards(progress)

    grapher = Grapher(results)
    return grapher.plot_time_over_size_and_pattern_count_plotly()


image_gen = gr.Interface(
    fn=board_to_image,
    inputs=["text", "file"],
    outputs=["text", "image"]
)

board_gen = gr.Interface(
    fn=generate_board,
    inputs=[
        gr.Slider(2, 32, 12, step=1, label="Puzzle Size"),
        gr.Slider(1, 128, 22, step=1, label="Pattern count"),
    ],
    outputs=[gr.Textbox(label="Board Data", show_copy_button=True), "image", "image"]
)

statistics_gen = gr.Interface(
    fn=generate_statistics,
    inputs=[
        gr.Slider(2, 32, 2, step=1, label="Minimum Size"),
        gr.Slider(2, 32, 4, step=1, label="Maximum Size"),
        gr.Slider(2, 32, 2, step=1, label="Minimum Pattern Count"),
        gr.Slider(2, 32, 10, step=1, label="Maximum Pattern Count"),
        gr.Slider(0.1, 600, 4, label="Timeout (seconds)")
    ],
    outputs=[
        gr.Plot(label="Time over Size and Pattern Count")
    ]
)

interface = gr.TabbedInterface([board_gen, image_gen, statistics_gen],
                               ["Generate Board", "Generate Image", "Generate Statistics"])

if __name__ == "__main__":
    interface.launch(share=True)
