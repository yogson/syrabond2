from tasks.models import Task


def create_task(action=None, scenario=None):
    t = Task(action=action)
    t.save()
    return t
