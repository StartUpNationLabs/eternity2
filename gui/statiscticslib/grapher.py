from typing import List

import matplotlib.pyplot as plt

from statiscticslib.result import Result


class Grapher:
    def __init__(self, data: List[Result]):
        self.data = data

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

        plt.show()
