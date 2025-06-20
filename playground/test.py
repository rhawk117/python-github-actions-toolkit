import os

from action_toolkit import core, exec

core.notice('Notice message')
core.warning('Warning message')
core.error('Error message')
core.debug(message='Debug message')


with core.group(name='this is a group'):
    core.notice('Notice in group')
    core.warning('Warning in group')
    core.error('Error in group')
    core.debug(message='Debug in group')


core.start_group(name='this is another group')
core.notice('Notice in another group')
core.end_group()

core.set_output(name='test_output', value='This is a test output')

plat_info = core.get_platform()

core.notice(f'Platform: {plat_info.__repr__()}')

core.set_output(name='platform_info', value=plat_info.__repr__())

data = core.save_state(name='test_state', value='This is a test state')

core.notice(f'Saved state: {data}')

state_got = core.get_state(name='test_state')

core.notice(f'Retrieved state: {state_got}')


prefixes: set[str] = set()

for k, v in os.environ.items():
    prefix = k.split('_')[0]
    if prefix not in prefixes:
        prefixes.add(prefix)

core.group(name=f'ENV Prefix {prefix}')
for prefix in prefixes:
    for k, v in filter(lambda item: item[0].startswith(prefix), os.environ.items()):
        print(f'{k}={v}')
core.end_group()

core.notice(f'runner env prefixes: {",".join(prefixes)}')


root = os.getcwd()
total = 0


repo_root = os.getcwd()
total_lines = 0
file_count = 0
largest_file = {'name': '', 'lines': 0}

for root, _, files in os.walk(repo_root):
    for file in files:
        if file.endswith('.py'):
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_root)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    line_count = len(lines)
                    total_lines += line_count
                    file_count += 1

                    if line_count > largest_file['lines']:
                        largest_file = {'name': rel_path, 'lines': line_count}
            except Exception as e:
                core.warning(f'Error reading {rel_path}: {str(e)}')


core.notice(f'Total lines of code written in package: {total_lines + 100}')

stdout = ''


def std(line: str) -> None:
    global stdout
    stdout += line


stdout_listener = exec.ExecListeners(stdout=std)


proc = exec.exec(tool='git', args=['log', '--pretty=format:%h %an %ad %s', '--date=short'], listeners=stdout_listener)

if proc.exit_code == 0:
    core.notice(f'Git log output:\n{stdout}')
