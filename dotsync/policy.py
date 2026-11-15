from typing import Literal

ConflictPolicy = Literal['prompt', 'overwrite', 'keep', 'abort']
CandidatePolicy = Literal['prompt', 'prefer-home', 'prefer-master', 'abort']


class RunPolicy:
    def __init__(
        self,
        non_interactive=False,
        conflict='prompt',
        candidate='prompt',
        keep_going=False,
        skip_pull=False,
        force_content_regression=False,
    ):
        self.non_interactive = non_interactive
        self.conflict = conflict
        self.candidate = candidate
        self.keep_going = keep_going
        self.skip_pull = skip_pull
        self.force_content_regression = force_content_regression


def from_args(args) -> RunPolicy:
    return RunPolicy(
        non_interactive=getattr(args, 'non_interactive', False),
        conflict=getattr(args, 'conflict', 'prompt'),
        candidate=getattr(args, 'candidate', 'prompt'),
        keep_going=getattr(args, 'keep_going', False),
        skip_pull=getattr(args, 'skip_pull', False),
        force_content_regression=getattr(args, 'force_content_regression', False),
    )
