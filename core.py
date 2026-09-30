"""Persistent task checkpoints. Elapsed time never implies physical completion."""
import json
import sqlite3
import time
import uuid
from contextlib import contextmanager


class Conflict(ValueError):
    pass


class TaskStore:
    def __init__(self, path, clock=time.time):
        self.path = str(path)
        self.clock = clock
        with self.connection() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, body TEXT NOT NULL)""")

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def create(self, title, steps):
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            raise ValueError('A task needs a title of 1–160 characters.')
        if not isinstance(steps, list) or not 1 <= len(steps) <= 30:
            raise ValueError('Provide 1–30 steps.')
        if any(not isinstance(s, str) or not s.strip() or len(s) > 500 for s in steps):
            raise ValueError('Each step needs 1–500 characters.')
        task = dict(id=uuid.uuid4().hex, title=title.strip(), steps=[s.strip() for s in steps],
                    cursor=0, revision=0, state='active', note='', timer=None, events=[])
        task['events'].append(dict(kind='created', at=self.clock()))
        with self.connection() as db:
            db.execute('INSERT INTO tasks VALUES (?, ?)', (task['id'], json.dumps(task)))
        return task

    def get(self, task_id):
        with self.connection() as db:
            row = db.execute('SELECT body FROM tasks WHERE id=?', (task_id,)).fetchone()
        if not row:
            raise KeyError('Task not found.')
        return json.loads(row[0])

    def all(self):
        with self.connection() as db:
            rows = db.execute('SELECT body FROM tasks ORDER BY rowid DESC').fetchall()
        return [json.loads(row[0]) for row in rows]

    def change(self, task_id, revision, action, note='', seconds=None):
        if type(revision) is not int or revision < 0:
            raise ValueError('Provide the current integer revision.')
        if not isinstance(note, str) or len(note) > 1000:
            raise ValueError('Checkpoint notes must be at most 1000 characters.')
        with self.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            row = db.execute('SELECT body FROM tasks WHERE id=?', (task_id,)).fetchone()
            if not row:
                raise KeyError('Task not found.')
            task = json.loads(row[0])
            if task['revision'] != revision:
                raise Conflict('This task changed. Read its checkpoint before acting again.')
            if task['state'] == 'completed':
                raise Conflict('This task is already complete.')
            if action == 'pause':
                if task['state'] != 'active':
                    raise Conflict('This task is already paused.')
                task.update(state='paused', note=note)
            elif action == 'resume':
                if task['state'] != 'paused':
                    raise Conflict('This task is not paused.')
                task['state'] = 'active'
            elif action == 'confirm_step':
                if task['state'] != 'active':
                    raise Conflict('Resume and review the checkpoint first.')
                task['cursor'] += 1
                task.update(timer=None, note='')
                if task['cursor'] == len(task['steps']):
                    task['state'] = 'completed'
            elif action == 'start_timer':
                if task['state'] != 'active':
                    raise Conflict('Resume before starting a timer.')
                if type(seconds) is not int or not 1 <= seconds <= 86400:
                    raise ValueError('Timer must be 1–86400 whole seconds.')
                task['timer'] = dict(due_at=self.clock() + seconds, step=task['cursor'])
            else:
                raise ValueError('Unknown action.')
            task['revision'] += 1
            task['events'].append(dict(kind=action, at=self.clock(), note=note,
                                       revision=task['revision']))
            db.execute('UPDATE tasks SET body=? WHERE id=?', (json.dumps(task), task_id))
        return task

    def checkpoint(self, task_id):
        task = self.get(task_id)
        timer = task['timer']
        return dict(task=task, completed_steps=task['steps'][:task['cursor']],
                    next_step=(task['steps'][task['cursor']] if task['state'] != 'completed' else None),
                    timer_due=bool(timer and self.clock() >= timer['due_at']),
                    reminder='Timer expiry is a reminder to check, never confirmation that a step is done.')
