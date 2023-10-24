from __future__ import annotations

import argparse
import cProfile
import json
import os
from typing import Any, Dict, Optional, TYPE_CHECKING

from ts import d2d


class Namespace(argparse.Namespace):
    if TYPE_CHECKING:
        problem: str
        iterations: int
        shuffle_after: int
        tabu_size: int
        profile: bool
        verbose: bool
        dump: Optional[str]
        pool_size: int


def to_json(solution: d2d.D2DPathSolution) -> Dict[str, Any]:
    return {
        "cost": solution.cost(),
        "drone_paths": solution.drone_paths,
        "technician_paths": solution.technician_paths,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Tabu search algorithm for TSP problems")
    parser.add_argument("problem", type=str, help="the problem name (e.g. \"6.5.1\", \"200.10.1\", ...)")
    parser.add_argument("-i", "--iterations", default=500, type=int, help="the number of iterations to run the tabu search for (default: 500)")
    parser.add_argument("-s", "--shuffle-after", default=10, type=int, help="after the specified number of non-improved iterations, shuffle the solution (default: 10)")
    parser.add_argument("-t", "--tabu-size", default=10, type=int, help="the tabu size for every neighborhood (default: 10)")
    parser.add_argument("-p", "--profile", action="store_true", help="run in profile mode and exit immediately")
    parser.add_argument("-v", "--verbose", action="store_true", help="whether to display the progress bar and plot the solution")
    parser.add_argument("-d", "--dump", type=str, help="dump the solution to a file")

    default_pool_size = os.cpu_count() or 1
    parser.add_argument("--pool-size", default=default_pool_size, type=int, help=f"the size of the process pool (default: {default_pool_size})")

    namespace: Namespace = parser.parse_args()  # type: ignore
    print(namespace)
    d2d.D2DPathSolution.import_problem(namespace.problem)

    d2d.Swap.reset_tabu(maxlen=namespace.tabu_size)

    eval_func = f"""d2d.D2DPathSolution.tabu_search(
        pool_size={namespace.pool_size},
        iterations_count={namespace.iterations},
        use_tqdm={namespace.verbose},
        shuffle_after={namespace.shuffle_after},
    )"""
    if namespace.profile:
        cProfile.run(eval_func)
        exit(0)
    else:
        solutions = d2d.D2DPathSolution.tabu_search(
            pool_size=namespace.pool_size,
            iterations_count=namespace.iterations,
            use_tqdm=namespace.verbose,
            shuffle_after=namespace.shuffle_after,
        )

    print(f"Found {len(solutions)} solution(s):")
    for index, solution in enumerate(solutions):
        print(f"SOLUTION #{index + 1}: cost = {solution.cost()}")
        print("Drone paths:\n" + "\n".join(f"Drone #{drone_index + 1}: {paths}" for drone_index, paths in enumerate(solution.drone_paths)))
        print("Technician paths:\n" + "\n".join(f"Drone #{technician_index + 1}: {path}" for technician_index, path in enumerate(solution.technician_paths)))

        if namespace.verbose:
            solution.plot()

    if namespace.dump is not None:
        with open(namespace.dump, "w") as f:
            data = {
                "problem": namespace.problem,
                "iterations": namespace.iterations,
                "tabu-size": namespace.tabu_size,
                "shuffle-after": namespace.shuffle_after,
                "solutions": [to_json(s) for s in solutions],
            }
            json.dump(data, f)

        print(f"Saved solution to {namespace.dump!r}")
