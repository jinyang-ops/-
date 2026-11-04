"""Extract full TensorBoard scalar streams and write a training-log report.

Exit 0: summary / passed comparison; 1: metric regression; 2: invalid input,
insufficient data, ambiguous restart or unverified configuration.
This script does not evaluate .pt checkpoints.
"""
import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path


def markdown_cell(value):
    return str(value).replace('|', '\\|').replace('\n', ' ')


def stats(values):
    values = list(values)
    if not values or not all(math.isfinite(float(value)) for value in values):
        raise ValueError('Empty or non-finite metric values')
    return {'mean': statistics.mean(values), 'std': statistics.pstdev(values), 'n': len(values)}


def summarize_events(events, window):
    if not events:
        return {'status': 'INVALID', 'reason': 'No scalar events'}
    if any(not math.isfinite(float(event.value)) for event in events):
        return {'status': 'INVALID', 'reason': 'NaN or Inf in scalar stream'}
    # Refuse to silently splice a restarted or rolled-back training branch.
    if any(current.step <= previous.step for previous, current in zip(events, events[1:])):
        return {'status': 'AMBIGUOUS_STEPS', 'reason': 'Duplicate or decreasing steps; separate sessions first'}
    if len(events) < window:
        return {'status': 'INSUFFICIENT_DATA', 'reason': '{} / {} points'.format(len(events), window)}
    tail = events[-window:]
    result = stats(event.value for event in tail)
    peak = max(events, key=lambda event: event.value)
    return {'status': 'SUMMARY_ONLY', 'reason': '', 'points': len(events),
            'window': window, 'step_start': int(tail[0].step),
            'step_end': int(tail[-1].step), 'mean': result['mean'], 'std': result['std'],
            'peak_step': int(peak.step), 'peak_value': float(peak.value),
            'final_step': int(events[-1].step), 'final_value': float(events[-1].value)}


def collect(root, tag, window):
    from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

    directories = sorted({path.parent for path in root.rglob('events.out.tfevents.*') if path.is_file()})
    rows = []
    for directory in directories:
        row = {'run': directory.relative_to(root).as_posix() or '.', 'tag': tag}
        try:
            accumulator = EventAccumulator(str(directory), size_guidance={'scalars': 0},
                                           purge_orphaned_data=False)
            accumulator.Reload()
            available = accumulator.Tags().get('scalars', [])
            if tag not in available:
                raise ValueError('Missing tag; available scalar tags: ' + ', '.join(available))
            row.update(summarize_events(accumulator.Scalars(tag), window))
            manifest = directory / 'qa_metadata.json'
            if manifest.exists():
                metadata = json.loads(manifest.read_text(encoding='utf-8'))
                row['comparison_key'] = metadata.get('comparison_key')
                row['source_commit'] = metadata.get('git_commit')
        except Exception as error:
            row.update(status='INVALID', reason='{}: {}'.format(type(error).__name__, error))
        rows.append(row)
    return rows


def compare(rows, baseline_run, max_drop):
    if baseline_run is None:
        return
    matching = [row for row in rows if row['run'] == baseline_run]
    if len(matching) != 1:
        raise ValueError('--baseline-run must exactly match one run ID in the report')
    baseline = matching[0]
    if baseline['status'] != 'SUMMARY_ONLY' or baseline['mean'] <= 0:
        raise ValueError('Baseline needs sufficient finite data and a positive mean')
    for row in rows:
        if row['status'] != 'SUMMARY_ONLY':
            continue
        if not baseline.get('comparison_key') or not row.get('comparison_key'):
            row.update(status='UNVERIFIED_CONFIG', reason='Missing recorded training manifest')
        elif row['comparison_key'] != baseline['comparison_key']:
            row.update(status='CONFIG_MISMATCH', reason='Environment, PPO, SDK or source differs')
        elif row is baseline:
            row['status'] = 'BASELINE'
            row['drop'] = 0.0
        else:
            row['drop'] = (baseline['mean'] - row['mean']) / abs(baseline['mean'])
            row['status'] = 'REGRESSION' if row['drop'] > max_drop else 'PASS'


def write_report(rows, output, tag, window, baseline_run, max_drop):
    output.parent.mkdir(parents=True, exist_ok=True)
    fields = ['run', 'tag', 'status', 'reason', 'step_start', 'step_end', 'points',
              'window', 'mean', 'std', 'peak_step', 'peak_value', 'final_step',
              'final_value', 'drop', 'comparison_key', 'source_commit']
    with output.with_suffix('.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# 训练日志分析报告', '',
             '数据来源：本次读取的 TensorBoard 事件文件。此报告未加载模型，不是固定场景检查点评测。', '',
             '- Tag：`{}`'.format(tag), '- 窗口：末尾 {} 个有效记录点；标准差为总体标准差。'.format(window),
             '- 基线：{}；允许下降：{:.1%}。'.format(baseline_run or '未设置，仅提取数据', max_drop),
             '- 跨 run 比较仅在训练配置、源码与 SDK 指纹匹配时启用；不同训练阶段仍需人工解释。', '',
             '| Run | Step 范围 | 均值 ± 标准差 | 下降率 | 状态 | 备注 |',
             '| --- | --- | ---: | ---: | --- | --- |']
    for row in rows:
        step_range = '{}–{}'.format(row['step_start'], row['step_end']) if 'mean' in row else '—'
        metric = '{:.6f} ± {:.6f}'.format(row['mean'], row['std']) if 'mean' in row else '—'
        drop = '{:.1%}'.format(row['drop']) if 'drop' in row else '—'
        lines.append('| {} | {} | {} | {} | {} | {} |'.format(
            markdown_cell(row['run']), step_range, metric, drop, row['status'], markdown_cell(row.get('reason', ''))))
    if not rows:
        lines += ['', '**INVALID：没有找到事件文件。**']
    lines += ['', '## 训练日志峰值与末值', '',
              '峰值指训练 scalar 记录点；对应 step 不自动等同于最佳模型检查点。', '',
              '| Run | 峰值 step | 峰值 | 末值 step | 末值 |',
              '| --- | ---: | ---: | ---: | ---: |']
    for row in rows:
        if 'peak_value' in row:
            lines.append('| {} | {} | {:.6f} | {} | {:.6f} |'.format(
                markdown_cell(row['run']), row['peak_step'], row['peak_value'],
                row['final_step'], row['final_value']))
    output.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log-root', type=Path, required=True)
    parser.add_argument('--tag', default='Episode/rew_tracking_lin_vel')
    parser.add_argument('--window', type=int, default=100)
    parser.add_argument('--baseline-run', help='Exact relative run directory printed in the report')
    parser.add_argument('--max-drop', type=float, default=0.10)
    parser.add_argument('--output', type=Path, default=Path('reports/training_log_report.md'))
    args = parser.parse_args(argv)
    if args.window <= 0 or not 0 <= args.max_drop < 1:
        parser.error('window must be positive; max-drop must be in [0, 1)')
    try:
        if not args.log_root.is_dir():
            raise ValueError('Log root does not exist: ' + str(args.log_root))
        rows = collect(args.log_root, args.tag, args.window)
        compare(rows, args.baseline_run, args.max_drop)
        write_report(rows, args.output, args.tag, args.window, args.baseline_run, args.max_drop)
        print('Report:', args.output)
        valid = {'SUMMARY_ONLY', 'BASELINE', 'PASS', 'REGRESSION'}
        if not rows or any(row['status'] not in valid for row in rows):
            return 2
        return 1 if any(row['status'] == 'REGRESSION' for row in rows) else 0
    except Exception as error:
        print('ERROR:', error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
