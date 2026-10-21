import threading
import time
import unittest

from app.controller import Controller, Mode
from app.tasks import TaskRunner


def drain(runner: TaskRunner, expected: int, timeout: float = 2.0) -> int:
    """Poll like the GUI loop would, until `expected` tasks have reported."""
    handled, deadline = 0, time.time() + timeout
    while handled < expected and time.time() < deadline:
        handled += runner.poll()
        time.sleep(0.01)
    return handled


class TaskRunnerTests(unittest.TestCase):
    def test_success_callback_runs_on_polling_thread(self):
        runner, seen = TaskRunner(), {}
        runner.submit("t", lambda: 42, on_success=lambda v: seen.update(v=v, thread=threading.current_thread()))
        self.assertEqual(drain(runner, 1), 1)
        self.assertEqual(seen["v"], 42)
        self.assertIs(seen["thread"], threading.current_thread())  # not the worker thread

    def test_error_callback_receives_exception(self):
        runner, errors = TaskRunner(), []
        runner.submit("t", lambda: 1 / 0, on_error=errors.append)
        drain(runner, 1)
        self.assertIsInstance(errors[0], ZeroDivisionError)

    def test_duplicate_submit_rejected_while_running(self):
        runner, gate = TaskRunner(), threading.Event()
        self.assertTrue(runner.submit("same", gate.wait))
        self.assertTrue(runner.is_busy("same"))
        self.assertFalse(runner.submit("same", lambda: None))
        gate.set()
        drain(runner, 1)
        self.assertFalse(runner.is_busy("same"))
        self.assertTrue(runner.submit("same", lambda: None))

    def test_closed_runner_rejects_and_drops_results(self):
        runner, called = TaskRunner(), []
        runner.submit("t", lambda: 1, on_success=called.append)
        runner.close()
        drain(runner, 1)
        self.assertEqual(called, [])
        self.assertFalse(runner.submit("u", lambda: 1))


class ControllerTests(unittest.TestCase):
    def test_defaults_to_offline_and_blocks_network(self):
        c = Controller()
        self.assertEqual(c.mode, Mode.OFFLINE)
        self.assertFalse(c.network_allowed())

    def test_mode_change_notifies_listeners_once(self):
        c, seen = Controller(), []
        c.on_mode_change(seen.append)
        c.set_mode(Mode.ONLINE)
        c.set_mode(Mode.ONLINE)  # no change -> no notification
        self.assertEqual(seen, [Mode.ONLINE])
        self.assertTrue(c.network_allowed())


if __name__ == "__main__":
    unittest.main()
