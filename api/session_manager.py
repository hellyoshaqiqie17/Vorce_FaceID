import uuid
import time
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np
from api.models import RegisterStep


@dataclass
class RegistrationSession:
    session_id: str
    user_id: str
    created_at: float
    current_step: RegisterStep = RegisterStep.FRONT
    embeddings: List[np.ndarray] = field(default_factory=list)
    step_samples: Dict[str, int] = field(default_factory=dict)
    is_complete: bool = False

    SAMPLES_PER_STEP = 3
    STEPS = [RegisterStep.FRONT, RegisterStep.LEFT, RegisterStep.RIGHT]

    def __post_init__(self):
        self.step_samples = {step.value: 0 for step in self.STEPS}

    def add_embedding(self, embedding: np.ndarray) -> bool:
        key = self.current_step.value
        if self.step_samples[key] < self.SAMPLES_PER_STEP:
            self.embeddings.append(embedding)
            self.step_samples[key] += 1
            return True
        return False

    def is_step_complete(self) -> bool:
        return self.step_samples[self.current_step.value] >= self.SAMPLES_PER_STEP

    def advance_step(self) -> Optional[RegisterStep]:
        if not self.is_step_complete():
            return None
        idx = self.STEPS.index(self.current_step)
        if idx < len(self.STEPS) - 1:
            self.current_step = self.STEPS[idx + 1]
            return self.current_step
        self.current_step = RegisterStep.COMPLETE
        self.is_complete = True
        return RegisterStep.COMPLETE

    def get_progress(self) -> float:
        total = self.SAMPLES_PER_STEP * len(self.STEPS)
        collected = sum(self.step_samples.values())
        return min(1.0, collected / total)

    def get_current_step_progress(self) -> int:
        return self.step_samples.get(self.current_step.value, 0)


class SessionManager:
    TIMEOUT = 300

    def __init__(self):
        self._sessions: Dict[str, RegistrationSession] = {}

    def create_session(self, user_id: str) -> RegistrationSession:
        self._cleanup()
        session = RegistrationSession(
            session_id=str(uuid.uuid4()),
            user_id=user_id,
            created_at=time.time()
        )
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[RegistrationSession]:
        session = self._sessions.get(session_id)
        if session and (time.time() - session.created_at) > self.TIMEOUT:
            del self._sessions[session_id]
            return None
        return session

    def remove_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    def _cleanup(self):
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if (now - s.created_at) > self.TIMEOUT]
        for sid in expired:
            del self._sessions[sid]


session_manager = SessionManager()
