from dataclasses import dataclass, field


@dataclass
class ReActStep:
    thought: str
    action: str
    action_input: dict
    observation: str = ""

    def to_dict(self) -> dict:
        return {
            "thought": self.thought,
            "action": self.action,
            "action_input": self.action_input,
            "observation": self.observation,
        }


@dataclass
class ReActResult:
    steps: list[ReActStep] = field(default_factory=list)
    tool_results: dict = field(default_factory=dict)
    iterations: int = 0
