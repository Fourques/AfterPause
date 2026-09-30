import tempfile
import unittest
from pathlib import Path
from core import Conflict, TaskStore


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'tasks.sqlite'
        self.now = 100
        self.store = TaskStore(self.path, clock=lambda: self.now)
        self.task = self.store.create('Pack for tomorrow', ['Choose bag', 'Pack charger', 'Check keys'])

    def test_restart_restores_exact_interruption(self):
        self.store.change(self.task['id'], 0, 'confirm_step')
        self.store.change(self.task['id'], 1, 'pause', note='Charger is on desk')
        resumed = TaskStore(self.path).checkpoint(self.task['id'])
        self.assertEqual(resumed['completed_steps'], ['Choose bag'])
        self.assertEqual(resumed['next_step'], 'Pack charger')
        self.assertEqual(resumed['task']['note'], 'Charger is on desk')
        self.assertEqual(resumed['task']['state'], 'paused')

    def test_retry_cannot_complete_two_steps(self):
        self.store.change(self.task['id'], 0, 'confirm_step')
        with self.assertRaises(Conflict):
            self.store.change(self.task['id'], 0, 'confirm_step')
        self.assertEqual(self.store.get(self.task['id'])['cursor'], 1)

    def test_timer_expiry_and_pause_never_complete_step(self):
        self.store.change(self.task['id'], 0, 'start_timer', seconds=30)
        self.store.change(self.task['id'], 1, 'pause')
        self.now = 200
        checkpoint = self.store.checkpoint(self.task['id'])
        self.assertTrue(checkpoint['timer_due'])
        self.assertEqual(checkpoint['task']['cursor'], 0)
        with self.assertRaises(Conflict):
            self.store.change(self.task['id'], 2, 'confirm_step')
        self.store.change(self.task['id'], 2, 'resume')
        self.store.change(self.task['id'], 3, 'confirm_step')
        self.assertIsNone(self.store.get(self.task['id'])['timer'])

    def test_tasks_do_not_overwrite_each_other(self):
        other = self.store.create('Laundry', ['Load', 'Unload'])
        self.store.change(other['id'], 0, 'confirm_step')
        self.assertEqual(self.store.get(self.task['id'])['cursor'], 0)

    def test_finish_and_invalid_actions_preserve_state(self):
        for revision in range(3):
            self.store.change(self.task['id'], revision, 'confirm_step')
        with self.assertRaises(Conflict):
            self.store.change(self.task['id'], 3, 'resume')
        self.assertIsNone(self.store.checkpoint(self.task['id'])['next_step'])

    def test_invalid_timer_rolls_back(self):
        for seconds in [True, -1, 0, 86401, float('inf'), '30']:
            with self.assertRaises(ValueError):
                self.store.change(self.task['id'], 0, 'start_timer', seconds=seconds)
        self.assertEqual(self.store.get(self.task['id'])['revision'], 0)


if __name__ == '__main__':
    unittest.main()
