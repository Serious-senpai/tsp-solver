from __future__ import annotations

import random
from functools import partial
from multiprocessing import Pool
from typing import Any, Callable, List, Sequence, Set, Union, TYPE_CHECKING

from matplotlib import axes, pyplot
from tqdm import tqdm
if TYPE_CHECKING:
    from typing_extensions import Self

from .costs import BaseMulticostComparison
from ..types import _BaseSolution
from ...utils import true, zero
if TYPE_CHECKING:
    from .neighborhoods import MultiObjectiveNeighborhood


__all__ = ("MultiObjectiveSolution",)


class MultiObjectiveSolution(_BaseSolution, BaseMulticostComparison):
    """Base class for solutions to a multi-objective optimization problem"""

    __slots__ = ()

    def get_neighborhoods(self) -> Sequence[MultiObjectiveNeighborhood[Self, Any]]:
        raise NotImplementedError

    @classmethod
    def tabu_search(
        cls,
        *,
        pool_size: int,
        iterations_count: int,
        use_tqdm: bool,
        propagation_predicate: Callable[[Set[Self], Self], bool] = true,
        propagation_priority_key: Callable[[Set[Self], Self], float] = zero,
        max_propagation: Union[int, Callable[[Set[Self]], int], None] = None,
        plot_pareto_front: bool = False,
    ) -> Set[Self]:
        """Run the tabu search algorithm to find the Pareto front for this multi-objective optimization problem.

        Parameters
        -----
        pool_size:
            The size of the process pool to perform parallelism
        iterations_count:
            The number of iterations to improve from the initial solution
        use_tqdm:
            Whether to display the progress bar
        propagation_predicate:
            A function taking 2 arguments: The first one is the currently considered Pareto front, the second one is the solution S.
            It must return a boolean value indicating whether the solution S should be added to the search tree. The provided function
            mustn't change the Pareto front by any means.
        propagation_priority_key:
            A function taking 2 arguments: The first one is the currently considered Pareto front, the second one is the solution S.
            The less the returned value, the more likely the solution S is added to the search tree. The provided function mustn't
            change the Pareto front by any means
        max_propagation:
            An integer or a function that takes the current Pareto front as a single parameter and return the maximum number of
            propagating solutions at a time
        plot_pareto_front:
            Plot the Pareto front for 2-objective optimization problems only, default to False

        Returns
        -----
        The Pareto front among the iterated solutions

        See also
        -----
        - https://en.wikipedia.org/wiki/Pareto_efficiency
        - https://en.wikipedia.org/wiki/Pareto_front
        """
        initial = cls.initial()
        results: Set[Self] = set()
        results.add(initial)
        iterations: Union[range, tqdm[int]] = range(iterations_count)
        if use_tqdm:
            iterations = tqdm(iterations, ascii=" █")

        current = [initial]
        candidate_costs = [initial.cost()] if plot_pareto_front else None
        if len(initial.cost()) != 2:
            message = f"Cannot plot the Pareto front when the number of objectives is not 2"
            raise ValueError(message)

        with Pool(pool_size) as pool:
            for _ in iterations:
                if isinstance(iterations, tqdm):
                    iterations.set_description_str(f"Tabu search ({len(current)}/{len(results)} solution(s))")

                propagate: List[Self] = []
                for solution in current:
                    neighborhoods = solution.get_neighborhoods()
                    for candidate in random.choice(neighborhoods).find_best_candidates(pool=pool, pool_size=pool_size):
                        if candidate_costs is not None:
                            candidate_costs.append(candidate.cost())

                        if candidate.add_to_pareto_set(results) or propagation_predicate(results, candidate):
                            propagate.append(candidate)

                propagate.sort(key=partial(propagation_priority_key, results))
                if max_propagation is not None:
                    max_propagation_value = max_propagation if isinstance(max_propagation, int) else max_propagation(results)
                    current = propagate[:max_propagation_value]

        if candidate_costs is not None:
            _, ax = pyplot.subplots()
            assert isinstance(ax, axes.Axes)

            ax.scatter(
                [float(cost[0]) for cost in candidate_costs],
                [float(cost[1]) for cost in candidate_costs],
                c="gray",
                label=f"Found solutions ({len(candidate_costs)})",
            )
            ax.scatter(
                [float(result.cost()[0]) for result in results],
                [float(result.cost()[1]) for result in results],
                c="red",
                label=f"Pareto front ({len(results)})",
            )

            ax.grid(True)

            pyplot.legend()
            pyplot.show()

        return set(r.post_optimization(pool=pool, pool_size=pool_size, use_tqdm=use_tqdm) for r in results)
