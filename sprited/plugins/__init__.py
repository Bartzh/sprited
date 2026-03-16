from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sprited.plugins.reminder import ReminderPlugin
    from sprited.plugins.time_incrementer import TimeIncrementerPlugin
    from sprited.plugins.instruction import InstructionPlugin
    from sprited.plugins.note import NotePlugin
    from sprited.plugins.cli import SimpleCLI
    from sprited.plugins.api import SimpleAPI

__all__ = [
    'ReminderPlugin',
    'TimeIncrementerPlugin',
    'InstructionPlugin',
    'NotePlugin',
    'SimpleCLI',
    'SimpleAPI',
]

def __getattr__(name):
    if name == 'ReminderPlugin':
        from sprited.plugins.reminder import ReminderPlugin
        return ReminderPlugin
    if name == 'TimeIncrementerPlugin':
        from sprited.plugins.time_incrementer import TimeIncrementerPlugin
        return TimeIncrementerPlugin
    if name == 'InstructionPlugin':
        from sprited.plugins.instruction import InstructionPlugin
        return InstructionPlugin
    if name == 'NotePlugin':
        from sprited.plugins.note import NotePlugin
        return NotePlugin
    if name =='SimpleCLI':
        from sprited.plugins.cli import SimpleCLI
        return SimpleCLI
    if name == 'SimpleAPI':
        from sprited.plugins.api import SimpleAPI
        return SimpleAPI
    raise AttributeError(f"module {__name__} has no attribute {name}")
