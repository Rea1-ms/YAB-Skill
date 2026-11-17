"""Check or synchronize this independent skill repository without deleting files."""

import argparse
from pathlib import Path


def skill_files(root):
    files = {}
    entry = root / 'SKILL.md'
    if entry.is_file():
        files[Path('SKILL.md')] = entry
    for folder in ('references', 'scripts', 'assets', 'agents'):
        directory = root / folder
        if directory.is_dir():
            for file in directory.rglob('*'):
                if '__pycache__' not in file.parts and file.is_file():
                    files[file.relative_to(root)] = file
    for file in files.values():
        if file.is_symlink():
            raise ValueError(f'技能文件为链接，保留并停止：{file}')
        if not file.resolve().is_relative_to(root):
            raise ValueError(f'技能文件位于目录之外：{file}')
    return files


def main():
    parser = argparse.ArgumentParser(description='从独立技能仓库检查或同步代理副本，不删除文件。')
    parser.add_argument('--apply', action='store_true', help='实际同步；默认只检查差异')
    parser.add_argument('--target', type=Path, action='append', help='目标技能目录，可重复指定')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    if not (source / '.git').exists():
        parser.error('请从独立技能仓库运行脚本，代理副本不能作为维护源。')
    home = Path.home()
    defaults = [home / name / 'skills/yab' for name in ('.cc-switch', '.agents', '.agent')]
    targets = args.target or [target for target in defaults if target.is_dir()]
    if not targets:
        parser.error('没有现有代理副本；请通过 --target 指定目标目录。')
    source_files = skill_files(source)
    if Path('SKILL.md') not in source_files:
        parser.error('维护源缺少 SKILL.md（技能入口）。')
    content = {name: file.read_bytes() for name, file in source_files.items()}
    plans = []
    seen = set()
    for target in targets:
        target = target.expanduser().resolve(strict=True)
        if target in seen:
            continue
        seen.add(target)
        if not target.is_dir() or target.is_relative_to(source) or source.is_relative_to(target):
            raise ValueError(f'同步目标与维护源重叠或不是目录：{target}')
        target_files = skill_files(target)
        extras = sorted(set(target_files) - set(content))
        extras += sorted(file.relative_to(target) for file in target.iterdir()
                         if file.name not in {'SKILL.md', 'references', 'scripts', 'assets', 'agents', '.git', '__pycache__'})
        changed = []
        for name, data in content.items():
            destination = target / name
            for parent in (destination, *destination.parents):
                if parent == target:
                    break
                if parent.is_symlink():
                    raise ValueError(f'目标文件路径包含链接，保留并停止：{destination}')
            if not destination.resolve().is_relative_to(target):
                raise ValueError(f'目标文件位于目录之外：{destination}')
            if destination.exists() and not destination.is_file():
                raise ValueError(f'目标文件与目录冲突：{destination}')
            if not destination.exists() or destination.read_bytes() != data:
                changed.append(name)
        plans.append((target, changed, extras))
    different = False
    for target, changed, extras in plans:
        print(f'{target.as_posix()}：待同步 {len(changed)} 个，额外保留 {len(extras)} 个')
        for name in changed:
            print(f'  更新：{name.as_posix()}')
        for name in extras:
            print(f'  保留：{name.as_posix()}')
        if args.apply:
            for name in changed:
                destination = target / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(content[name])
            for name, data in content.items():
                if (target / name).read_bytes() != data:
                    raise ValueError(f'同步后内容不一致：{target / name}')
        different |= bool(extras or (changed and not args.apply))
    print('同步完成，未删除文件。' if args.apply else '检查完成，未写入文件。')
    return 1 if different else 0


if __name__ == '__main__':
    raise SystemExit(main())
