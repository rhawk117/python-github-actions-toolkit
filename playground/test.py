
from action_toolkit import core


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

core.set_output(
    name='test_output',
    value='This is a test output'
)

plat_info = core.get_platform()

core.notice(f"Platform: {plat_info.__repr__()}")

core.set_output(
    name='platform_info',
    value=plat_info.__repr__()
)

data = core.save_state(
    name='test_state',
    value='This is a test state'
)

core.notice(f"Saved state: {data}")

state_got = core.get_state(
    name='test_state'
)

core.notice(f"Retrieved state: {state_got}")