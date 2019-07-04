import json

from six.moves import zip_longest


def skip_logic_block_data(choice, logic, form=None, question=None):
    return {
        'choice': choice,
        'skip_logic': logic,
        'form': form,
        'question': question,
    }


def skip_logic_data(choices=list(), logics=list(), form=None, question=None):
    data = [
        {'type': 'skip_logic', 'value': skip_logic_block_data(
            choice,
            logic,
            form.id if logic == 'form' else None,
            question.sort_order + 1 if logic == 'question' else None,
        )
        } for choice, logic in zip_longest(choices, logics, fillvalue='next')
    ]
    return json.dumps(data)
