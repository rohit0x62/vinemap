"""Per-turn read budgets and duplicate-read deduplication for agents."""

from typing import Dict, Optional, Set, Tuple

DEFAULT_READ_BUDGET = 12  # max graph_read calls per session window
DEFAULT_RETRIEVE_BUDGET = 6


class Guardrails:
    """Track agent tool usage to nudge toward graph-first exploration."""

    def __init__(
        self,
        read_budget: int = DEFAULT_READ_BUDGET,
        retrieve_budget: int = DEFAULT_RETRIEVE_BUDGET,
    ):
        self.read_budget = read_budget
        self.retrieve_budget = retrieve_budget
        self.reads: Set[str] = set()
        self.read_count = 0
        self.retrieve_count = 0
        self.grep_hints = 0

    def check_read(self, path: str) -> Tuple[bool, Optional[str]]:
        if path in self.reads:
            return True, (
                f"Hint: you already read {path} this session — "
                "use graph_neighbors or graph_retrieve instead of re-reading."
            )
        if self.read_count >= self.read_budget:
            return False, (
                f"Read budget exhausted ({self.read_budget} files). "
                "Use graph_retrieve with a broader query instead of sequential reads."
            )
        return True, None

    def record_read(self, path: str) -> None:
        self.reads.add(path)
        self.read_count += 1

    def check_retrieve(self) -> Tuple[bool, Optional[str]]:
        if self.retrieve_count >= self.retrieve_budget:
            return False, (
                f"Retrieve budget exhausted ({self.retrieve_budget}). "
                "Refine your query or use graph_read on specific paths from the last pack."
            )
        return True, None

    def record_retrieve(self) -> None:
        self.retrieve_count += 1

    def grep_hint(self) -> Optional[str]:
        """Nudge away from grep-style exploration when graph tools are available."""
        if self.read_count >= 4 and self.retrieve_count == 0:
            return (
                "Hint: use graph_retrieve with a natural-language query instead of "
                "sequential grep/read — Vinemap ranks by imports, symbols, and calls."
            )
        if self.read_count >= self.read_budget // 2:
            return (
                "Hint: broad searches belong in graph_retrieve; use graph_neighbors "
                "to expand from a seed file instead of grep across the tree."
            )
        return None

    def stats(self) -> Dict[str, int]:
        return {
            "reads": self.read_count,
            "unique_reads": len(self.reads),
            "retrieves": self.retrieve_count,
            "read_budget": self.read_budget,
            "retrieve_budget": self.retrieve_budget,
        }
