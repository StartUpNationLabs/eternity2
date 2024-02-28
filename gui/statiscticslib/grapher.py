import random
import string
from pathlib import Path
from typing import List

import matplotlib.pyplot as plt
import pandas as pd
import plotly.graph_objects as go
from statiscticslib.result import Result


class Grapher:
    def __init__(self, data: List[Result]):
        self.data = data

    @property
    def df(self):
        # Create a dataframe with board size as columns and pattern count as index and time as values
        unique_sizes = list(set([result.board.size for result in self.data]))
        unique_patterns = list(set([result.board.pattern_count for result in self.data]))
        df = pd.DataFrame(columns=unique_sizes, index=unique_patterns)

        for result in self.data:
            # Group by size and pattern count and get the time
            size = result.board.size
            pattern_count = result.board.pattern_count
            df.loc[pattern_count, size] = result.execution.time

        return df

    def plot_time_over_size(self):
        plt.plot([result.board.size for result in self.data], [result.execution.time for result in self.data])
        plt.xlabel("Size")
        plt.ylabel("Time")
        plt.show()

    def plot_time_over_pattern_count(self):
        plt.plot([result.board.pattern_count for result in self.data], [result.execution.time for result in self.data])
        plt.xlabel("Pattern Count")
        plt.ylabel("Time")
        plt.show()

    def plot_time_over_size_and_pattern_count(self):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        print(self.data)

        ax.scatter([result.board.size for result in self.data], [result.board.pattern_count for result in self.data],
                   [result.execution.time for result in self.data])

        ax.set_xlabel("Size")
        ax.set_ylabel("Pattern Count")
        ax.set_zlabel("Time")

        rand_path = Path(
            __file__).parent.parent / "tmp" / f"{''.join(random.choices(string.ascii_lowercase, k=10))}.jpg"

        plt.show()
        plt.savefig(rand_path)
        return rand_path

    def plot_time_over_size_and_pattern_count_plotly(self) -> str:
        fig = go.Figure(data=[go.Surface(z=self.df.values)])

        fig.update_layout(scene=dict(
            xaxis_title='Size',
            yaxis_title='Pattern Count',
            zaxis_title='Time'
        ))

        return fig
