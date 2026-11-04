"""Standalone synthetic tests for batch_test.py; no Isaac Gym or torch needed."""
import contextlib
import importlib.util
import io
import json
import math
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('standalone_batch', Path(__file__).with_name('batch_test.py'))
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


def write_events(folder, value, tag='Episode/rew_tracking_lin_vel'):
    from tensorboard.compat.proto.event_pb2 import Event
    from tensorboard.compat.proto.summary_pb2 import Summary
    from tensorboard.summary.writer.event_file_writer import EventFileWriter
    writer = EventFileWriter(str(folder))
    for step in range(5):
        writer.add_event(Event(wall_time=time.time(), step=step,
                               summary=Summary(value=[Summary.Value(tag=tag, simple_value=value)])))
    writer.flush()
    writer.close()


class StandaloneBatchTests(unittest.TestCase):
    def test_window_and_peak_are_separate(self):
        events = [SimpleNamespace(step=i, value=v) for i, v in enumerate([8.0, 2.0, 4.0])]
        result = batch.summarize_events(events, 2)
        self.assertEqual((result['mean'], result['std']), (3.0, 1.0))
        self.assertEqual((result['peak_step'], result['peak_value']), (0, 8.0))
        self.assertEqual(result['final_value'], 4.0)

    def test_invalid_and_short_streams(self):
        self.assertEqual(batch.summarize_events([], 1)['status'], 'INVALID')
        for value in (math.nan, math.inf):
            self.assertEqual(batch.summarize_events([SimpleNamespace(step=0, value=value)], 1)['status'], 'INVALID')
        self.assertEqual(batch.summarize_events([SimpleNamespace(step=0, value=1)], 2)['status'], 'INSUFFICIENT_DATA')

    def test_restart_or_duplicate_is_rejected(self):
        for steps in ([0, 1, 0], [0, 1, 1]):
            result = batch.summarize_events([SimpleNamespace(step=s, value=1) for s in steps], 2)
            self.assertEqual(result['status'], 'AMBIGUOUS_STEPS')

    def test_comparison_requires_manifest(self):
        rows = [{'run': name, 'status': 'SUMMARY_ONLY', 'mean': 1.0} for name in ('a', 'b')]
        batch.compare(rows, 'a', 0.1)
        self.assertTrue(all(row['status'] == 'UNVERIFIED_CONFIG' for row in rows))

    def test_real_format_events_csv_and_markdown(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, value in [('base', 0.9), ('candidate', 0.4)]:
                folder = root / 'logs' / name
                write_events(folder, value)
                (folder / 'qa_metadata.json').write_text(json.dumps({'comparison_key': 'synthetic-fixture'}))
            output = root / 'report.md'
            with contextlib.redirect_stdout(io.StringIO()):
                code = batch.main(['--log-root', str(root / 'logs'), '--window', '3',
                                   '--baseline-run', 'base', '--output', str(output)])
            self.assertEqual(code, 1)
            self.assertIn('55.6%', output.read_text())
            self.assertIn('REGRESSION', output.read_text())
            self.assertTrue(output.with_suffix('.csv').is_file())

    def test_missing_tag_and_empty_directory(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_events(root / 'run', 1.0, tag='Train/mean_reward')
            rows = batch.collect(root, 'Episode/rew_tracking_lin_vel', 3)
            self.assertEqual(rows[0]['status'], 'INVALID')
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with contextlib.redirect_stdout(io.StringIO()):
                code = batch.main(['--log-root', str(root), '--output', str(root / 'empty.md')])
            self.assertEqual(code, 2)


if __name__ == '__main__':
    unittest.main()
